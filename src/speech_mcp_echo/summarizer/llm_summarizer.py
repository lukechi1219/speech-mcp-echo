"""
LLM-based summarizer for speech-mcp-echo.

Uses Claude or OpenAI for intelligent summarization.
TODO: Implement LLM integration.
"""

import logging
from typing import Optional

from speech_mcp_echo.summarizer import BaseSummarizer

logger = logging.getLogger(__name__)


class LLMSummarizer(BaseSummarizer):
    """
    LLM-based summarizer.

    Uses Claude or OpenAI API for intelligent summarization
    with JARVIS personality.
    """

    def __init__(
        self,
        max_input_length: int = 500,
        target_length: int = 150,
        personality: str = "jarvis",
        language: str = "en",
        provider: str = "anthropic",  # anthropic or openai
    ):
        super().__init__(
            max_input_length=max_input_length,
            target_length=target_length,
            personality=personality,
            language=language,
        )
        self.provider = provider

    def summarize(self, text: str) -> str:
        """
        Summarize using LLM.

        Args:
            text: Input text

        Returns:
            Summarized text with personality
        """
        # TODO: Implement LLM-based summarization
        # For now, fall back to local summarizer
        from speech_mcp_echo.summarizer.local_summarizer import LocalSummarizer

        local = LocalSummarizer(
            max_input_length=self.max_input_length,
            target_length=self.target_length,
            personality=self.personality,
            language=self.language,
        )
        return local.summarize(text)
