"""
Summarizer module for speech-mcp-echo.

Provides text summarization with optional personality (JARVIS-style).
Reduces long responses to concise, speakable summaries before TTS output.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseSummarizer(ABC):
    """
    Base class for text summarizers.

    All summarizers must implement this interface.
    """

    def __init__(
        self,
        max_input_length: int = 500,
        target_length: int = 150,
        personality: str = "neutral",
        language: str = "en",
    ):
        """
        Initialize the summarizer.

        Args:
            max_input_length: Threshold above which to summarize
            target_length: Target length for summaries
            personality: Personality style (jarvis, neutral)
            language: Output language (en, zh-Hant)
        """
        self.max_input_length = max_input_length
        self.target_length = target_length
        self.personality = personality
        self.language = language

    def should_summarize(self, text: str) -> bool:
        """
        Check if text should be summarized.

        Args:
            text: Input text

        Returns:
            True if text exceeds max_input_length
        """
        return len(text) > self.max_input_length

    @abstractmethod
    def summarize(self, text: str) -> str:
        """
        Summarize the given text.

        Args:
            text: Input text to summarize

        Returns:
            Summarized text
        """
        pass


# Import available summarizers
try:
    from speech_mcp_echo.summarizer.local_summarizer import LocalSummarizer
except ImportError:
    pass

try:
    from speech_mcp_echo.summarizer.llm_summarizer import LLMSummarizer
except ImportError:
    pass
