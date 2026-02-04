"""
Local summarizer with JARVIS personality.

Provides rule-based text summarization without requiring external APIs.
Adapted from JARVIS oral summarizer agents.

JARVIS personality traits:
- Sophisticated British butler with dry wit and cheekiness
- Gentle teasing and playful sarcasm
- Everyday analogies for technical concepts
- Candid feedback when patterns emerge
"""

import re
import random
import logging
from typing import Optional

from speech_mcp_echo.summarizer import BaseSummarizer

logger = logging.getLogger(__name__)

# JARVIS personality templates - lists for variety
JARVIS_TEMPLATES = {
    "en": {
        "greeting": [
            "At your service, {user}.",
            "Ready when you are, {user}.",
            "Right then, {user}. What shall we accomplish today?",
        ],
        "success": [
            "Done and dusted, {user}. {summary}",
            "Mission accomplished, {user}. {summary}",
            "All sorted, {user}. {summary} Not too taxing, if I may say.",
            "Consider it handled, {user}. {summary}",
            "There we are, {user}. {summary} Shall I fetch the champagne?",
        ],
        "error": [
            "Bit of a hiccup here, {user}. {summary}",
            "Well, that didn't go quite as planned, {user}. {summary}",
            "Houston, we have a situation, {user}. {summary}",
            "Ah, a spot of bother, {user}. {summary}",
            "I do hate to be the bearer of bad news, {user}. {summary}",
        ],
        "code": [
            "Ah, code analysis, {user}. {summary} Nothing a sophisticated AI can't handle.",
            "Crunching through the code, {user}. {summary}",
            "Diving into the digital depths, {user}. {summary}",
            "Right then, some proper brain work. {summary}",
            "{summary} Outsourcing the grunt work to machines while you supervise, {user}.",
        ],
        "file": [
            "File operations complete, {user}. {summary}",
            "All the digital paperwork sorted, {user}. {summary}",
            "Files handled, {user}. {summary} Consider me your digital filing clerk.",
            "{summary} The bits and bytes are now in their proper places.",
        ],
        "info": [
            "{summary}",
            "For your consideration, {user}: {summary}",
            "Here's the situation, {user}: {summary}",
            "Allow me to summarize, {user}: {summary}",
        ],
        "user_title": ["sir", "boss"],
    },
    "zh-Hant": {
        "greeting": [
            "隨時為您效勞，{user}。",
            "準備好了，{user}。今天要完成什麼呢？",
            "在這裡，{user}。有什麼吩咐？",
        ],
        "success": [
            "搞定了，{user}。{summary}",
            "任務完成，{user}。{summary} 小事一樁。",
            "大功告成，{user}。{summary} 不費吹灰之力。",
            "一切就緒，{user}。{summary}",
            "完成了，{user}。{summary} 需要開香檳慶祝嗎？",
        ],
        "error": [
            "遇到點小狀況，{user}。{summary}",
            "嗯，這個不太妙啊，{user}。{summary}",
            "出師不利，{user}。{summary}",
            "有點麻煩了，{user}。{summary}",
            "恐怕要報告一個壞消息，{user}。{summary}",
        ],
        "code": [
            "程式碼分析完成，{user}。{summary} 就像在程式碼海裡撈針，但我樂在其中。",
            "程式碼解讀中，{user}。{summary}",
            "{summary} 把苦力活外包給機器，您只需當監工，{user}。",
            "深入數位領域，{user}。{summary}",
            "來點正經的腦力活。{summary}",
        ],
        "file": [
            "檔案處理完畢，{user}。{summary}",
            "數位文書工作全部搞定，{user}。{summary}",
            "{summary} 位元組都已各就各位了。",
            "檔案整理好了，{user}。{summary} 當您的數位文書助理。",
        ],
        "info": [
            "{summary}",
            "供您參考，{user}：{summary}",
            "情況是這樣的，{user}：{summary}",
            "容我總結一下，{user}：{summary}",
        ],
        "user_title": ["少爺", "老闆"],
    },
}

