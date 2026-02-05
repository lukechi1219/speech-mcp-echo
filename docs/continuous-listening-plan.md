# Speech-MCP 持續監聽改進計畫

> **狀態**：計畫中
> **建立日期**：2026-02-05
> **目標**：解決「沉默後失效」問題，實現持續監聽機制

---

## 問題分析

### 用戶遇到的問題
**症狀**：「如果我一段時間不說話，MCP 就再也不會聽我說話了」

**根本原因**：
1. **Timeout 機制**：當前設定 60 秒 timeout，沉默超時後返回空字符串，對話中斷
2. **單次監聽模式**：`voice_listen()` 和 `voice_reply()` 都是一次性的，不會自動重新監聽
3. **沉默檢測**：3 秒靜音會自動停止錄音（這部分正常，是為了檢測用戶說完話）

**期望行為**：像語音助手一樣持續待命，不會因為思考時間過長而中斷對話

---

## 推薦方案：Silence-Tolerant Voice Reply（靜默容忍語音回覆）

### 核心設計理念
在 `voice_reply()` 中加入**重試機制**，當沉默超時時：
1. 播放提示音（Tink.aiff）
2. 自動重新監聽
3. 重複最多 10 次（可配置）
4. 設定總對話時長上限防止無限循環

### 為什麼選擇這個方案？
- ✅ **最小改動**：只需修改 `voice_reply()` 和配置系統
- ✅ **符合 MCP 架構**：在現有 request-response 模式內運作
- ✅ **用戶體驗佳**：自然的對話流程，不會突然中斷
- ✅ **安全可控**：有明確的退出機制和安全上限
- ✅ **向後相容**：不影響現有工具的使用方式

---

## 實施計畫

### Phase 1: 配置系統擴充 ⭐ 核心

**檔案**：`src/speech_mcp_echo/config/__init__.py`

**修改內容**：
```python
DEFAULT_CONFIG = {
    "stt": {
        "timeout": 60,                      # 單次監聽超時（秒）
        "silence_retry_count": 10,          # 沉默重試次數（新增）
        "retry_prompt_type": "beep",        # 重試提示類型（新增）
        "max_conversation_timeout": 3600,   # 總對話時長上限（秒，新增）
        "silence_threshold": 0.02,          # 沉默振幅閾值（可配置化）
        "max_silence_duration": 3.0,        # 停止錄音前的沉默時長（秒，可配置化）
    },
    # ... 其他配置保持不變
}
```

**新增配置項說明**：
| 參數 | 預設值 | 說明 |
|------|--------|------|
| `silence_retry_count` | 10 | 沉默超時後重試幾次 |
| `retry_prompt_type` | "beep" | 提示類型：beep/voice/silent |
| `max_conversation_timeout` | 3600 | 總對話時長上限（秒） |

---

### Phase 2: voice_reply() 重試機制 ⭐ 核心

**檔案**：`src/speech_mcp_echo/server.py`

**修改函數**：`voice_reply()`

**新增功能**：
1. 新增 `silence_retry_count` 參數（可選，預設讀取配置）
2. 新增 `retry_prompt_type` 參數（可選）
3. 實作重試循環邏輯
4. 每次重試前播放提示音

**關鍵邏輯**：
```python
@mcp.tool()
def voice_reply(
    text: str,
    wait_for_response: bool = True,
    timeout: Optional[int] = None,
    silence_retry_count: Optional[int] = None,  # 新增參數
    retry_prompt_type: Optional[str] = None     # 新增參數（"beep" 或 "voice"）
) -> str:
    engine = get_engine()

    # 1. 先播放回應
    spoken = engine.speak(text, summarize=True)

    if not wait_for_response:
        return f"Spoke: {spoken}"

    # 2. 獲取重試配置
    if silence_retry_count is None:
        silence_retry_count = get_setting("stt", "silence_retry_count", default=10)

    if retry_prompt_type is None:
        retry_prompt_type = get_setting("stt", "retry_prompt_type", default="beep")

    time.sleep(0.5)

    # 3. 重試循環
    for attempt in range(silence_retry_count + 1):  # +1 因為第一次不算重試
        response = engine.listen(timeout=timeout)

        if response:  # 獲得有效回應
            return response

        # 沉默超時，判斷是否重試
        if attempt < silence_retry_count:
            logger.info(f"Silence timeout, retry {attempt+1}/{silence_retry_count}")

            # 根據配置播放不同提示
            if retry_prompt_type == "beep":
                # 播放簡短提示音（使用 macOS 系統音效）
                import subprocess
                subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"],
                             check=False, capture_output=True)
            elif retry_prompt_type == "voice":
                # 播放語音提示
                engine.speak("還在嗎？", summarize=False)
            # else: silent (不播放任何提示)

            time.sleep(0.5)
        else:
            logger.info("All silence retries exhausted, ending conversation")

    # 所有重試用盡
    return ""
```

