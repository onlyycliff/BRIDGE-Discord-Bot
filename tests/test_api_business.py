"""Tests for API business logic — poll creation, ending, and feedback validation."""

import asyncio
import concurrent.futures
import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin

from bridge_bot.api import api, set_bot_adapter
from bridge_bot.adapter import StubBotAdapter
import bridge_bot.validators as validators


class _TestUser(UserMixin):
    def __init__(self):
        self.id = 1
        self.email = "test@bridge.org"
        self.name = "Test Coach"
        self.password_hash = "fake"
        self.created_at = None


def _make_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def _load_user(user_id):
        if user_id == "1":
            return _TestUser()
        return None

    adapter = StubBotAdapter()
    set_bot_adapter(adapter)

    app.register_blueprint(api)
    return app, adapter


@pytest.fixture
def client():
    app, adapter = _make_app()
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["_user_id"] = "1"
        yield c, adapter


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    validators._message_rate_limiter.reset_all()
    yield
    validators._message_rate_limiter.reset_all()


class TestCreatePollValidation:
    def test_create_poll_missing_question(self, client):
        c, _ = client
        resp = c.post("/api/polls/create", json={
            "options": ["A", "B"],
        })
        assert resp.status_code == 400
        assert "Question is required" in resp.get_json()["error"]

    def test_create_poll_too_few_options(self, client):
        c, _ = client
        resp = c.post("/api/polls/create", json={
            "question": "Test?",
            "options": ["Only one"],
        })
        assert resp.status_code == 400
        assert "At least 2 options" in resp.get_json()["error"]

    def test_create_poll_too_many_options(self, client):
        c, _ = client
        resp = c.post("/api/polls/create", json={
            "question": "Test?",
            "options": ["A", "B", "C", "D", "E", "F"],
        })
        assert resp.status_code == 400
        assert "Maximum 5 options" in resp.get_json()["error"]

    def test_create_poll_no_json(self, client):
        c, _ = client
        resp = c.post("/api/polls/create")
        assert resp.status_code == 400

    def test_create_poll_sanitizes_mentions(self, client):
        c, adapter = client
        loop = asyncio.new_event_loop()

        def _run_schedule(coro):
            result = loop.run_until_complete(coro)
            f = concurrent.futures.Future()
            f.set_result(result)
            return f

        adapter.schedule_coroutine = _run_schedule
        adapter.get_event_loop = lambda: loop
        resp = c.post("/api/polls/create", json={
            "question": "Test @everyone blast",
            "options": ["A", "B"],
        })
        assert resp.status_code == 201
        call_args = adapter._send_poll_calls[-1]
        assert "\u200b@" in call_args["question"]
        loop.close()

    def test_create_poll_deduplicates_options(self, client):
        c, adapter = client
        loop = asyncio.new_event_loop()

        def _run_schedule(coro):
            result = loop.run_until_complete(coro)
            f = concurrent.futures.Future()
            f.set_result(result)
            return f

        adapter.schedule_coroutine = _run_schedule
        adapter.get_event_loop = lambda: loop
        resp = c.post("/api/polls/create", json={
            "question": "Test?",
            "options": ["Same", "Same", "Different"],
        })
        assert resp.status_code == 201
        call_args = adapter._send_poll_calls[-1]
        assert len(call_args["options"]) == 2
        loop.close()

    def test_create_poll_invalid_channel_id(self, client):
        c, _ = client
        resp = c.post("/api/polls/create", json={
            "question": "Test?",
            "options": ["A", "B"],
            "channel_id": "not-a-number",
        })
        assert resp.status_code == 400
        assert "Invalid channel_id" in resp.get_json()["error"]

    def test_create_poll_invalid_role_ids(self, client):
        c, _ = client
        resp = c.post("/api/polls/create", json={
            "question": "Test?",
            "options": ["A", "B"],
            "role_ids": "not-a-list",
        })
        assert resp.status_code == 400
        assert "role_ids must be a list" in resp.get_json()["error"]

    def test_create_poll_max_votes_invalid(self, client):
        c, _ = client
        resp = c.post("/api/polls/create", json={
            "question": "Test?",
            "options": ["A", "B"],
            "max_votes_per_option": 0,
        })
        assert resp.status_code == 400
        assert "at least 1" in resp.get_json()["error"]


class TestEndPollValidation:
    def test_end_poll_not_found(self, client):
        c, adapter = client
        resp = c.post("/api/polls/99999/end", json={})
        assert resp.status_code == 404

    def test_end_poll_idempotent(self, client):
        c, adapter = client
        adapter._poll_active[123] = True
        resp1 = c.post("/api/polls/123/end", json={})
        assert resp1.status_code == 200
        resp2 = c.post("/api/polls/123/end", json={})
        assert resp2.status_code == 200


class TestSubmitFeedbackValidation:
    def test_submit_feedback_missing_tour_id(self, client):
        c, _ = client
        resp = c.post("/api/feedback/submit", json={
            "student_id": 123,
        })
        assert resp.status_code == 400
        assert "tour_id and student_id are required" in resp.get_json()["error"]

    def test_submit_feedback_missing_student_id(self, client):
        c, _ = client
        resp = c.post("/api/feedback/submit", json={
            "tour_id": 1,
        })
        assert resp.status_code == 400

    def test_submit_feedback_invalid_rating_too_high(self, client):
        c, _ = client
        resp = c.post("/api/feedback/submit", json={
            "tour_id": 1,
            "student_id": 123,
            "rating": 6,
        })
        assert resp.status_code == 400
        assert "between 1 and 5" in resp.get_json()["error"]

    def test_submit_feedback_invalid_rating_too_low(self, client):
        c, _ = client
        resp = c.post("/api/feedback/submit", json={
            "tour_id": 1,
            "student_id": 123,
            "rating": 0,
        })
        assert resp.status_code == 400

    def test_submit_feedback_invalid_tour_id(self, client):
        c, _ = client
        resp = c.post("/api/feedback/submit", json={
            "tour_id": "not-a-number",
            "student_id": 123,
        })
        assert resp.status_code == 400
        assert "Invalid tour_id" in resp.get_json()["error"]
