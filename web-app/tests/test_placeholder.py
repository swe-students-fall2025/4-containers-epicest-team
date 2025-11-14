"""Basic tests for the Codebreaker web app."""

import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


from app import create_app


def get_client():
    """Create a Flask test client."""
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_index_page_renders():
    """The main game page should load successfully."""
    client = get_client()
    response = client.get("/")
    assert response.status_code == 200
    #check that the main heading text is present
    assert b"Guess the Passphrase" in response.data


def test_dashboard_page_renders():
    """The dashboard page should load successfully."""
    client = get_client()
    response = client.get("/dashboard")
    assert response.status_code == 200


def test_game_state_endpoint():
    """GET /api/game-state should return JSON with attempts_left."""
    client = get_client()
    response = client.get("/api/game-state")
    assert response.status_code == 200
    data = response.get_json()
    assert "attempts_left" in data


def test_submit_guess_decrements_attempts():
    """
    POST /api/submit-guess should accept JSON and
    respond with attempts_left and guess echoed back.
    """
    client = get_client()

    #get initial attempts
    initial = client.get("/api/game-state").get_json()["attempts_left"]

    response = client.post(
        "/api/submit-guess",
        json={"guess": "test guess"},
    )
    assert response.status_code == 200
    data = response.get_json()

    assert data["guess"] == "test guess"
    assert data["attempts_left"] == max(initial - 1, 0)


def test_reset_endpoint_resets_state():
    """POST /api/reset should reset attempts_left and last_guess/result."""
    client = get_client()

    #change state a bit
    client.post("/api/submit-guess", json={"guess": "something"})

    response = client.post("/api/reset")
    assert response.status_code == 200
    data = response.get_json()

    assert data["attempts_left"] == 3
    assert data["last_guess"] is None
    assert data["last_result"] is None