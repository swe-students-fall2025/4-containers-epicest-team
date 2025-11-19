"""
Test MongoDB helper functions.
"""

# pylint: skip-file

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Import the helper functions we're testing
from web_app.app import (
    init_mongo,
    get_active_secret,
    create_default_secret,
    mark_secret_solved,
    increment_wrong_guesses,
    create_new_secret,
    get_or_create_state,
    update_game_state,
)


class TestInitMongo:
    """Tests for init_mongo function."""

    def test_init_mongo_success(self, monkeypatch):
        """init_mongo with valid credentials should connect successfully."""
        monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
        monkeypatch.setenv("MONGO_DB", "testdb")
        monkeypatch.setenv("MONGO_USER", "testuser")
        monkeypatch.setenv("MONGO_PASS", "testpass")

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch("web_app.app.pymongo.MongoClient", return_value=mock_client):
            client, db = init_mongo()
            assert client is not None
            assert db is not None

    def test_init_mongo_missing_credentials(self, monkeypatch):
        """init_mongo with missing credentials should return None."""
        # Create a fresh environment without MongoDB credentials
        with patch("web_app.app.MONGO_URI", None):
            with patch("web_app.app.MONGO_DB", None):
                with patch("web_app.app.MONGO_USER", None):
                    with patch("web_app.app.MONGO_PASS", None):
                        client, db = init_mongo()
                        assert client is None
                        assert db is None

    def test_init_mongo_connection_error(self, monkeypatch):
        """init_mongo with connection error should return None."""
        monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
        monkeypatch.setenv("MONGO_DB", "testdb")
        monkeypatch.setenv("MONGO_USER", "testuser")
        monkeypatch.setenv("MONGO_PASS", "testpass")

        with patch(
            "web_app.app.pymongo.MongoClient",
            side_effect=Exception("Connection failed"),
        ):
            client, db = init_mongo()
            assert client is None
            assert db is None


class TestGetActiveSecret:
    """Tests for get_active_secret function."""

    def test_get_active_secret_found(self, mock_db, active_secret):
        """get_active_secret should return the active secret."""
        mock_db.secrets.find_one.return_value = active_secret

        result = get_active_secret(mock_db)
        assert result == active_secret
        mock_db.secrets.find_one.assert_called_once()

    def test_get_active_secret_not_found(self, mock_db):
        """get_active_secret with no active secret should return None."""
        mock_db.secrets.find_one.return_value = None

        result = get_active_secret(mock_db)
        assert result is None

    def test_get_active_secret_db_none(self):
        """get_active_secret with None db should return None."""
        result = get_active_secret(None)
        assert result is None

    def test_get_active_secret_db_error(self, mock_db):
        """get_active_secret with DB error should return None."""
        mock_db.secrets.find_one.side_effect = Exception("DB error")

        result = get_active_secret(mock_db)
        assert result is None


class TestCreateDefaultSecret:
    """Tests for create_default_secret function."""

    def test_create_default_secret_when_none_exists(self, mock_db):
        """create_default_secret should create secret when none exists."""
        mock_db.secrets.find_one.return_value = None
        mock_db.secrets.insert_one.return_value = MagicMock()

        result = create_default_secret(mock_db)
        assert result is not None
        assert result["secret_phrase"] == "Open Sesame"
        mock_db.secrets.insert_one.assert_called_once()

    def test_create_default_secret_when_exists(self, mock_db, active_secret):
        """create_default_secret should return existing secret if one exists."""
        mock_db.secrets.find_one.return_value = active_secret

        result = create_default_secret(mock_db)
        assert result == active_secret
        mock_db.secrets.insert_one.assert_not_called()

    def test_create_default_secret_db_none(self):
        """create_default_secret with None db should return None."""
        result = create_default_secret(None)
        assert result is None

    def test_create_default_secret_db_error(self, mock_db):
        """create_default_secret with DB error should return None."""
        mock_db.secrets.find_one.return_value = None
        mock_db.secrets.insert_one.side_effect = Exception("DB error")

        result = create_default_secret(mock_db)
        assert result is None


class TestMarkSecretSolved:
    """Tests for mark_secret_solved function."""

    def test_mark_secret_solved_success(self, mock_db):
        """mark_secret_solved should update the secret."""
        mock_db.secrets.update_one.return_value = MagicMock()

        result = mark_secret_solved(mock_db, "test-secret-123")
        assert result is True
        mock_db.secrets.update_one.assert_called_once()

    def test_mark_secret_solved_db_none(self):
        """mark_secret_solved with None db should return False."""
        result = mark_secret_solved(None, "test-secret-123")
        assert result is False

    def test_mark_secret_solved_db_error(self, mock_db):
        """mark_secret_solved with DB error should return False."""
        mock_db.secrets.update_one.side_effect = Exception("DB error")

        result = mark_secret_solved(mock_db, "test-secret-123")
        assert result is False


class TestIncrementWrongGuesses:
    """Tests for increment_wrong_guesses function."""

    def test_increment_wrong_guesses_success(self, mock_db):
        """increment_wrong_guesses should increment the counter."""
        mock_db.secrets.update_one.return_value = MagicMock()

        result = increment_wrong_guesses(mock_db, "test-secret-123")
        assert result is True
        mock_db.secrets.update_one.assert_called_once()

    def test_increment_wrong_guesses_db_none(self):
        """increment_wrong_guesses with None db should return False."""
        result = increment_wrong_guesses(None, "test-secret-123")
        assert result is False

    def test_increment_wrong_guesses_db_error(self, mock_db):
        """increment_wrong_guesses with DB error should return False."""
        mock_db.secrets.update_one.side_effect = Exception("DB error")

        result = increment_wrong_guesses(mock_db, "test-secret-123")
        assert result is False


