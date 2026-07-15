"""Tests for API auth gate — verifies that protected routes reject unauthenticated requests."""

import pytest
from flask import Flask
from flask_login import LoginManager

from bridge_bot.api import api, PUBLIC_ROUTES
from bridge_bot.adapter import StubBotAdapter


class _FakeUser:
    id = 999
    is_authenticated = False


def _make_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    from bridge_bot.api import set_bot_adapter
    set_bot_adapter(StubBotAdapter())

    app.register_blueprint(api)
    return app


@pytest.fixture
def client():
    app = _make_app()
    with app.test_client() as c:
        yield c


class TestPublicRoutes:
    def test_health_check_no_auth(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"

    def test_auth_me_no_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["authenticated"] is False


class TestProtectedRoutes:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/discord/channels"),
        ("GET", "/api/discord/roles"),
        ("GET", "/api/bot-status"),
        ("GET", "/api/polls"),
        ("GET", "/api/polls/stats?poll_id=1"),
        ("GET", "/api/votes"),
        ("GET", "/api/votes/all"),
        ("GET", "/api/summary"),
        ("GET", "/api/data/status"),
        ("GET", "/api/dashboard/overview"),
        ("GET", "/api/tours"),
        ("POST", "/api/polls/create"),
        ("POST", "/api/polls/1/end"),
        ("GET", "/api/export/csv"),
    ])
    def test_unauthenticated_returns_401(self, client, method, path):
        resp = client.open(path, method=method, json={})
        assert resp.status_code == 401, f"{method} {path} should return 401"
        data = resp.get_json()
        assert "Authentication required" in data["error"]

    def test_unauthenticated_submit_feedback_still_works(self, client):
        resp = client.post("/api/feedback/submit", json={
            "tour_id": 999,
            "student_id": 12345,
            "student_name": "Test",
        })
        assert resp.status_code != 401


class TestPublicRoutesAllowlist:
    def test_all_public_routes_are_in_allowlist(self):
        expected_public = {
            "api.health_check",
            "api.tours.submit_feedback",
            "api.tours.github_profile",
            "api.auth.auth_login",
            "api.auth.auth_me",
        }
        assert expected_public == PUBLIC_ROUTES
