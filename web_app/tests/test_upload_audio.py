# pylint: disable=wrong-import-position, import-error

import sys
from pathlib import Path
import io
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from web_app.app import create_app  # noqa: E402
from web_app.app import USERS  # noqa: E402


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(app, client):
    USERS["testuser"] = {"password_hash": ""}
    with client.session_transaction() as sess:
        sess["_user_id"] = "testuser"
    return client


def test_upload_audio_no_file(logged_in_client):
    """POST without an audio file should return 400."""
    response = logged_in_client.post("/api/upload-audio")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_upload_audio_valid_file(monkeypatch, logged_in_client):
    """POST with a valid audio file should call stub transcription."""

    # Patch the stub to confirm it's invoked
    monkeypatch.setattr(
        "web_app.app.transcribe_audio", lambda f: "stubbed transcription"
    )

    data = {"audio_file": (io.BytesIO(b"fakeaudio"), "recording.webm", "audio/webm")}

    response = logged_in_client.post(
        "/api/upload-audio", data=data, content_type="multipart/form-data"
    )

    assert response.status_code == 200

    json_data = response.get_json()
    assert json_data["recognized_text"] == "stubbed transcription"


def test_upload_audio_rejects_non_binary(logged_in_client):
    """
    If 'audio_file' is present but is not a binary file or is empty,
    the endpoint should return HTTP 400.
    """
    fake_file = io.BytesIO(b"this is not audio data")

    # Simulate a text file instead of audio
    data = {"audio_file": (fake_file, "bad.txt")}

    response = logged_in_client.post(
        "/api/upload-audio", data=data, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data
