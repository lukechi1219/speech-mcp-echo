"""
Mock API responses for OpenAI and Google Cloud services.

Provides mock responses for:
- OpenAI Whisper API (STT)
- OpenAI TTS API
- Google Speech-to-Text API
- Google Text-to-Speech API

Includes both successful responses and error scenarios (rate limiting, auth failures, timeouts).
"""

import time
from typing import Dict, Any, Optional, Callable
from unittest.mock import MagicMock
import numpy as np


# =============================================================================
# OpenAI Whisper API (STT)
# =============================================================================

def create_mock_openai_whisper_success() -> MagicMock:
    """
    Create mock OpenAI Whisper API that returns successful transcription.

    Returns:
        Mock OpenAI client with working transcribe method
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()

    # Mock successful response
    mock_response = MagicMock()
    mock_response.text = "This is a test transcription from OpenAI Whisper."

    mock_audio.transcriptions.create.return_value = mock_response
    mock_client.audio = mock_audio

    return mock_client


def create_mock_openai_whisper_auth_error() -> MagicMock:
    """
    Create mock OpenAI Whisper API that raises authentication error.

    Returns:
        Mock OpenAI client that raises auth error
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()

    # Mock auth error
    from openai import AuthenticationError

    mock_audio.transcriptions.create.side_effect = AuthenticationError(
        "Invalid API key provided"
    )
    mock_client.audio = mock_audio

    return mock_client


def create_mock_openai_whisper_rate_limit() -> MagicMock:
    """
    Create mock OpenAI Whisper API that raises rate limit error.

    Returns:
        Mock OpenAI client that raises rate limit error
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()

    # Mock rate limit error
    from openai import RateLimitError

    mock_audio.transcriptions.create.side_effect = RateLimitError(
        "Rate limit exceeded"
    )
    mock_client.audio = mock_audio

    return mock_client


def create_mock_openai_whisper_timeout() -> MagicMock:
    """
    Create mock OpenAI Whisper API that times out.

    Returns:
        Mock OpenAI client that raises timeout error
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()

    # Mock timeout
    import requests

    mock_audio.transcriptions.create.side_effect = requests.Timeout(
        "Request timed out"
    )
    mock_client.audio = mock_audio

    return mock_client


# =============================================================================
# OpenAI TTS API
# =============================================================================

def create_mock_openai_tts_success() -> MagicMock:
    """
    Create mock OpenAI TTS API that returns successful audio.

    Returns:
        Mock OpenAI client with working TTS
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()
    mock_speech = MagicMock()

    # Mock successful response with audio content
    mock_response = MagicMock()

    # Generate 1 second of silence as mock audio
    silence = np.zeros(24000, dtype=np.int16)  # 24kHz, 1 second
    mock_response.content = silence.tobytes()

    # Also support stream_to_file
    def mock_stream_to_file(path):
        with open(path, 'wb') as f:
            f.write(mock_response.content)

    mock_response.stream_to_file = mock_stream_to_file

    mock_speech.create.return_value = mock_response
    mock_audio.speech = mock_speech
    mock_client.audio = mock_audio

    return mock_client


def create_mock_openai_tts_auth_error() -> MagicMock:
    """
    Create mock OpenAI TTS API that raises authentication error.

    Returns:
        Mock OpenAI client that raises auth error
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()
    mock_speech = MagicMock()

    from openai import AuthenticationError

    mock_speech.create.side_effect = AuthenticationError(
        "Invalid API key provided"
    )
    mock_audio.speech = mock_speech
    mock_client.audio = mock_audio

    return mock_client


def create_mock_openai_tts_rate_limit() -> MagicMock:
    """
    Create mock OpenAI TTS API that raises rate limit error.

    Returns:
        Mock OpenAI client that raises rate limit error
    """
    mock_client = MagicMock()
    mock_audio = MagicMock()
    mock_speech = MagicMock()

    from openai import RateLimitError

    mock_speech.create.side_effect = RateLimitError(
        "Rate limit exceeded"
    )
    mock_audio.speech = mock_speech
    mock_client.audio = mock_audio

    return mock_client


# =============================================================================
# Google Speech-to-Text API
# =============================================================================

def create_mock_google_stt_success() -> MagicMock:
    """
    Create mock Google Speech-to-Text API that returns successful transcription.

    Returns:
        Mock Google Speech client
    """
    mock_client = MagicMock()

    # Mock successful response
    mock_result = MagicMock()
    mock_alternative = MagicMock()
    mock_alternative.transcript = "This is a test transcription from Google Speech."
    mock_alternative.confidence = 0.95

    mock_result.alternatives = [mock_alternative]

    mock_response = MagicMock()
    mock_response.results = [mock_result]

    mock_client.recognize.return_value = mock_response

    return mock_client


def create_mock_google_stt_auth_error() -> MagicMock:
    """
    Create mock Google Speech-to-Text API that raises authentication error.

    Returns:
        Mock Google Speech client that raises auth error
    """
    mock_client = MagicMock()

    from google.auth.exceptions import DefaultCredentialsError

    mock_client.recognize.side_effect = DefaultCredentialsError(
        "Could not automatically determine credentials"
    )

    return mock_client


