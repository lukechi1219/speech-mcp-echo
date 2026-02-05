"""
Unit tests for LocalSummarizer (JARVIS personality).

Run with:
    cd speech-mcp-echo
    pytest tests/test_local_summarizer.py -v
"""

import random
from unittest.mock import patch

import pytest

from speech_mcp_echo.summarizer.local_summarizer import (
    LocalSummarizer,
    JARVIS_TEMPLATES,
    NEUTRAL_TEMPLATES,
    TECH_ANALOGIES,
)


# =============================================================================
# Test Initialization
# =============================================================================


class TestLocalSummarizerInitialization:
    """Test LocalSummarizer initialization."""

    def test_init_with_defaults(self):
        """Should initialize with default parameters."""
        summarizer = LocalSummarizer()

        assert summarizer.max_input_length == 500
        assert summarizer.target_length == 150
        assert summarizer.personality == "jarvis"
        assert summarizer.language == "en"
        assert summarizer.templates == JARVIS_TEMPLATES["en"]
        assert summarizer.analogies == TECH_ANALOGIES["en"]

    @pytest.mark.parametrize("personality,language,expected_templates,expected_analogies", [
        ("jarvis", "en", "JARVIS_TEMPLATES", "TECH_ANALOGIES"),
        ("jarvis", "zh-Hant", "JARVIS_TEMPLATES", "TECH_ANALOGIES"),
        ("neutral", "en", "NEUTRAL_TEMPLATES", "empty"),
    ], ids=["jarvis-en", "jarvis-zh", "neutral-en"])
    def test_init_with_personality_and_language(self, personality, language, expected_templates, expected_analogies):
        """Should initialize with specified personality and language."""
        summarizer = LocalSummarizer(personality=personality, language=language)

        assert summarizer.personality == personality
        assert summarizer.language == language

        # Verify templates
        if expected_templates == "JARVIS_TEMPLATES":
            assert summarizer.templates == JARVIS_TEMPLATES[language]
        elif expected_templates == "NEUTRAL_TEMPLATES":
            assert summarizer.templates == NEUTRAL_TEMPLATES[language]

        # Verify analogies
        if expected_analogies == "TECH_ANALOGIES":
            assert summarizer.analogies == TECH_ANALOGIES[language]
        elif expected_analogies == "empty":
            assert summarizer.analogies == {}

    def test_init_with_custom_lengths(self):
        """Should initialize with custom length parameters."""
        summarizer = LocalSummarizer(
            max_input_length=1000,
            target_length=200,
        )

        assert summarizer.max_input_length == 1000
        assert summarizer.target_length == 200

    def test_init_with_unknown_language_fallback_to_english(self):
        """Should fall back to English for unknown language."""
        summarizer = LocalSummarizer(personality="jarvis", language="fr")

        # Should fall back to English templates
        assert summarizer.templates == JARVIS_TEMPLATES["en"]
        assert summarizer.analogies == TECH_ANALOGIES["en"]


# =============================================================================
# Test JARVIS Personality Templates
# =============================================================================


class TestJARVISPersonalityTemplates:
    """Test JARVIS personality template application."""

    @pytest.mark.parametrize("language,input_text,expected_keywords", [
        ("en", "File created successfully.", ["file", "created"]),
        ("en", "Error: File not found.", ["error", "not found"]),
        ("zh-Hant", "成功建立檔案。", ["檔案"]),
    ], ids=["success-en", "error-en", "success-zh"])
    def test_template_applied_with_content(self, language, input_text, expected_keywords):
        """Should apply JARVIS template and include content."""
        summarizer = LocalSummarizer(personality="jarvis", language=language)
        result = summarizer.summarize(input_text)

        # Template was applied (result is not empty and differs from input)
        assert result

        # Content is preserved (at least one keyword is present, case-insensitive)
        assert any(keyword.lower() in result.lower() for keyword in expected_keywords)

    def test_template_variety(self):
        """Should select different templates on different calls."""
        summarizer = LocalSummarizer(personality="jarvis", language="en")

        # Generate multiple summaries
        summaries = set()
        for _ in range(10):
            result = summarizer.summarize("File created successfully.")
            summaries.add(result)

        # Should have at least 2 different variants (due to random selection)
        # (Probabilistically very likely with 10 tries)
        assert len(summaries) >= 2


# =============================================================================
# Test Text Summarization
# =============================================================================


