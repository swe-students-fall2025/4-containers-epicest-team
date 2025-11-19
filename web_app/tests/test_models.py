"""
Test User model class.
"""

# pylint: skip-file

from web_app.app import User


class TestUserModel:
    """Tests for User class."""

    def test_user_initialization(self):
        """User should initialize with username and uuid."""
        user = User("testuser", user_uuid="test-uuid-123")
        assert user.id == "testuser"
        assert user.user_uuid == "test-uuid-123"

    def test_user_initialization_without_uuid(self):
        """User should initialize with username only."""
        user = User("testuser")
        assert user.id == "testuser"
        assert user.user_uuid is None

    def test_user_username_property(self):
        """User.username property should return the username."""
        user = User("testuser", user_uuid="test-uuid-123")
        assert user.username == "testuser"

    def test_user_id_matches_username(self):
        """User.id should be the same as username."""
        user = User("myusername", user_uuid="uuid")
        assert user.id == user.username

    def test_user_is_authenticated(self):
        """User should inherit is_authenticated from UserMixin."""
        user = User("testuser", user_uuid="test-uuid")
        assert hasattr(user, "is_authenticated")
        assert user.is_authenticated is True

    def test_user_is_active(self):
        """User should inherit is_active from UserMixin."""
        user = User("testuser", user_uuid="test-uuid")
        assert hasattr(user, "is_active")
        assert user.is_active is True

    def test_user_is_anonymous(self):
        """User should inherit is_anonymous from UserMixin."""
        user = User("testuser", user_uuid="test-uuid")
        assert hasattr(user, "is_anonymous")
        assert user.is_anonymous is False

    def test_user_get_id(self):
        """User should inherit get_id from UserMixin."""
        user = User("testuser", user_uuid="test-uuid")
        assert hasattr(user, "get_id")
        assert user.get_id() == "testuser"
