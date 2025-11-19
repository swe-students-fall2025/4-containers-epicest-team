"""Tests for speech analysis logic in speech_analysis.py."""

# pylint: disable=redefined-outer-name

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ml_client import speech_analysis

# Mock Whisper's behavior for transcription tests
MOCK_TRANSCRIPTION_RESULT = " Hello, There! "
EXPECTED_CLEANED_TRANSCRIPTION = "hello there"
# NOTE: This test WAV file path will likely fail in a real environment
# unless a test_recordings directory is present and populated.
TEST_WAV_PATH = Path(__file__).resolve().parent / "test_recordings" / "hello_there.wav"


@pytest.fixture
def model_name():
    """Fixture for model name to ensure consistent model use."""
    return "small"

@pytest.fixture
def mock_whisper_model():
    """Mock the Whisper model object to control transcription output."""
    mock_model = Mock()
    mock_model.transcribe.return_value = {"text": MOCK_TRANSCRIPTION_RESULT}
    return mock_model


@patch("ml_client.speech_analysis.whisper.load_model")
def test_load_whisper_model_success(mock_load_model, model_name):
    """Test if the model is loaded correctly by mocking the load operation."""
    # The actual whisper model object is mocked
    mock_model_instance = Mock()
    mock_load_model.return_value = mock_model_instance

    model = speech_analysis.load_whisper_model(model_name)

    mock_load_model.assert_called_once_with(model_name, in_memory=True, device="cpu")
    assert (
        model is mock_model_instance
    ), "Model object returned should be the mock instance."


@patch(
    "ml_client.speech_analysis.whisper.load_model",
    side_effect=RuntimeError("Test Load Fail"),
)
def test_load_whisper_model_failure(model_name):
    """Test if the model load failure raises the expected RuntimeError."""
    with pytest.raises(RuntimeError) as excinfo:
        speech_analysis.load_whisper_model(model_name)
    assert "Unable to load Whisper model" in str(excinfo.value)


def test_transcribe_audio_success(mock_whisper_model):
    """Test transcription function ensures correct text cleaning and output format."""

    # We pass a dummy path since the mock prevents actual file reading
    transcribed_text, transcription_success = speech_analysis.transcribe_audio(
        "/path/to/fake/audio.wav", mock_whisper_model
    )

    # Check transcription was called on the mock model
    mock_whisper_model.transcribe.assert_called_once()

    # Check the cleaning and formatting
    assert (
        transcription_success is True
    ), "Transcription flag should be True on success."
    assert isinstance(
        transcribed_text, str
    ), "Transcription result should be a single string."
    assert (
        transcribed_text == EXPECTED_CLEANED_TRANSCRIPTION
    ), "Text cleaning failed (lowercasing, punctuation, stripping)."


def test_transcribe_audio_failure(mock_whisper_model):
    """Test transcription failure returns the expected failure state."""

    # Simulate an error during transcription (e.g., bad file format, whisper error)
    mock_whisper_model.transcribe.side_effect = ValueError("Corrupt file")

    transcribed_text, transcription_success = speech_analysis.transcribe_audio(
        "/path/to/fake/audio.wav", mock_whisper_model
    )

    assert (
        transcription_success is False
    ), "Transcription flag should be False on failure."
    assert transcribed_text == "Transcription Failed", "Failure message is incorrect."
