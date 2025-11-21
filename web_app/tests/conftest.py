# pylint: skip-file

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from web_app.app import create_app

## Establish environment for testing (mock database, mock client)


@pytest.fixture
def mock_db():
    """Create a mocked MongoDB database with all necessary collections."""
    db = MagicMock()

    db.users = MagicMock()
    db.secrets = MagicMock()
    db.game_states = MagicMock()
    db.metadata = MagicMock()

    return db


@pytest.fixture
def mock_mongo_client(mock_db):
    """Create a mocked MongoDB client."""
    client = MagicMock()
    client.__getitem__.return_value = mock_db
    return client


@pytest.fixture
def active_secret():
    """Return a mock active secret document."""
    return {
        "secret_id": "test-secret-123",
        "secret_phrase": "Open Sesame",
        "hint": "A classic phrase to unlock a secret",
        "created_at": datetime.now().isoformat(),
        "wrong_guesses": 0,
        "solved_at": None,
    }


@pytest.fixture
def mock_user():
    """Return a mock user document."""
    return {
        "username": "testuser",
        "password_hash": "pbkdf2:sha256:260000$test$hash",
        "user_uuid": "test-user-uuid-123",
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def app(monkeypatch, mock_db, mock_mongo_client, active_secret):
    """Create a fresh Flask app for each test run with mocked MongoDB."""

    def mock_init_mongo():
        return mock_mongo_client, mock_db

    monkeypatch.setattr("web_app.app.init_mongo", mock_init_mongo)

    mock_db.secrets.find_one.return_value = active_secret

    app_instance = create_app()
    app_instance.config["TESTING"] = True
    app_instance.config["WTF_CSRF_ENABLED"] = False
    app_instance.config["SECRET_KEY"] = "test-secret-key"

    return app_instance


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def logged_in_client(client, mock_db, mock_user):
    """
    Creates a logged-in test user session.
    Allows tests to hit @login_required routes.
    """
    # Mock user lookup for Flask-Login
    mock_db.users.find_one.return_value = mock_user

    # Create session with logged-in user
    with client.session_transaction() as sess:
        sess["_user_id"] = "testuser"

    return client


@pytest.fixture
def game_state():
    """Return a mock game state document."""
    return {
        "user_uuid": "test-user-uuid-123",
        "current_secret_id": "test-secret-123",
        "attempts_left": 3,
        "last_result": None,
        "last_guess": None,
        "can_create_secret": False,
        "locked_until": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def locked_game_state(game_state):
    """Return a game state with user locked out."""
    locked = game_state.copy()
    locked["attempts_left"] = 0
    locked["locked_until"] = (datetime.now() + timedelta(hours=24)).isoformat()
    return locked


@pytest.fixture
def winner_game_state(game_state):
    """Return a game state where user can create a secret."""
    winner = game_state.copy()
    winner["can_create_secret"] = True
    return winner
