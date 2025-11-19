"""
Tests webapp HTML routes.
"""

# pylint: skip-file

class TestIndexRoute:
    """Tests for / endpoint."""

    def test_index_requires_login(self, client):
        """GET / without login should redirect to login page."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_index_renders_when_logged_in(self, logged_in_client):
        """GET / when logged in should render the index page."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        # response is HTML
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


class TestDashboardRoute:
    """Tests for /dashboard endpoint."""

    def test_dashboard_requires_login(self, client):
        """GET /dashboard without login should redirect to login page."""
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_dashboard_renders_when_logged_in(self, logged_in_client):
        """GET /dashboard when logged in should render the dashboard page."""
        response = logged_in_client.get("/dashboard")
        assert response.status_code == 200
        # response is HTML
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data
