"""
Local summarizer with JARVIS personality.

Provides rule-based text summarization without requiring external APIs.
Adapted from JARVIS oral summarizer agents.
"""

import re
import logging
from typing import Optional

from speech_mcp_echo.summarizer import BaseSummarizer

logger = logging.getLogger(__name__)

# JARVIS personality templates
JARVIS_TEMPLATES = {
    "en": {
        "greeting": "Right then, {user}.",
        "success": "Done and dusted, {user}. {summary}",
        "error": "Bit of a hiccup here, {user}. {summary}",
        "code": "Ah, code analysis. {summary} Nothing too taxing.",
        "file": "File operations complete. {summary}",
        "info": "{summary}",
        "user_title": "boss",
    },
    "zh-Hant": {
        "greeting": "好的，{user}。",
        "success": "搞定了，{user}。{summary}",
        "error": "遇到點小問題，{user}。{summary}",
        "code": "程式碼分析完成。{summary}",
        "file": "檔案操作完成。{summary}",
        "info": "{summary}",
        "user_title": "少爺",
    },
}

# Neutral templates (no personality)
NEUTRAL_TEMPLATES = {
    "en": {
        "greeting": "",
        "success": "{summary}",
        "error": "Error: {summary}",
        "code": "{summary}",
        "file": "{summary}",
        "info": "{summary}",
        "user_title": "",
    },
    "zh-Hant": {
        "greeting": "",
        "success": "{summary}",
        "error": "錯誤：{summary}",
        "code": "{summary}",
        "file": "{summary}",
        "info": "{summary}",
        "user_title": "",
    },
}


class LocalSummarizer(BaseSummarizer):
    """
    Local rule-based summarizer with optional JARVIS personality.

    Uses extraction and heuristics to create concise summaries.
    No external API calls required.
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
        else:
            self.templates = NEUTRAL_TEMPLATES.get(language, NEUTRAL_TEMPLATES["en"])

    def summarize(self, text: str) -> str:
        """
        Summarize the given text.

        Args:
            text: Input text to summarize

        Returns:
            Summarized text with personality
        """
        if not text:
            return ""

        # Detect content type
        content_type = self._detect_content_type(text)

        # Extract key information
        summary = self._extract_summary(text, content_type)

        # Apply personality template
        template = self.templates.get(content_type, self.templates["info"])
        user_title = self.templates["user_title"]

        result = template.format(summary=summary, user=user_title)

        # Ensure we don't exceed target length too much
        if len(result) > self.target_length * 1.5:
            result = self._truncate_smart(result, self.target_length)

        return result.strip()

    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content for appropriate summarization."""
        text_lower = text.lower()

        # Error detection
        if any(word in text_lower for word in ["error", "failed", "exception", "錯誤", "失敗"]):
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