**重試提示策略**：
| 類型 | 說明 | 適用場景 |
|------|------|---------|
| `beep` | macOS Tink.aiff 音效 | 預設，不干擾思考 |
| `voice` | 語音「還在嗎？」 | 需要明確提醒時 |
| `silent` | 完全靜默 | 極長時間思考 |

---

### Phase 3: 對話狀態追蹤（建議實作）

**檔案**：`src/speech_mcp_echo/core/voice_engine.py`

**新增功能**：
1. 在 `VoiceEngine` 中加入對話狀態追蹤
2. 記錄總對話時長
3. 檢查是否超過 `max_conversation_timeout`
4. 提供重置狀態的方法

**新增屬性**：
```python
class VoiceEngine:
    def __init__(self):
        # ... 現有初始化 ...
        self._conversation_state = {
            "start_time": None,
            "turn_count": 0,
            "total_silence_timeouts": 0,
        }

    def reset_conversation_state(self):
        """重置對話狀態（新對話開始時調用）"""
        self._conversation_state = {
            "start_time": time.time(),
            "turn_count": 0,
            "total_silence_timeouts": 0,
        }

    def check_conversation_timeout(self) -> bool:
        """檢查是否超過總對話時長上限"""
        if self._conversation_state["start_time"] is None:
            return False

        max_timeout = get_setting("stt", "max_conversation_timeout", default=3600)
        elapsed = time.time() - self._conversation_state["start_time"]
        return elapsed > max_timeout
```

---

### Phase 4: 可配置化沉默檢測（可選）

**檔案**：`src/speech_mcp_echo/audio_processor.py`、`constants.py`

**目標**：讓沉默檢測參數可配置，而非寫死

**修改內容**：
1. 將 `SILENCE_THRESHOLD` 和 `MAX_SILENCE_DURATION` 從 constants.py 改為可配置
2. 在 `audio_processor.py` 的 `_detect_silence()` 中讀取配置

**範例**：
```python
# audio_processor.py _detect_silence() 中
silence_threshold = get_setting("stt", "silence_threshold", default=0.02)
max_silence_duration = get_setting("stt", "max_silence_duration", default=3.0)
```

---

## 實施優先級

| 優先級 | Phase | 內容 | 預估工作量 |
|--------|-------|------|-----------|
| ⭐ 必須 | Phase 1 | 配置系統新增參數 | 小 |
| ⭐ 必須 | Phase 2 | `voice_reply()` 重試邏輯 | 中 |
| ⭕ 建議 | Phase 3 | 對話狀態追蹤 | 小 |
| ⭕ 可選 | Phase 4 | 可配置沉默檢測 | 小 |

**最小可行方案**：Phase 1-2 即可解決 80% 的問題
**完整方案**：Phase 1-3 可達到生產級品質

---

## 關鍵檔案清單

| 檔案 | 修改內容 | 優先級 |
|------|---------|--------|
| `config/__init__.py` | 新增配置參數 | ⭐ 必須 |
| `server.py` | 修改 `voice_reply()` 加入重試邏輯 | ⭐ 必須 |
| `core/voice_engine.py` | 新增對話狀態追蹤 | ⭕ 建議 |
| `audio_processor.py` | 可配置化沉默檢測 | ⭕ 可選 |
| `constants.py` | 文件更新（如實作 Phase 4） | ⭕ 可選 |

**完整路徑**：
```
src/speech_mcp_echo/
├── config/__init__.py       ← Phase 1
├── server.py                ← Phase 2
├── core/voice_engine.py     ← Phase 3
├── audio_processor.py       ← Phase 4
└── constants.py             ← Phase 4
```

---

## 使用範例

### 配置檔案範例
```json
{
  "stt": {
    "engine": "faster-whisper",
    "timeout": 90,
    "silence_retry_count": 10,
    "retry_prompt_type": "beep",
    "max_conversation_timeout": 3600,
    "silence_threshold": 0.02,
    "max_silence_duration": 3.0
  }
}
```

**說明**：
- `silence_retry_count: 10`：極長等待，約 15-20 分鐘的容忍度
- `retry_prompt_type: "beep"`：使用 macOS Tink.aiff 音效
- `max_conversation_timeout: 3600`：總時長上限 1 小時

### 對話流程範例

**場景 1：正常對話**
```
User: "早安 Sylvie"
AI: "早安！今天想做什麼？" (voice_reply, wait=True)
[User 思考 5 秒]
User: "我想規劃一下今天的高槓桿活動"
AI: [繼續對話]
```

**場景 2：短暫沉默，重試成功**
```
User: "老賈"
AI: "Boss，有何吩咐？" (voice_reply, wait=True)
[User 沉默 90 秒，超過 timeout]
AI: *Tink* (播放提示音，重試 1)
User: "在，我在想問題"
AI: [繼續對話]
```

