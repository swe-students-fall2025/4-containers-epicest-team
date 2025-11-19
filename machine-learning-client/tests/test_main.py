"""Pytest suite for the ML client (main.py)."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Import app components after path fix
# type: ignore[import]
from main import app, startup_event

# --- Fixtures ---


@pytest.fixture(scope="module", name="ml_client")
def fixture_ml_client():
    """Create a FastAPI TestClient for the main app."""
    # We skip the startup event that loads the real Whisper model
    with patch("main.startup_event"):
        with TestClient(app) as client:
            yield client


@pytest.fixture(name="mock_speech_analysis")
def fixture_mock_speech_analysis():
    """Patch the transcription function to control the ML result."""
    with patch("main.speech_analysis") as mock_sa:
        # Mock the load_whisper_model used in main.py for model loading
        mock_sa.load_whisper_model.return_value = Mock()
        # Mock the transcribe_audio helper for the actual transcription result
        mock_sa.transcribe_audio.return_value = ("hello there", True)
        yield mock_sa


@pytest.fixture(name="mock_mongo_db")
def fixture_mock_mongo_db():
    """Patch the MongoDB connection and insert method."""
    with patch("main.mongo_db") as mock_db:
        mock_db.__getitem__.return_value.insert_one.return_value = Mock()
        yield mock_db


# --- Tests ---


def test_ml_client_startup_event_loads_model():
    """Test that the startup event attempts to load the model."""
    with patch("main.speech_analysis.load_whisper_model") as mock_load:
        # Import main again to trigger the
        #startup event logic (if not done by FastAPI)
        # We manually call the decorated function
        #since TestClient doesn't run startup events by default
        startup_event()
        mock_load.assert_called_once()


def test_transcribe_endpoint_success(ml_client, mock_speech_analysis, mock_mongo_db):
    """POST /transcribe should successfully transcribe and return data."""
    test_user_id = "test_ml_user"

    # Create a dummy file for upload
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        f.write(b"RIFF\x24\x00\x00\x00WAVEdata\x00\x00\x00\x00")
        f.seek(0)

        response = ml_client.post(
            "/transcribe",
            data={"user_id": test_user_id},
            files={"audio": ("test_audio.wav", f, "audio/wav")},
        )

    # Check the transcription function was called
    assert mock_speech_analysis.transcribe_audio.called is True

    # Check the database insert was attempted
    assert mock_mongo_db.__getitem__.return_value.insert_one.called is True

    # Check the response structure
    assert response.status_code == 200
    data = response.json()
    assert data["transcription"] == "hello there"
    assert data["transcription_success"] is True

    # Check cleanup: the temporary file created should have been saved in AUDIO_DIR
    # We just check the transcribe_audio was called with a path
    call_args = mock_speech_analysis.transcribe_audio.call_args[0]
    uploaded_path = call_args[0]
    assert os.path.exists(uploaded_path) is True
    # Clean up the file created by the endpoint logic
    os.remove(uploaded_path)


def test_transcribe_endpoint_no_audio_file(ml_client, mock_speech_analysis):
    """POST /transcribe should fail if audio file is missing."""
    response = ml_client.post("/transcribe", data={"user_id": "test_ml_user"})
    assert (
        response.status_code == 422
    )  # Unprocessable Entity (FastAPI validation error)
    # The transcription process should not have been called
    assert mock_speech_analysis.transcribe_audio.called is False
