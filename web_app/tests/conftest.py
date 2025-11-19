# pylint: skip-file

import sys
from pathlib import Path
import pytest

# ------------------------------------------------------------
# FIX PYTHON IMPORT PATH SO THAT `web_app.app` CAN BE IMPORTED
# ------------------------------------------------------------
# This adds the project root to sys.path, allowing:
#     from web_app.app import create_app
#
# It works for:
# - local development
# - pytest
# - GitHub Actions CI
# - Docker CI
#
ROOT = Path(__file__).resolve().parents[2]  # up from tests/ → web_app/ → project root
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------
# NOW WE CAN IMPORT THE FLASK APPLICATION PROPERLY
# ------------------------------------------------------------
from web_app.app import create_app   # noqa: E402  (import after sys.path fix)
from web_app.app import USERS        # noqa: E402


# ------------------------------------------------------------
# PYTEST FIXTURES
# ------------------------------------------------------------

@pytest.fixture
def app():
    """Create a fresh Flask app for each test run."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test"
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def logged_in_client(app, client):
    """
    Creates & logs in a test user.
    Allows tests to hit @login_required routes.
    """
    USERS["testuser"] = {"password_hash": ""}

    with client.session_transaction() as sess:
        sess["_user_id"] = "testuser"

    return client