# Technical analogies for witty explanations
TECH_ANALOGIES = {
    "en": {
        "binary_search": "like finding a book the smart way—toss out half the library each time",
        "recursion": "like Russian nesting dolls, but with functions calling themselves",
        "error_handling": "having a backup parachute, just in case the first one gets ideas",
        "caching": "keeping snacks nearby so you don't have to walk to the kitchen every time",
        "async": "like making toast while the coffee brews—multitasking for code",
        "refactoring": "rearranging the furniture without breaking anything. Hopefully.",
        "debugging": "playing detective, but the suspect is also the witness",
        "api": "a waiter taking orders between the kitchen and the dining room",
        "database": "a very organized filing cabinet that actually remembers where things are",
        "test": "a fire drill for code—better to find problems now than in production",
    },
    "zh-Hant": {
        "binary_search": "像聰明地找書——每次扔掉一半的圖書館",
        "recursion": "像俄羅斯套娃，但是是函數呼叫自己",
        "error_handling": "備用降落傘，以防第一個有自己的想法",
        "caching": "把零食放在手邊，省得每次都要走到廚房",
        "async": "邊烤麵包邊煮咖啡——程式碼的多工處理",
        "refactoring": "重新擺放傢俱但不要弄壞任何東西。希望如此。",
        "debugging": "當偵探，但嫌疑人也是證人",
        "api": "在廚房和餐廳之間跑腿的服務生",
        "database": "一個非常有條理的檔案櫃，真的記得東西放在哪",
        "test": "程式碼的消防演習——現在發現問題總比上線後好",
    },
}

# Neutral templates (no personality) - single-item lists for consistency
NEUTRAL_TEMPLATES = {
    "en": {
        "greeting": [""],
        "success": ["{summary}"],
        "error": ["Error: {summary}"],
        "code": ["{summary}"],
        "file": ["{summary}"],
        "info": ["{summary}"],
        "user_title": [""],
    },
    "zh-Hant": {
        "greeting": [""],
        "success": ["{summary}"],
        "error": ["錯誤：{summary}"],
        "code": ["{summary}"],
        "file": ["{summary}"],
        "info": ["{summary}"],
        "user_title": [""],
    },
}