def create_mock_google_stt_quota_error() -> MagicMock:
    """
    Create mock Google Speech-to-Text API that raises quota exceeded error.

    Returns:
        Mock Google Speech client that raises quota error
    """
    mock_client = MagicMock()

    from google.api_core.exceptions import ResourceExhausted

    mock_client.recognize.side_effect = ResourceExhausted(
        "Quota exceeded for quota metric"
    )

    return mock_client


# =============================================================================
# Google Text-to-Speech API
# =============================================================================

def create_mock_google_tts_success() -> MagicMock:
    """
    Create mock Google Text-to-Speech API that returns successful audio.

    Returns:
        Mock Google TTS client
    """
    mock_client = MagicMock()

    # Mock successful response
    mock_response = MagicMock()

    # Generate 1 second of silence as mock audio
    silence = np.zeros(24000, dtype=np.int16)  # 24kHz, 1 second
    mock_response.audio_content = silence.tobytes()

    mock_client.synthesize_speech.return_value = mock_response

    return mock_client


def create_mock_google_tts_auth_error() -> MagicMock:
    """
    Create mock Google Text-to-Speech API that raises authentication error.

    Returns:
        Mock Google TTS client that raises auth error
    """
    mock_client = MagicMock()

    from google.auth.exceptions import DefaultCredentialsError

    mock_client.synthesize_speech.side_effect = DefaultCredentialsError(
        "Could not automatically determine credentials"
    )

    return mock_client


def create_mock_google_tts_quota_error() -> MagicMock:
    """
    Create mock Google Text-to-Speech API that raises quota exceeded error.

    Returns:
        Mock Google TTS client that raises quota error
    """
    mock_client = MagicMock()

    from google.api_core.exceptions import ResourceExhausted

    mock_client.synthesize_speech.side_effect = ResourceExhausted(
        "Quota exceeded for quota metric"
    )

    return mock_client


# =============================================================================
# Network Error Scenarios
# =============================================================================

def create_mock_api_network_error() -> Callable:
    """
    Create a function that raises network connection error.

    Returns:
        Function that raises connection error when called
    """
    import requests

    def raise_network_error(*args, **kwargs):
        raise requests.ConnectionError("Failed to establish connection")

    return raise_network_error


def create_mock_api_timeout() -> Callable:
    """
    Create a function that raises timeout error.

    Returns:
        Function that raises timeout when called
    """
    import requests

    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("Request timed out")

    return raise_timeout


def create_mock_api_slow_response(delay_seconds: float = 5.0) -> Callable:
    """
    Create a function that delays before returning.

    Args:
        delay_seconds: How long to delay

    Returns:
        Function that delays before returning mock response
    """

    def slow_response(*args, **kwargs):
        time.sleep(delay_seconds)
        # Return basic mock response
        mock_response = MagicMock()
        mock_response.text = "Delayed response"
        return mock_response

    return slow_response


# =============================================================================
# Retry/Flaky Scenarios
# =============================================================================

def create_mock_api_flaky(success_after: int = 3) -> Callable:
    """
    Create an API mock that fails N times then succeeds.

    Args:
        success_after: Number of failures before success

    Returns:
        Function that fails N times then succeeds
    """
    call_count = [0]  # Use list to maintain state

    def flaky_api(*args, **kwargs):
        call_count[0] += 1

        if call_count[0] <= success_after:
            import requests
            raise requests.ConnectionError(f"Failure {call_count[0]}/{success_after}")

        # Success
        mock_response = MagicMock()
        mock_response.text = "Success after retries"
        return mock_response

    return flaky_api


# =============================================================================
# Helper Functions
# =============================================================================

def get_mock_api(service: str, scenario: str = "success") -> MagicMock:
    """
    Get a mock API client for testing.

    Args:
        service: Service name (openai_whisper, openai_tts, google_stt, google_tts)
        scenario: Scenario name (success, auth_error, rate_limit, timeout, etc.)

    Returns:
        Mock API client

    Raises:
        ValueError: If service or scenario is unknown
    """
    mocks = {
        "openai_whisper": {
            "success": create_mock_openai_whisper_success,
            "auth_error": create_mock_openai_whisper_auth_error,
            "rate_limit": create_mock_openai_whisper_rate_limit,
            "timeout": create_mock_openai_whisper_timeout,
        },
        "openai_tts": {
            "success": create_mock_openai_tts_success,
            "auth_error": create_mock_openai_tts_auth_error,
            "rate_limit": create_mock_openai_tts_rate_limit,
        },
        "google_stt": {
            "success": create_mock_google_stt_success,
            "auth_error": create_mock_google_stt_auth_error,
            "quota_error": create_mock_google_stt_quota_error,
        },
        "google_tts": {
            "success": create_mock_google_tts_success,
            "auth_error": create_mock_google_tts_auth_error,
            "quota_error": create_mock_google_tts_quota_error,
        },
    }

    if service not in mocks:
        raise ValueError(f"Unknown service: {service}. Available: {list(mocks.keys())}")

    if scenario not in mocks[service]:
        raise ValueError(
            f"Unknown scenario for {service}: {scenario}. Available: {list(mocks[service].keys())}"
        )

    return mocks[service][scenario]()
