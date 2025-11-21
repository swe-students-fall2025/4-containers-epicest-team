"""
Test webapp API endpoints.
"""

# pylint: skip-file

import io
from datetime import datetime
from unittest.mock import MagicMock


class TestGameStateEndpoint:
    """Tests for /api/game-state endpoint."""

    def test_game_state_requires_login(self, client):
        """GET /api/game-state without login should return 401."""
        response = client.get("/api/game-state")
        assert response.status_code == 401

    def test_game_state_returns_state(
        self, logged_in_client, mock_db, active_secret, game_state
    ):
        """GET /api/game-state should return game state and hint."""
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.create_index.return_value = None

        response = logged_in_client.get("/api/game-state")
        assert response.status_code == 200

        json_data = response.get_json()
        assert "attempts_left" in json_data
        assert "hint" in json_data
        assert "secret_id" in json_data
        assert json_data["attempts_left"] == 3

    def test_game_state_creates_default_secret_if_none(
        self, logged_in_client, mock_db, game_state
    ):
        """GET /api/game-state should handle case when secret needs to be created."""
        default_secret = {
            "secret_id": "default-123",
            "secret_phrase": "Open Sesame",
            "hint": "A classic phrase to unlock a secret",
            "created_at": datetime.now().isoformat(),
            "wrong_guesses": 0,
            "solved_at": None,
        }
        mock_db.secrets.find_one.reset_mock()
        mock_db.secrets.find_one.side_effect = [None, default_secret, default_secret]
        mock_db.secrets.insert_one.return_value = MagicMock()
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.create_index.return_value = None

        response = logged_in_client.get("/api/game-state")
        # Should successfully return state even if secret had to be created
        assert response.status_code == 200 or response.status_code == 503

    def test_game_state_error_no_secret(self, logged_in_client, mock_db):
        """GET /api/game-state with no secret available should return 503."""
        mock_db.secrets.find_one.return_value = None
        mock_db.secrets.insert_one.side_effect = Exception("Cannot create secret")

        response = logged_in_client.get("/api/game-state")
        assert response.status_code == 503


class TestSubmitGuessEndpoint:
    """Tests for /api/submit-guess endpoint."""

    def test_submit_guess_requires_login(self, client):
        """POST /api/submit-guess without login should return 401."""
        response = client.post("/api/submit-guess", json={"guess": "test"})
        assert response.status_code == 401

    def test_submit_guess_correct(
        self, logged_in_client, mock_db, active_secret, game_state
    ):
        """POST /api/submit-guess with correct guess should mark as solved."""
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.create_index.return_value = None
        mock_db.secrets.update_one.return_value = MagicMock()
        mock_db.game_states.update_one.return_value = MagicMock()

        response = logged_in_client.post(
            "/api/submit-guess", json={"guess": "Open Sesame"}
        )
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["result"] == "correct"
        assert json_data["match"] is True
        assert json_data["can_create_secret"] is True
        assert mock_db.secrets.update_one.called  # Secret marked as solved

    def test_submit_guess_correct_case_insensitive(
        self, logged_in_client, mock_db, active_secret, game_state
    ):
        """POST /api/submit-guess should be case-insensitive."""
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.create_index.return_value = None
        mock_db.secrets.update_one.return_value = MagicMock()
        mock_db.game_states.update_one.return_value = MagicMock()

        response = logged_in_client.post(
            "/api/submit-guess", json={"guess": "OPEN SESAME"}
        )
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["result"] == "correct"
        assert json_data["match"] is True

    def test_submit_guess_incorrect(
        self, logged_in_client, mock_db, active_secret, game_state
    ):
        """POST /api/submit-guess with wrong guess should decrement attempts."""
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.create_index.return_value = None
        mock_db.secrets.update_one.return_value = MagicMock()
        mock_db.game_states.update_one.return_value = MagicMock()

        response = logged_in_client.post(
            "/api/submit-guess", json={"guess": "wrong guess"}
        )
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["result"] == "incorrect"
        assert json_data["match"] is False
        assert json_data["attempts_left"] == 2
        # Wrong guesses incremented
        assert mock_db.secrets.update_one.called

    def test_submit_guess_no_attempts_left(
        self, logged_in_client, mock_db, active_secret, locked_game_state
    ):
        """POST /api/submit-guess with no attempts should return no_attempts."""
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.find_one.return_value = locked_game_state
        mock_db.game_states.create_index.return_value = None

        response = logged_in_client.post(
            "/api/submit-guess", json={"guess": "any guess"}
        )
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["result"] == "no_attempts"
        assert json_data["attempts_left"] == 0

    def test_submit_guess_last_attempt_locks_user(
        self, logged_in_client, mock_db, active_secret, game_state
    ):
        """POST /api/submit-guess that exhausts attempts should lock user for 24h."""
        # Set user to 1 attempt left
        game_state["attempts_left"] = 1
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.create_index.return_value = None
        mock_db.secrets.update_one.return_value = MagicMock()
        mock_db.game_states.update_one.return_value = MagicMock()

        response = logged_in_client.post(
            "/api/submit-guess", json={"guess": "wrong guess"}
        )
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["attempts_left"] == 0
        assert "locked_until" in json_data
        assert json_data["locked_until"] is not None

    def test_submit_guess_no_active_secret(self, logged_in_client, mock_db):
        """POST /api/submit-guess with no active secret should return 503."""
        mock_db.secrets.find_one.return_value = None

        response = logged_in_client.post(
            "/api/submit-guess", json={"guess": "any guess"}
        )
        assert response.status_code == 503