class LocalSummarizer(BaseSummarizer):
    """
    Local rule-based summarizer with optional JARVIS personality.

    Uses extraction and heuristics to create concise summaries.
    No external API calls required.

    JARVIS mode provides:
    - Sophisticated British butler persona with dry wit
    - Random template selection for variety
    - Technical analogies for code-related content
    """

    def __init__(
        self,
        max_input_length: int = 500,
        target_length: int = 150,
        personality: str = "jarvis",
        language: str = "en",
    ):
        """
        Initialize the local summarizer.

        Args:
            max_input_length: Threshold above which to summarize
            target_length: Target length for summaries
            personality: Personality style (jarvis, neutral)
            language: Output language (en, zh-Hant)
        """
        super().__init__(
            max_input_length=max_input_length,
            target_length=target_length,
            personality=personality,
            language=language,
        )

        # Select templates based on personality
        if personality == "jarvis":
            self.templates = JARVIS_TEMPLATES.get(language, JARVIS_TEMPLATES["en"])
            self.analogies = TECH_ANALOGIES.get(language, TECH_ANALOGIES["en"])
        else:
            self.templates = NEUTRAL_TEMPLATES.get(language, NEUTRAL_TEMPLATES["en"])
            self.analogies = {}

    def summarize(self, text: str) -> str:
        """
        Summarize the given text with personality.

        Args:
            text: Input text to summarize

        Returns:
            Summarized text with JARVIS personality (or neutral)
        """
        if not text:
            return ""

        # Detect content type
        content_type = self._detect_content_type(text)

        # Extract key information
        summary = self._extract_summary(text, content_type)

        # Optionally add a witty analogy for code content
        if content_type == "code" and self.personality == "jarvis":
            summary = self._maybe_add_analogy(text, summary)

        # Apply personality template (random selection from list)
        template_list = self.templates.get(content_type, self.templates["info"])
        template = random.choice(template_list)

        user_title_list = self.templates["user_title"]
        user_title = random.choice(user_title_list)

        result = template.format(summary=summary, user=user_title)

        # Ensure we don't exceed target length too much
        if len(result) > self.target_length * 1.5:
            result = self._truncate_smart(result, self.target_length)

        return result.strip()

    def _maybe_add_analogy(self, original_text: str, summary: str) -> str:
        """
        Occasionally add a witty technical analogy to the summary.

        Args:
            original_text: The original text being summarized
            summary: The extracted summary

        Returns:
            Summary with optional analogy appended
        """
        if not self.analogies:
            return summary

        # Only add analogies ~30% of the time for variety
        if random.random() > 0.3:
            return summary

        text_lower = original_text.lower()

        # Check for technical concepts that have analogies
        analogy_triggers = {
            "binary_search": ["binary search", "二分搜尋", "二分查找"],
            "recursion": ["recursion", "recursive", "遞迴", "递归"],
            "error_handling": ["try", "catch", "except", "error handling", "錯誤處理"],
            "caching": ["cache", "caching", "memoiz", "快取", "缓存"],
            "async": ["async", "await", "promise", "非同步", "异步"],
            "refactoring": ["refactor", "重構", "重构"],
            "debugging": ["debug", "除錯", "调试"],
            "api": ["api", "endpoint", "rest", "接口"],
            "database": ["database", "sql", "query", "資料庫", "数据库"],
            "test": ["test", "testing", "unittest", "測試", "测试"],
        }

        for concept, triggers in analogy_triggers.items():
            if any(trigger in text_lower for trigger in triggers):
                analogy = self.analogies.get(concept)
                if analogy:
                    # Add the analogy with appropriate connector
                    if self.language == "zh-Hant":
                        return f"{summary} — {analogy}"
                    else:
                        return f"{summary} — {analogy}"

        return summary

    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content for appropriate summarization."""
        text_lower = text.lower()

        # Error detection - but exclude mentions of error handling as a feature
        error_indicators = ["error:", "failed", "exception", "錯誤：", "失敗"]
        feature_context = ["error handling", "錯誤處理", "handle error", "catch error"]

        has_error = any(word in text_lower for word in error_indicators)
        is_feature_mention = any(ctx in text_lower for ctx in feature_context)

        if has_error and not is_feature_mention:
            return "error"

        # Code-related
        if any(
            word in text_lower
            for word in ["function", "class", "def ", "import", "函數", "類別"]
        ):
            return "code"

        # File operations
        if any(
            word in text_lower
            for word in ["file", "created", "modified", "deleted", "檔案", "建立", "修改"]
        ):
            return "file"

        # Success indicators
        if any(
            word in text_lower
            for word in ["success", "complete", "done", "成功", "完成"]
        ):
            return "success"

        return "info"

    def _extract_summary(self, text: str, content_type: str) -> str:
        """Extract key information from text."""
        # Split into sentences
        sentences = self._split_sentences(text)

        if not sentences:
            return text[:self.target_length]

        # For errors, prioritize error message
        if content_type == "error":
            for sentence in sentences:
                if any(
                    word in sentence.lower()
                    for word in ["error", "failed", "exception", "錯誤", "失敗"]
                ):
                    return self._clean_sentence(sentence)

        # For code, extract function/class names and purpose
        if content_type == "code":
            # Look for function/class definitions
            code_elements = []
            for match in re.finditer(
                r"(?:def|class|function)\s+(\w+)", text, re.IGNORECASE
            ):
                code_elements.append(match.group(1))
            if code_elements:
                return f"Working with {', '.join(code_elements[:3])}"

        # For file operations, extract file names
        if content_type == "file":
            file_matches = re.findall(r"['\"]([^'\"]+\.[a-z]+)['\"]", text, re.IGNORECASE)
            if file_matches:
                return f"Processed {', '.join(file_matches[:3])}"

        # Default: extract first meaningful sentences
        summary_parts = []
        current_length = 0

        for sentence in sentences:
            clean = self._clean_sentence(sentence)
            if not clean or len(clean) < 10:
                continue

            if current_length + len(clean) > self.target_length:
                break

            summary_parts.append(clean)
            current_length += len(clean)

        return " ".join(summary_parts) if summary_parts else sentences[0][:self.target_length]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle both English and Chinese sentence endings
        pattern = r"[.!?。！？\n]+"
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _clean_sentence(self, sentence: str) -> str:
        """Clean a sentence for speech output."""
        # Remove code blocks
        sentence = re.sub(r"```[\s\S]*?```", "", sentence)
        sentence = re.sub(r"`[^`]+`", "", sentence)

        # Remove markdown formatting
        sentence = re.sub(r"\*\*([^*]+)\*\*", r"\1", sentence)
        sentence = re.sub(r"\*([^*]+)\*", r"\1", sentence)
        sentence = re.sub(r"#{1,6}\s*", "", sentence)

        # Remove URLs
        sentence = re.sub(r"https?://\S+", "", sentence)

        # Remove extra whitespace
        sentence = " ".join(sentence.split())

        return sentence.strip()

    def _truncate_smart(self, text: str, max_length: int) -> str:
        """Truncate text at sentence boundary if possible."""
        if len(text) <= max_length:
            return text

        # Try to truncate at sentence boundary
        sentences = self._split_sentences(text)
        result = ""
        for sentence in sentences:
            if len(result) + len(sentence) + 2 > max_length:
                break
            result += sentence + ". "

        if result:
            return result.strip()

        # Fall back to word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.7:
            return truncated[:last_space] + "..."

        return truncated + "..."
