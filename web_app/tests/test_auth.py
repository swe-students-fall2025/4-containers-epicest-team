"""
Test web app registration, login, logout, and authorization.
"""

# pylint: skip-file

from unittest.mock import MagicMock
from werkzeug.security import generate_password_hash
import pymongo.errors


class TestRegisterRoute:
    """Tests for /register endpoint."""

    def test_register_get_returns_200(self, client):
        """GET /register should return the registration page."""
        response = client.get("/register")
        assert response.status_code == 200
        assert b"register" in response.data.lower()

    def test_register_post_valid_creates_user(self, client, mock_db):
        """POST /register with valid data should create user and redirect."""
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.return_value = MagicMock()
        mock_db.users.create_index.return_value = None

        response = client.post(
            "/register",
            data={"username": "newuser", "password": "password123"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert mock_db.users.insert_one.called

    def test_register_post_duplicate_username(self, client, mock_db, mock_user):
        """POST /register with existing username should show error."""
        mock_db.users.find_one.return_value = mock_user

        response = client.post(
            "/register",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"already taken" in response.data.lower()

    def test_register_post_missing_username(self, client, mock_db):
        """POST /register without username should show error."""
        response = client.post(
            "/register",
            data={"username": "", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_register_post_missing_password(self, client, mock_db):
        """POST /register without password should show error."""
        response = client.post(
            "/register",
            data={"username": "newuser", "password": ""},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_register_post_short_password(self, client, mock_db):
        """POST /register with password < 6 chars should show error."""
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={"username": "newuser", "password": "12345"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"at least 6 characters" in response.data.lower()

    def test_register_post_invalid_username_chars(self, client, mock_db):
        """POST /register with invalid username characters should show error."""
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={"username": "user@name!", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"letters, numbers, and underscores" in response.data.lower()

    def test_register_post_duplicate_key_error(self, client, mock_db):
        """POST /register with DB duplicate key error should show error."""
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.side_effect = pymongo.errors.DuplicateKeyError(
            "duplicate"
        )

        response = client.post(
            "/register",
            data={"username": "newuser", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"already taken" in response.data.lower()

    def test_register_post_database_error(self, client, mock_db):
        """POST /register with general DB error should show error."""
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.side_effect = Exception("DB error")

        response = client.post(
            "/register",
            data={"username": "newuser", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"error occurred" in response.data.lower()


class TestLoginRoute:
    """Tests for /login endpoint."""

    def test_login_get_returns_200(self, client):
        """GET /login should return the login page."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"login" in response.data.lower()

    def test_login_post_valid_credentials(self, client, mock_db):
        """POST /login with valid credentials should log user in."""
        user_doc = {
            "username": "testuser",
            "password_hash": generate_password_hash("password123"),
            "user_uuid": "test-uuid",
        }
        mock_db.users.find_one.return_value = user_doc

        response = client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False,
        )

        assert response.status_code == 302

    def test_login_post_invalid_password(self, client, mock_db):
        """POST /login with wrong password should show error."""
        user_doc = {
            "username": "testuser",
            "password_hash": generate_password_hash("correctpass"),
            "user_uuid": "test-uuid",
        }
        mock_db.users.find_one.return_value = user_doc

        response = client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpass"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"invalid" in response.data.lower()

    def test_login_post_nonexistent_user(self, client, mock_db):
        """POST /login with non-existent user should show error."""
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/login",
            data={"username": "nonexistent", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"invalid" in response.data.lower()

    def test_login_post_missing_username(self, client, mock_db):
        """POST /login without username should show error."""
        response = client.post(
            "/login",
            data={"username": "", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_login_post_missing_password(self, client, mock_db):
        """POST /login without password should show error."""
        response = client.post(
            "/login",
            data={"username": "testuser", "password": ""},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_login_post_database_error(self, client, mock_db):
        """POST /login with DB error should show error."""
        mock_db.users.find_one.side_effect = Exception("DB error")

        response = client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"error occurred" in response.data.lower()

    def test_login_with_next_parameter(self, client, mock_db):
        """POST /login with 'next' parameter should redirect to that page."""
        user_doc = {
            "username": "testuser",
            "password_hash": generate_password_hash("password123"),
            "user_uuid": "test-uuid",
        }
        mock_db.users.find_one.return_value = user_doc

        response = client.post(
            "/login?next=/dashboard",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/dashboard" in response.location


class TestLogoutRoute:
    """Tests for /logout endpoint."""

    def test_logout_requires_login(self, client):
        """GET /logout without login should redirect to login."""
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_logout_success(self, logged_in_client):
        """GET /logout when logged in should log user out."""
        response = logged_in_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location


class TestUnauthorizedHandler:
    """Tests for unauthorized access handling."""

    def test_unauthorized_api_request_returns_json(self, client):
        """Unauthorized API request should return JSON error."""
        response = client.get("/api/game-state")
        assert response.status_code == 401
        json_data = response.get_json()
        assert json_data is not None
        assert "error" in json_data

    def test_unauthorized_html_request_redirects(self, client):
        """Unauthorized HTML request should redirect to login."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location