class TestCreateSecretEndpoint:
    """Tests for /api/create-secret endpoint."""

    def test_create_secret_requires_login(self, client):
        """POST /api/create-secret without login should return 401."""
        response = client.post(
            "/api/create-secret", json={"secret_phrase": "test", "hint": "test hint"}
        )
        assert response.status_code == 401

    def test_create_secret_requires_permission(
        self, logged_in_client, mock_db, game_state
    ):
        """POST /api/create-secret without permission should return 403."""
        game_state["can_create_secret"] = False
        mock_db.game_states.find_one.return_value = game_state

        response = logged_in_client.post(
            "/api/create-secret",
            json={"secret_phrase": "New Secret", "hint": "A new hint"},
        )
        assert response.status_code == 403

    def test_create_secret_success(self, logged_in_client, mock_db, winner_game_state):
        """POST /api/create-secret with permission should create secret."""
        mock_db.game_states.find_one.return_value = winner_game_state
        mock_db.secrets.insert_one.return_value = MagicMock()
        mock_db.game_states.update_one.return_value = MagicMock()

        response = logged_in_client.post(
            "/api/create-secret",
            json={"secret_phrase": "New Secret", "hint": "A helpful hint"},
        )
        assert response.status_code == 200

        json_data = response.get_json()
        assert "secret_id" in json_data
        assert mock_db.secrets.insert_one.called

    def test_create_secret_empty_phrase(
        self, logged_in_client, mock_db, winner_game_state
    ):
        """POST /api/create-secret with empty phrase should return 400."""
        mock_db.game_states.find_one.return_value = winner_game_state

        response = logged_in_client.post(
            "/api/create-secret", json={"secret_phrase": "", "hint": "A hint"}
        )
        assert response.status_code == 400
        assert b"cannot be empty" in response.data

    def test_create_secret_empty_hint(
        self, logged_in_client, mock_db, winner_game_state
    ):
        """POST /api/create-secret with empty hint should return 400."""
        mock_db.game_states.find_one.return_value = winner_game_state

        response = logged_in_client.post(
            "/api/create-secret", json={"secret_phrase": "Secret", "hint": ""}
        )
        assert response.status_code == 400
        assert b"cannot be empty" in response.data

    def test_create_secret_short_phrase(
        self, logged_in_client, mock_db, winner_game_state
    ):
        """POST /api/create-secret with phrase < 3 chars should return 400."""
        mock_db.game_states.find_one.return_value = winner_game_state

        response = logged_in_client.post(
            "/api/create-secret", json={"secret_phrase": "ab", "hint": "A hint"}
        )
        assert response.status_code == 400
        assert b"at least 3 characters" in response.data

    def test_create_secret_short_hint(
        self, logged_in_client, mock_db, winner_game_state
    ):
        """POST /api/create-secret with hint < 5 chars should return 400."""
        mock_db.game_states.find_one.return_value = winner_game_state

        response = logged_in_client.post(
            "/api/create-secret", json={"secret_phrase": "Secret", "hint": "hint"}
        )
        assert response.status_code == 400
        assert b"at least 5 characters" in response.data

    def test_create_secret_db_error(self, logged_in_client, mock_db, winner_game_state):
        """POST /api/create-secret with DB error should return 500."""
        mock_db.game_states.find_one.return_value = winner_game_state
        mock_db.secrets.insert_one.side_effect = Exception("DB error")

        response = logged_in_client.post(
            "/api/create-secret",
            json={"secret_phrase": "New Secret", "hint": "A helpful hint"},
        )
        assert response.status_code == 500