class TestCreateNewSecret:
    """Tests for create_new_secret function."""

    def test_create_new_secret_success(self, mock_db):
        """create_new_secret should insert a new secret."""
        mock_db.secrets.insert_one.return_value = MagicMock()

        result = create_new_secret(mock_db, "New Secret", "New Hint", "creator-uuid")
        assert result is not None
        assert result["secret_phrase"] == "New Secret"
        assert result["hint"] == "New Hint"
        assert result["created_by"] == "creator-uuid"
        mock_db.secrets.insert_one.assert_called_once()

    def test_create_new_secret_db_none(self):
        """create_new_secret with None db should return None."""
        result = create_new_secret(None, "Secret", "Hint", "uuid")
        assert result is None

    def test_create_new_secret_db_error(self, mock_db):
        """create_new_secret with DB error should return None."""
        mock_db.secrets.insert_one.side_effect = Exception("DB error")

        result = create_new_secret(mock_db, "Secret", "Hint", "uuid")
        assert result is None


class TestGetOrCreateState:
    """Tests for get_or_create_state function."""

    def test_get_or_create_state_new_user(self, mock_db, active_secret):
        """get_or_create_state for new user should create state."""
        mock_db.game_states.find_one.return_value = None
        mock_db.game_states.insert_one.return_value = MagicMock()
        mock_db.game_states.create_index.return_value = None

        result = get_or_create_state("new-user-uuid", mock_db, active_secret)
        assert result["attempts_left"] == 3
        assert result["current_secret_id"] == "test-secret-123"
        mock_db.game_states.insert_one.assert_called_once()

    def test_get_or_create_state_existing_user(
        self, mock_db, active_secret, game_state
    ):
        """get_or_create_state for existing user should return state."""
        mock_db.game_states.find_one.return_value = game_state

        result = get_or_create_state("test-user-uuid-123", mock_db, active_secret)
        assert result["attempts_left"] == 3
        assert result["current_secret_id"] == "test-secret-123"

    def test_get_or_create_state_secret_changed(
        self, mock_db, active_secret, game_state
    ):
        """get_or_create_state with different secret should reset state."""
        game_state["current_secret_id"] = "old-secret-id"
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.update_one.return_value = MagicMock()

        result = get_or_create_state("test-user-uuid-123", mock_db, active_secret)
        assert result["attempts_left"] == 3
        assert result["current_secret_id"] == "test-secret-123"
        assert result["last_result"] is None
        mock_db.game_states.update_one.assert_called_once()

    def test_get_or_create_state_locked_expired(
        self, mock_db, active_secret, game_state
    ):
        """get_or_create_state with expired lockout should restore attempts."""
        game_state["attempts_left"] = 0
        game_state["locked_until"] = (datetime.now() - timedelta(hours=1)).isoformat()
        mock_db.game_states.find_one.return_value = game_state
        mock_db.game_states.update_one.return_value = MagicMock()

        result = get_or_create_state("test-user-uuid-123", mock_db, active_secret)
        assert result["attempts_left"] == 3
        assert result["locked_until"] is None
        mock_db.game_states.update_one.assert_called_once()

    def test_get_or_create_state_locked_active(
        self, mock_db, active_secret, game_state
    ):
        """get_or_create_state with active lockout should keep 0 attempts."""
        game_state["attempts_left"] = 0
        game_state["locked_until"] = (datetime.now() + timedelta(hours=1)).isoformat()
        mock_db.game_states.find_one.return_value = game_state

        result = get_or_create_state("test-user-uuid-123", mock_db, active_secret)
        assert result["attempts_left"] == 0
        assert result["locked_until"] is not None

    def test_get_or_create_state_db_none(self, active_secret):
        """get_or_create_state with None db should return default state."""
        result = get_or_create_state("user-uuid", None, active_secret)
        assert result["attempts_left"] == 3
        assert result["current_secret_id"] is None

    def test_get_or_create_state_secret_none(self, mock_db):
        """get_or_create_state with None secret should return default state."""
        result = get_or_create_state("user-uuid", mock_db, None)
        assert result["attempts_left"] == 3
        assert result["current_secret_id"] is None

    def test_get_or_create_state_db_error(self, mock_db, active_secret):
        """get_or_create_state with DB error should return default state."""
        mock_db.game_states.find_one.side_effect = Exception("DB error")

        result = get_or_create_state("user-uuid", mock_db, active_secret)
        assert result["attempts_left"] == 3
        assert result["current_secret_id"] == "test-secret-123"


class TestUpdateGameState:
    """Tests for update_game_state function."""

    def test_update_game_state_success(self, mock_db):
        """update_game_state should update the state."""
        mock_db.game_states.update_one.return_value = MagicMock()

        updates = {"attempts_left": 2, "last_guess": "test"}
        result = update_game_state("user-uuid", mock_db, updates)
        assert result is True
        mock_db.game_states.update_one.assert_called_once()

    def test_update_game_state_db_none(self):
        """update_game_state with None db should return False."""
        result = update_game_state("user-uuid", None, {"attempts_left": 2})
        assert result is False

    def test_update_game_state_db_error(self, mock_db):
        """update_game_state with DB error should return False."""
        mock_db.game_states.update_one.side_effect = Exception("DB error")

        result = update_game_state("user-uuid", mock_db, {"attempts_left": 2})
        assert result is False