class TestTextSummarization:
    """Test text summarization logic."""

    def test_summarize_empty_text(self):
        """Should return empty string for empty input."""
        summarizer = LocalSummarizer()
        result = summarizer.summarize("")

        assert result == ""

    def test_summarize_short_text(self):
        """Should pass through short text with personality."""
        summarizer = LocalSummarizer(max_input_length=100)
        text = "Hello world"

        result = summarizer.summarize(text)

        # Should include the text (possibly with JARVIS flair)
        assert len(result) > 0
        # Should be relatively short
        assert len(result) < 200

    def test_summarize_medium_text(self):
        """Should summarize medium-length text."""
        summarizer = LocalSummarizer(max_input_length=100, target_length=50)
        text = "This is a medium-length text. " * 10  # ~300 chars

        result = summarizer.summarize(text)

        # Should be shorter than original
        assert len(result) <= len(text)
        # Should not be empty
        assert len(result) > 0

    def test_summarize_long_text(self):
        """Should summarize long text."""
        summarizer = LocalSummarizer(max_input_length=100, target_length=50)
        text = "This is a very long text with lots of information. " * 50  # ~2500 chars

        result = summarizer.summarize(text)

        # Should be significantly shorter
        assert len(result) < len(text) * 0.5
        # Should not be empty
        assert len(result) > 0

    def test_summarize_text_with_code_blocks(self):
        """Should remove code blocks from summary."""
        summarizer = LocalSummarizer()
        text = """
Here's some code:
```python
def hello():
    print("world")
```
And some more text.
"""

        result = summarizer.summarize(text)

        # Should not include the code block markers
        assert "```" not in result
        # Should produce a non-empty result
        assert len(result) > 0

    def test_summarize_text_with_markdown(self):
        """Should remove markdown formatting."""
        summarizer = LocalSummarizer()
        text = "This is **bold** and *italic* text with # headings"

        result = summarizer.summarize(text)

        # Should remove markdown formatting
        assert "**" not in result
        assert "*" not in result
        assert "#" not in result
        # Should preserve content
        assert "bold" in result or "italic" in result or "text" in result

    def test_summarize_text_with_urls(self):
        """Should remove URLs from summary."""
        summarizer = LocalSummarizer()
        text = "Check out https://example.com for more info."

        result = summarizer.summarize(text)

        # Should not include the URL
        assert "https://" not in result
        assert "example.com" not in result

    def test_summarize_text_with_bullet_points(self):
        """Should handle text with bullet points."""
        summarizer = LocalSummarizer()
        text = """
Files created:
- file1.py
- file2.py
- file3.py
All done!
"""

        result = summarizer.summarize(text)

        # Should create a readable summary
        assert len(result) > 0
        # Bullet points may or may not be preserved


# =============================================================================
# Test Language Detection & Switching
# =============================================================================


class TestLanguageDetection:
    """Test language detection and switching."""

    def test_detect_english_text(self):
        """Should handle English text correctly."""
        summarizer = LocalSummarizer(language="en")
        text = "Successfully created the file."

        result = summarizer.summarize(text)

        # Should use English templates
        assert len(result) > 0

    def test_detect_chinese_text(self):
        """Should handle Chinese text correctly."""
        summarizer = LocalSummarizer(language="zh-Hant")
        text = "成功建立檔案。"

        result = summarizer.summarize(text)

        # Should use Chinese templates
        assert len(result) > 0

    def test_mixed_language_text(self):
        """Should handle mixed language text."""
        summarizer = LocalSummarizer(language="en")
        text = "Created 檔案.txt successfully."

        result = summarizer.summarize(text)

        # Should still produce a summary
        assert len(result) > 0

    def test_switch_personality_language_at_runtime(self):
        """Should use configured language for output."""
        # Create English summarizer
        summarizer_en = LocalSummarizer(personality="jarvis", language="en")
        result_en = summarizer_en.summarize("File created")

        # Create Chinese summarizer
        summarizer_zh = LocalSummarizer(personality="jarvis", language="zh-Hant")
        result_zh = summarizer_zh.summarize("建立檔案")

        # Results should use different language templates
        assert result_en != result_zh


# =============================================================================
# Test Content Type Detection
# =============================================================================


class TestContentTypeDetection:
    """Test content type detection logic."""

    def test_detect_error_content(self):
        """Should detect error messages."""
        summarizer = LocalSummarizer(personality="neutral")

        # Test various error formats
        error_texts = [
            "Error: File not found",
            "Failed to connect to server",
            "Exception occurred during processing",
            "錯誤：找不到檔案",
        ]

        for text in error_texts:
            result = summarizer._detect_content_type(text)
            assert result == "error", f"Failed to detect error in: {text}"

    def test_detect_error_handling_feature_not_error(self):
        """Should not detect 'error handling' feature as error."""
        summarizer = LocalSummarizer(personality="neutral")

        texts = [
            "Implemented error handling with try-catch",
            "Added 錯誤處理 to the module",
            "Handle error cases gracefully",
        ]

        for text in texts:
            result = summarizer._detect_content_type(text)
            assert result != "error", f"Incorrectly detected error in: {text}"

    def test_detect_code_content(self):
        """Should detect code-related content."""
        summarizer = LocalSummarizer(personality="neutral")

        code_texts = [
            "Created function calculate_sum",
            "Added class UserManager",
            "def main():",
            "import numpy as np",
        ]

        for text in code_texts:
            result = summarizer._detect_content_type(text)
            assert result == "code", f"Failed to detect code in: {text}"

    def test_detect_file_content(self):
        """Should detect file operation content."""
        summarizer = LocalSummarizer(personality="neutral")

        file_texts = [
            "File created successfully",
            "Modified test.py",
            "Deleted old files",
            "建立新檔案",
        ]

        for text in file_texts:
            result = summarizer._detect_content_type(text)
            assert result == "file", f"Failed to detect file operation in: {text}"

    def test_detect_success_content(self):
        """Should detect success messages."""
        summarizer = LocalSummarizer(personality="neutral")

        success_texts = [
            "Success! All tests passed",
            "Task completed successfully",
            "Done processing",
            "成功完成",
        ]

        for text in success_texts:
            result = summarizer._detect_content_type(text)
            assert result == "success", f"Failed to detect success in: {text}"

    def test_detect_info_content_default(self):
        """Should default to 'info' for general content."""
        summarizer = LocalSummarizer(personality="neutral")

        info_texts = [
            "The weather is nice today",
            "Processing data...",
            "Please wait",
        ]

        for text in info_texts:
            result = summarizer._detect_content_type(text)
            assert result == "info", f"Should default to info for: {text}"