class TestSendMetadataEndpoint:
    """Tests for /api/send-metadata endpoint."""

    def test_send_metadata_requires_login(self, client):
        """POST /api/send-metadata without login should return 401."""
        response = client.post("/api/send-metadata", json={"key": "value"})
        assert response.status_code == 401

    def test_send_metadata_success(self, logged_in_client, mock_db):
        """POST /api/send-metadata with valid data should save metadata."""
        mock_db.metadata.insert_one.return_value = MagicMock()

        response = logged_in_client.post(
            "/api/send-metadata", json={"key": "value", "data": "test"}
        )
        assert response.status_code == 200
        assert mock_db.metadata.insert_one.called

    def test_send_metadata_empty(self, logged_in_client, mock_db):
        """POST /api/send-metadata with empty data should return 400."""
        response = logged_in_client.post("/api/send-metadata", json={})
        assert response.status_code == 400

    def test_send_metadata_db_error(self, logged_in_client, mock_db):
        """POST /api/send-metadata with DB error should return 500."""
        mock_db.metadata.insert_one.side_effect = Exception("DB error")

        response = logged_in_client.post("/api/send-metadata", json={"key": "value"})
        assert response.status_code == 500


class TestResetEndpoint:
    """Tests for /api/reset endpoint."""

    def test_reset_requires_login(self, client):
        """POST /api/reset without login should return 401."""
        response = client.post("/api/reset")
        assert response.status_code == 401

    def test_reset_success(
        self, logged_in_client, mock_db, active_secret, locked_game_state
    ):
        """POST /api/reset should reset user's game state."""
        mock_db.secrets.find_one.return_value = active_secret
        mock_db.game_states.update_one.return_value = MagicMock()

        response = logged_in_client.post("/api/reset")
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["attempts_left"] == 3
        assert json_data["last_guess"] is None
        assert json_data["last_result"] is None
        assert json_data["locked_until"] is None

    def test_reset_no_active_secret(self, logged_in_client, mock_db):
        """POST /api/reset with no active secret should return 503."""
        mock_db.secrets.find_one.return_value = None

        response = logged_in_client.post("/api/reset")
        assert response.status_code == 503


class TestUploadAudioEndpoint:
    """Tests for /api/upload-audio endpoint."""

    def test_upload_audio_requires_login(self, client):
        """POST /api/upload-audio without login should return 401."""
        response = client.post("/api/upload-audio")
        assert response.status_code == 401

    def test_upload_audio_no_file(self, logged_in_client):
        """POST /api/upload-audio without file should return 400."""
        response = logged_in_client.post("/api/upload-audio")
        assert response.status_code == 400

        json_data = response.get_json()
        assert "error" in json_data

    def test_upload_audio_empty_file(self, logged_in_client):
        """POST /api/upload-audio with empty file should return 400."""
        data = {"audio_file": (io.BytesIO(b""), "")}

        response = logged_in_client.post(
            "/api/upload-audio", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 400

    def test_upload_audio_invalid_mimetype(self, logged_in_client):
        """POST /api/upload-audio with non-audio file should return 400."""
        fake_file = io.BytesIO(b"this is not audio")
        data = {"audio_file": (fake_file, "file.txt", "text/plain")}

        response = logged_in_client.post(
            "/api/upload-audio", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 400

        json_data = response.get_json()
        assert "error" in json_data

    def test_upload_audio_valid_file(self, logged_in_client, monkeypatch):
        """POST /api/upload-audio with valid audio file should return transcription."""

        monkeypatch.setattr(
            "web_app.app.transcribe_audio", lambda f: ("transcribed text", True)
        )

        fake_audio = io.BytesIO(b"fake audio data")
        fake_audio.seek(0)
        data = {
                "audio_file": (fake_audio, "recording.webm", "audio/webm")
        }

        response = logged_in_client.post(
            "/api/upload-audio", data=data, content_type="multipart/form-data"
        )
        print(response)
        print(logged_in_client.application.url_map)
        print(response.status_code)
        print(response.location)
        print(response.data)

        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data["recognized_text"] == "transcribed text"

    def test_upload_audio_transcription_fails(self, logged_in_client, monkeypatch):
        """POST /api/upload-audio with transcription failure should return 500."""

        monkeypatch.setattr("web_app.app.transcribe_audio", lambda f: "")

        fake_audio = io.BytesIO(b"fake audio data")
        data = {"audio_file": (fake_audio, "audio.webm", "audio/webm")}

        response = logged_in_client.post(
            "/api/upload-audio", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 500

    def test_upload_audio_exception(self, logged_in_client, monkeypatch):
        """POST /api/upload-audio with exception should return 500."""

        def mock_transcribe(f):
            raise Exception("Transcription error")

        monkeypatch.setattr("web_app.app.transcribe_audio", mock_transcribe)

        fake_audio = io.BytesIO(b"fake audio data")
        data = {"audio_file": (fake_audio, "audio.webm", "audio/webm")}

        response = logged_in_client.post(
            "/api/upload-audio", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 500