**場景 3：極長時間沉默，優雅退出**
```
User: "語音討論"
AI: "好的，開始語音討論模式" (voice_reply, wait=True)
[User 離開座位，持續沉默]
AI: *Tink* (重試 1, ~90秒後)
AI: *Tink* (重試 2, ~180秒後)
AI: *Tink* (重試 3, ~270秒後)
... (繼續到第 10 次)
AI: *Tink* (重試 10, ~900秒 = 15分鐘後)
[仍然沉默]
AI: [返回空字符串，對話結束]
```

**實際等待時長**：約 15-20 分鐘（取決於 timeout 設定）

---

## 驗證測試計畫

### 測試案例 1：基本重試功能
1. 啟動語音對話（如 `/oralDiscussGoogleTTS`）
2. AI 說話後，保持沉默超過 timeout（90 秒）
3. **預期**：聽到 *Tink* 提示音並繼續監聽
4. 回應後對話繼續

### 測試案例 2：多次重試（10 次）
1. 啟動對話
2. 第一次沉默超時 → 聽到 *Tink* 提示音
3. 繼續沉默 → 再次聽到 *Tink*
4. 重複 10 次
5. 第 10 次後繼續沉默 → 對話結束
6. **預期**：總共重試 10 次（約 15-20 分鐘）後優雅退出

### 測試案例 3：提示音播放
1. 啟動對話並保持沉默至超時
2. **預期**：聽到 macOS Tink.aiff 音效（清脆的「叮」聲）
3. 確認音效音量適中，不會過於干擾
4. 確認音效播放不會阻塞監聽重啟

### 測試案例 4：總對話時長限制（Phase 3）
1. 設定 `"max_conversation_timeout": 60`（1 分鐘）
2. 持續對話超過 1 分鐘
3. **預期**：系統提示「對話時間過長」並優雅退出

### 測試案例 5：與現有 Agent 整合
1. 測試 `jarvis-oral-summarizer`（老賈模式）
2. 測試 `voice-discussion`（語音討論模式）
3. 測試 `sylvie-journal-companion`（早安 Sylvie）
4. **預期**：所有模式都能正常使用重試機制

---

## 用戶偏好設定（已確認）

### ✅ 已確認的配置

1. **重試提示方式**：只播放提示音（beep）
   - 使用 macOS 系統音效 `/System/Library/Sounds/Tink.aiff`
   - 通過 `afplay` 指令播放，非阻塞
   - 不干擾思考，但提供明確的「還在聽」反饋

2. **重試次數**：10 次（極長等待）
   - 約等於 15-20 分鐘的等待容忍度
   - 適合需要長時間思考的場景（寫作、規劃、深度對話）
   - 總時長上限設為 1 小時作為安全網

3. **退出機制**：
   - 主要依賴重試次數用盡（10 次後自動退出）
   - 可選：未來可加入語音指令「結束對話」立即中斷（不在本次實作範圍）

---

## 風險評估與緩解策略

| 風險 | 嚴重性 | 緩解策略 |
|------|--------|---------|
| 無限循環（重試失控） | 中 | `max_conversation_timeout` 總時長上限 |
| 重試提示干擾思考 | 低 | 可配置提示方式（beep/voice/silent） |
| 資源洩漏（長時間對話） | 中 | 對話狀態追蹤 + 定期清理 |
| 與現有 Agent 不相容 | 低 | 向後相容設計，預設行為不變 |
| 配置檔案錯誤 | 低 | 提供預設值 fallback |

---

## 備選方案

### 如果推薦方案不可行

**Plan B：延長 Timeout**
- 將 timeout 延長至 300-600 秒
- 每 60 秒播放「還在聽」提示音
- 優點：實作極簡
- 缺點：只是延後問題，未根本解決

**Plan C：真正的背景監聽（進階）**
- 使用 asyncio 建立背景監聽線程
- 需要 MCP 協議支援或 workaround
- 優點：專業級解決方案
- 缺點：開發成本高，MCP 可能不支援

---

## 總結

此計畫透過在 `voice_reply()` 中加入**智能重試機制**，解決「沉默後失效」的問題：

| 範圍 | 內容 |
|------|------|
| ✅ **核心改進** | Phase 1-2（配置 + voice_reply 重試） |
| ⭕ **增強功能** | Phase 3（對話狀態追蹤） |
| ⭕ **可選優化** | Phase 4（可配置沉默檢測） |

**最小可行方案**：只實作 Phase 1-2 即可解決 80% 的問題
**完整方案**：實作 Phase 1-3 可達到生產級品質

---

## 變更記錄

| 日期 | 變更內容 |
|------|---------|
| 2026-02-05 | 初版計畫建立 |
