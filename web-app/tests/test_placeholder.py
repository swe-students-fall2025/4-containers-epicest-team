"""Basic tests for the Codebreaker web app."""

# pylint: disable=import-error, wrong-import-position


#standard imports first
import os
import sys

#fix import path so 'app' can be imported from parent directory
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

#local imports AFTER path fix
from app import create_app


def get_client():
    """Create a Flask test client."""
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def test_index_page_renders():
    """The main game page should load successfully."""
    client = get_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Guess the Passphrase" in response.data


def test_dashboard_page_renders():
    """The dashboard page should load successfully."""
    client = get_client()
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_game_state_endpoint():
    """GET /api/game-state should return JSON."""
    client = get_client()
    response = client.get("/api/game-state")
    assert response.status_code == 200
    data = response.get_json()
    assert "attempts_left" in data


def test_submit_guess_decrements_attempts():
    """POST /api/submit-guess should decrement attempts."""
    client = get_client()
    initial = client.get("/api/game-state").get_json()["attempts_left"]

    response = client.post("/api/submit-guess", json={"guess": "test guess"})
    assert response.status_code == 200
    data = response.get_json()

    assert data["guess"] == "test guess"
    assert data["attempts_left"] == max(initial - 1, 0)


def test_reset_endpoint_resets_state():
    """POST /api/reset should reset attempts and state."""
    client = get_client()

    # modify state
    client.post("/api/submit-guess", json={"guess": "something"})

    response = client.post("/api/reset")
    assert response.status_code == 200
    data = response.get_json()

    assert data["attempts_left"] == 3
    assert data["last_guess"] is None
    assert data["last_result"] is None
