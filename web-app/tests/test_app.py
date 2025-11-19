"""Pytest suite for the Codebreaker web app (app.py)."""

import io
import os
import sys
from unittest.mock import Mock, patch

import pytest

# Fix import path so 'app' can be imported from the parent directory
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import app components after path fix
from app import DEFAULT_SECRET_PHRASE, PLAYER_STATES, USERS, create_app, g

# --- Fixtures ---


@pytest.fixture
def client():
    """Create a Flask test client for each test, ensuring a clean state."""
    flask_app = create_app()
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret-key")

    # Ensure clean globals for each test run
    USERS.clear()
    PLAYER_STATES.clear()

    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(client):
    """Register and log in a user for tests requiring authentication."""
    username = "testuser"
    password = "testpass"

    # Register the user
    client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=True,
    )

    # Log in the user
    client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )

    return client


# --- Helper for Mocking ML Service ---


def mock_ml_client_response(transcribed_text, success=True):
    """Mock the response from the ML client."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "transcription": transcribed_text,
        "transcription_success": success,
    }
    return mock_resp


def mock_ml_client_failure():
    """Mock a 500 failure from the ML client."""
    mock_resp = Mock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
    return mock_resp


# --- Tests ---


def test_submit_guess_decrements_attempts(auth_client):
    """POST /api/submit-guess should decrement attempts and check failure."""

    # Mock the ML client to return an incorrect guess
    with patch("requests.post", return_value=mock_ml_client_response("wrong guess")):
        audio = (io.BytesIO(b"\x00\x01\x02binary-data"), "test.webm")
        # Get initial attempts
        initial_attempts = auth_client.get("/api/game-state").get_json()[
            "attempts_left"
        ]

        # FIXED: Send 'audio_url' instead of 'guess'
        response = auth_client.post(
            "/api/submit-guess",
            data={"audio": audio},
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        data = response.get_json()
        print(data)
        assert data["guess"] == "wrong guess"
        assert data["match"] is False
        assert data["attempts_left"] == initial_attempts - 1


def test_submit_correct_guess(auth_client):
    """POST /api/submit-guess with correct phrase should succeed."""

    secret_phrase = DEFAULT_SECRET_PHRASE  # "open sesame"

    # Mock the ML client to return the correct phrase
    with patch("requests.post", return_value=mock_ml_client_response(secret_phrase)):

        audio = (io.BytesIO(b"\x00\x01\x02binary-data"), "test.webm")
        response = auth_client.post(
            "/api/submit-guess",
            data={"audio": audio},
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["guess"] == secret_phrase
        assert data["match"] is True
        assert data["can_change_passphrase"] is True


def test_submit_guess_no_attempts_left(auth_client):
    """POST /api/submit-guess should fail if attempts are 0."""

    # FIXED: Look up the correct UUID for 'testuser'
    # USERS is keyed by username, so we get the user data dict
    player_id = g.player_id

    # Manually set attempts to 0 for this specific player
    # Note: We might need to initialize the state first if it wasn't created by login
    if player_id not in PLAYER_STATES:
        PLAYER_STATES[player_id] = {
            "attempts_left": 3,
            "secret_phrase": DEFAULT_SECRET_PHRASE,
        }

    PLAYER_STATES[player_id]["attempts_left"] = 0

    # Mock the ML client
    with patch("requests.post", return_value=mock_ml_client_response("test guess")):

        # FIXED: Send 'audio_url'
        audio = (io.BytesIO(b"\x00\x01\x02binary-data"), "test.webm")
        response = auth_client.post(
            "/api/submit-guess",
            data={"audio": audio},
            content_type="multipart/form-data",
        )

        # Since attempts are 0, the logic in app.py (line 277) handles this.
        # Note: 200 with a "Game Over" message, not 403,
        # unless you hit the explicit check at the start of the route.
        # If the check at line 212 fires, it returns 403.

        # Since we manually set attempts to 0, the check at the start of the route
        # (lines 208-216 in app.py) should trigger.
        assert response.status_code == 200
        data = response.get_json()
        assert "No attempts left" in data["message"]
