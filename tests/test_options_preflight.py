"""Tests that OPTIONS preflight requests bypass the auth check.

The bug: require_auth() checks current_user.is_authenticated for ALL
requests, including OPTIONS preflight. Browsers send OPTIONS before the
real POST with CORS headers — if OPTIONS returns 401, the browser blocks
the actual request, breaking poll creation from the frontend.
"""

import pytest
from flask import Flask
from flask_login import LoginManager

from bridge_bot.api import api, set_bot_adapter
from bridge_bot.adapter import StubBotAdapter


def _make_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    set_bot_adapter(StubBotAdapter())
    app.register_blueprint(api)
    return app


@pytest.fixture
def client():
    app = _make_app()
    with app.test_client() as c:
        yield c


class TestOptionsPreflightBypassesAuth:
    """OPTIONS preflight must return 200, not 401, on protected routes."""

    def test_options_polls_create_returns_200(self, client):
        """OPTIONS /api/polls/create must not be blocked by auth."""
        resp = client.options("/api/polls/create")
        assert resp.status_code == 200, (
            f"OPTIONS preflight returned {resp.status_code}, expected 200. "
            "CORS preflight will fail, blocking the browser's actual POST."
        )

    def test_options_polls_end_returns_200(self, client):
        """OPTIONS /api/polls/1/end must not be blocked by auth."""
        resp = client.options("/api/polls/1/end")
        assert resp.status_code == 200

    def test_options_tours_return_200(self, client):
        """OPTIONS /api/tours must not be blocked by auth."""
        resp = client.options("/api/tours")
        assert resp.status_code == 200