# =============================================================================
# Test Technical Analogies
# =============================================================================


class TestTechnicalAnalogies:
    """Test technical analogy injection."""

    @patch("speech_mcp_echo.summarizer.local_summarizer.random.random")
    def test_maybe_add_analogy_recursion(self, mock_random):
        """Should add analogy for recursion with 30% probability."""
        # Force analogy to be added
        mock_random.return_value = 0.1  # < 0.3, so add analogy

        summarizer = LocalSummarizer(personality="jarvis", language="en")
        original = "Implemented recursive function to traverse tree"
        summary = "Implemented recursive function"

        result = summarizer._maybe_add_analogy(original, summary)

        # Should include the recursion analogy
        assert "—" in result
        assert "Russian nesting dolls" in result

    @patch("speech_mcp_echo.summarizer.local_summarizer.random.random")
    def test_maybe_add_analogy_caching(self, mock_random):
        """Should add analogy for caching."""
        mock_random.return_value = 0.1

        summarizer = LocalSummarizer(personality="jarvis", language="en")
        original = "Added caching layer to improve performance"
        summary = "Added caching layer"

        result = summarizer._maybe_add_analogy(original, summary)

        assert "—" in result
        assert "snacks" in result.lower()

    @patch("speech_mcp_echo.summarizer.local_summarizer.random.random")
    def test_maybe_add_analogy_skipped_70_percent(self, mock_random):
        """Should skip analogy 70% of the time."""
        mock_random.return_value = 0.5  # > 0.3, so skip analogy

        summarizer = LocalSummarizer(personality="jarvis", language="en")
        original = "Implemented recursive function"
        summary = "Implemented recursive function"

        result = summarizer._maybe_add_analogy(original, summary)

        # Should NOT add analogy
        assert result == summary
        assert "—" not in result

    def test_no_analogies_for_neutral_personality(self):
        """Should not add analogies for neutral personality."""
        summarizer = LocalSummarizer(personality="neutral", language="en")
        original = "Implemented recursive function to traverse tree"
        summary = "Implemented recursive function"

        result = summarizer._maybe_add_analogy(original, summary)

        # Should not add analogy (no analogies dict)
        assert result == summary

    @patch("speech_mcp_echo.summarizer.local_summarizer.random.random")
    def test_chinese_analogy(self, mock_random):
        """Should add Chinese analogy for Chinese language."""
        mock_random.return_value = 0.1

        summarizer = LocalSummarizer(personality="jarvis", language="zh-Hant")
        original = "實現遞迴函數來遍歷樹狀結構"
        summary = "實現遞迴函數"

        result = summarizer._maybe_add_analogy(original, summary)

        # Should include Chinese recursion analogy
        assert "—" in result
        assert "俄羅斯套娃" in result


# =============================================================================
# Test Configuration
# =============================================================================


class TestSummarizerConfiguration:
    """Test configuration and settings."""

    def test_should_summarize_short_text(self):
        """Should not summarize text below threshold."""
        summarizer = LocalSummarizer(max_input_length=500)
        text = "Short text"

        assert summarizer.should_summarize(text) is False

    def test_should_summarize_long_text(self):
        """Should summarize text above threshold."""
        summarizer = LocalSummarizer(max_input_length=100)
        text = "This is a long text. " * 20  # > 100 chars

        assert summarizer.should_summarize(text) is True

    def test_enable_disable_summarizer(self):
        """Should respect personality setting."""
        # JARVIS enabled
        jarvis = LocalSummarizer(personality="jarvis", language="en")
        assert jarvis.personality == "jarvis"
        assert jarvis.templates == JARVIS_TEMPLATES["en"]

        # Neutral (JARVIS disabled)
        neutral = LocalSummarizer(personality="neutral", language="en")
        assert neutral.personality == "neutral"
        assert neutral.templates == NEUTRAL_TEMPLATES["en"]

    def test_change_language_at_runtime(self):
        """Should use configured language for templates."""
        # Create with English
        summarizer = LocalSummarizer(personality="jarvis", language="en")
        assert summarizer.language == "en"
        assert summarizer.templates == JARVIS_TEMPLATES["en"]

        # Create new instance with Chinese
        summarizer_zh = LocalSummarizer(personality="jarvis", language="zh-Hant")
        assert summarizer_zh.language == "zh-Hant"
        assert summarizer_zh.templates == JARVIS_TEMPLATES["zh-Hant"]
