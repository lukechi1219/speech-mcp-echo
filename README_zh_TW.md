# Speech MCP Echo

> **基於**: [Kvadratni/speech-mcp](https://github.com/Kvadratni/speech-mcp) - 原始 Speech MCP 專案

為多種 AI CLI 提供語音介面 - 支援 Claude Code、Gemini CLI、Codex CLI 及所有 MCP 相容工具。

## 功能特色

- **多 CLI 支援**：支援 Claude Code、Gemini CLI、Codex CLI 及任何 MCP 相容工具
- **持續聆聽** *(v0.2.0 新功能)*：非阻塞式背景聆聽，靜默時自動重試
- **可設定的 STT**：本地端 (faster-whisper) 或雲端 (Groq Whisper、OpenAI Whisper、Google Speech)
- **可設定的 TTS**：本地端 (pyttsx3) 或雲端 (Google Cloud TTS、OpenAI TTS)
- **雙語支援**：英文及中文（繁體/簡體）文字處理
- **JARVIS 摘要器**：將冗長的回應濃縮成簡潔有趣的摘要

## 快速開始

### 安裝

```bash
# 從 git 安裝（推薦）
pip install 'speech-mcp-echo[recommended] @ git+https://github.com/lukechi1219/speech-mcp-echo.git@v0.2.1'

# 或從 wheel 安裝
pip install 'speech-mcp-echo[recommended] @ https://github.com/lukechi1219/speech-mcp-echo/releases/download/v0.2.1/speech_mcp_echo-0.2.1-py3-none-any.whl'
```

### CLI 整合

#### Claude Code（主要目標）

新增至 `~/.claude.json`：
```json
{
  "mcpServers": {
    "speech-mcp-echo": {
      "command": "speech-mcp-echo"
    }
  }
}
```

**選擇性**：在 `~/.claude/settings.json` 中自動核准語音工具，以避免確認提示：
```json
{
  "permissions": {
    "allow": [
      "mcp__speech-mcp-echo__start_conversation",
      "mcp__speech-mcp-echo__voice_listen",
      "mcp__speech-mcp-echo__voice_speak",
      "mcp__speech-mcp-echo__voice_reply",
      "mcp__speech-mcp-echo__voice_config",
      "mcp__speech-mcp-echo__voice_status",
      "mcp__speech-mcp-echo__start_listening",
      "mcp__speech-mcp-echo__check_listening",
      "mcp__speech-mcp-echo__cancel_listening"
    ]
  }
}
```

然後重新啟動 Claude Code，並說：**「Let's have a voice conversation」**

#### 其他 CLI

**Goose CLI**：
```bash
goose session --with-extension "speech-mcp-echo"
```

**Gemini CLI**：新增至 `~/.gemini/settings.json`（格式同 Claude Code）

**Codex CLI**：新增至 `~/.codex/config.toml`：
```toml
[mcp_servers.speech-mcp-echo]
command = "speech-mcp-echo"
```

## 為什麼選擇這些技術？

### STT：Groq Whisper（推薦）

我們選擇 **Groq Whisper API** 作為推薦的 STT 引擎，原因如下：

- **最準確**：使用 whisper-large-v3-turbo 模型（WER 約 12%，本地 base 模型約 23%）
- **極速**：在 Groq LPU 硬體上達到 216 倍即時速度
- **無本地資源消耗**：不需下載模型，不佔用 GPU/CPU
- **慷慨免費額度**：免費 API，速率限制寬裕
- **簡易設定**：只需設定 `GROQ_API_KEY` 環境變數
- **OpenAI 相容**：使用相同的 `openai` SDK，僅變更 base URL

```bash
# 設定 Groq API 金鑰（在 https://console.groq.com 免費取得）
export GROQ_API_KEY="gsk_..."
```

### STT：faster-whisper（本地替代方案）

**faster-whisper** 適合需要完全離線運作的使用者：

- **輕量化**：約 150MB，相比 OpenAI 原版 whisper 的 1.5GB
- **快速**：使用 CTranslate2 優化，比原版 whisper 快 4 倍
- **離線運作**：完全離線運作，無需 API 費用
- **CPU 友善**：使用 int8 量化在 CPU 上運作良好

### TTS：Google Cloud TTS（推薦）

我們選擇 **Google Cloud TTS** 作為主要 TTS 引擎，原因如下：

- **無繁重依賴**：不像 Kokoro 需要 PyTorch（約 2GB），Google Cloud TTS 使用簡單的 REST API
- **高品質**：具有自然語調的神經網路語音
- **多語言**：優秀支援英文、中文（繁體/簡體）及 40 多種語言
- **彈性驗證**：多種驗證方式（詳見下方）
- **經濟實惠**：免費額度每月包含 400 萬字元
- **跨平台**：支援 macOS、Linux 和 Windows

#### Google Cloud TTS 驗證選項

選擇最適合您設定的方式：

**選項 A：gcloud CLI（推薦開發者使用）**
```bash
# 安裝 gcloud CLI
brew install google-cloud-sdk  # macOS
# 或：https://cloud.google.com/sdk/docs/install

# 登入並設定
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**選項 B：服務帳戶（推薦伺服器/正式環境使用）**
```bash
# 1. 在 Google Cloud Console 建立服務帳戶
#    - 前往 IAM 與管理 > 服務帳戶
#    - 建立具有「Cloud Text-to-Speech API 使用者」角色的帳戶
#    - 下載 JSON 金鑰檔案

# 2. 設定環境變數
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# 3. 選擇性設定專案 ID（如果金鑰檔案中沒有）
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

**選項 C：Python 用戶端程式庫**
```bash
# 安裝程式庫
pip install google-cloud-texttospeech

# 然後使用選項 A 或 B 進行驗證
# 程式庫會自動偵測憑證
```

轉接器會依序嘗試這些方法，並使用第一個成功的方式。

#### 為什麼不用 Kokoro？

Kokoro 是優秀的本地 TTS 引擎，但它需要：
- PyTorch（約 2GB 下載）
- CUDA 以獲得最佳效能
- 額外的語言模型（misaki）

對大多數使用者來說，Google Cloud TTS 以更簡單的設定提供更好的品質。Kokoro 仍可作為偏好完全離線運作的使用者的選擇。

## 設定

設定檔儲存於 `~/.config/speech-mcp-echo/config.json`：

```json
{
  "stt": {
    "engine": "groq",
    "model": "whisper-large-v3-turbo",
    "language": "auto",
    "timeout": 45,
    "silence_retry_count": 10,
    "retry_prompt_type": "beep"
  },
  "tts": {
    "engine": "google",
    "voice": "cmn-TW-Standard-B",
    "language": "cmn-TW"
  },
  "summarizer": {
    "enabled": true,
    "personality": "jarvis",
    "language": "en"
  }
}
```

### 支援的語言

| 語言 | STT (Groq/faster-whisper) | TTS (Google Cloud) |
|------|---------------------------|-------------------|
| 英文 | ✅ | ✅ en-US, en-GB |
| 中文（繁體） | ✅ | ✅ cmn-TW |
| 中文（簡體） | ✅ | ✅ cmn-CN |
| 日文 | ✅ | ✅ ja-JP |

### 環境變數

API 金鑰從環境變數讀取：

- `GROQ_API_KEY` - 用於 Groq Whisper STT（推薦）
- `OPENAI_API_KEY` - 用於 OpenAI Whisper STT 和 TTS
- `GOOGLE_APPLICATION_CREDENTIALS` - 用於 Google Cloud 服務（如果使用 gcloud CLI 則為選用）
- `ANTHROPIC_API_KEY` - 用於基於 Claude 的摘要功能

## 架構

```
src/speech_mcp_echo/
├── __init__.py              # 主要進入點
├── __main__.py              # 模組執行
├── audio_processor.py       # 音訊擷取、播放、提示音
├── constants.py             # 集中管理的常數
├── server.py                # 統一的 MCP 伺服器（所有工具）
├── config/                  # 設定管理
├── core/
│   └── voice_engine.py      # STT、TTS、摘要
├── resources/
│   └── audio/               # 音訊提示檔案（.wav）
├── stt_adapters/            # 語音轉文字引擎
│   ├── groq_whisper_adapter.py    # 雲端（推薦）
│   ├── faster_whisper_adapter.py  # 本地端
│   ├── openai_whisper_adapter.py  # 雲端
│   └── google_speech_adapter.py   # 雲端
├── tts_adapters/            # 文字轉語音引擎
│   ├── google_tts_adapter.py      # 雲端（推薦）
│   └── openai_tts_adapter.py      # 雲端
├── summarizer/              # 回應摘要
│   ├── local_summarizer.py  # 基於規則，具 JARVIS 風格
│   └── llm_summarizer.py    # 基於 LLM（預留位置）
└── utils/
    └── logger.py            # 集中管理的日誌
```

## 開發

```bash
# 複製並以開發模式安裝
git clone https://github.com/lukechi1219/speech-mcp-echo.git
cd speech-mcp-echo
pip install -e ".[dev]"

# 執行測試
pytest tests/
```

## 授權條款

MIT

## 致謝

改編自 [Kvadratni/speech-mcp](https://github.com/Kvadratni/speech-mcp)，加入多 CLI 支援。
