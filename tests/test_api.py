"""Tests for the Flask JSON API endpoints."""

import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# ---------------------------------------------------------------------------
# Mock excel_manager module BEFORE any app imports happen.
# The dashboard adds bridge_bot/ to sys.path, so api.py and bot.py import
# "from excel_manager import excel_manager" as a top-level module.
# ---------------------------------------------------------------------------
mock_mgr = MagicMock()

mock_mgr.get_all_polls.return_value = [
    {
        "poll_id": 1,
        "question": "Test Poll?",
        "options": [{"name": "Yes", "votes": 5}, {"name": "No", "votes": 3}],
        "total_votes": 8,
        "timestamp": "2026-07-10 12:00:00",
    },
    {
        "poll_id": 2,
        "question": "Second Poll?",
        "options": [{"name": "A", "votes": 2}, {"name": "B", "votes": 4}],
        "total_votes": 6,
        "timestamp": "2026-07-10 13:00:00",
    },
]

mock_mgr.get_poll_stats.side_effect = lambda pid: (
    {
        "total_votes": 8,
        "question": "Test Poll?",
        "choices": {"Yes": 5, "No": 3},
        "voters_by_choice": {"Yes": ["Alice", "Bob"], "No": ["Charlie"]},
    }
    if pid == 1
    else None
)

mock_mgr.get_all_votes.return_value = [
    {"Timestamp": "2026-07-10 12:00:00", "Username": "Alice", "User_ID": 100, "Question": "Test Poll?", "Choice": "Yes", "Poll_ID": 1},
    {"Timestamp": "2026-07-10 12:05:00", "Username": "Bob", "User_ID": 101, "Question": "Test Poll?", "Choice": "Yes", "Poll_ID": 1},
    {"Timestamp": "2026-07-10 12:10:00", "Username": "Charlie", "User_ID": 102, "Question": "Test Poll?", "Choice": "No", "Poll_ID": 1},
    {"Timestamp": "2026-07-10 13:00:00", "Username": "Dave", "User_ID": 103, "Question": "Second Poll?", "Choice": "Option A", "Poll_ID": 2},
    {"Timestamp": "2026-07-10 13:05:00", "Username": "Eve", "User_ID": 104, "Question": "Second Poll?", "Choice": "Option B", "Poll_ID": 2},
    {"Timestamp": "2026-07-10 13:10:00", "Username": "Frank", "User_ID": 105, "Question": "Second Poll?", "Choice": "Option B", "Poll_ID": 2},
]

mock_mgr.get_summary_by_question.return_value = {
    "Test Poll?": {"Total_Votes": 3, "choices": {"Yes": 2, "No": 1}},
    "Second Poll?": {"Total_Votes": 3, "choices": {"Option A": 1, "Option B": 2}},
}

mock_mgr.get_poll_metadata.return_value = {
    "poll_id": 1,
    "question": "Test Poll?",
    "channel_id": 12345,
}

mock_mgr.export_to_csv.return_value = "/tmp/test_export.csv"

# Make mock attributes JSON-serializable (e.g. _dirty used by /api/data/status)
mock_mgr._dirty = False

# Insert a mock module so that "from excel_manager import excel_manager" works.
# The real module has a module-level "excel_manager = ExcelDataManager()" instance.
import types
_excel_mod = types.ModuleType("excel_manager")
_excel_mod.excel_manager = mock_mgr
sys.modules["excel_manager"] = _excel_mod

# Also mock discord before it's imported
discord_mock = MagicMock()
discord_mock.Intents.default.return_value = MagicMock()
sys.modules["discord"] = discord_mock
sys.modules["discord.ext"] = MagicMock()
sys.modules["discord.ext.commands"] = MagicMock()
sys.modules["discord.ui"] = MagicMock()


@pytest.fixture(autouse=True)
def _reset_mocks():
    mock_mgr.reset_mock()
    mock_mgr._dirty = False
    # Re-set return values after reset
    mock_mgr.get_all_polls.return_value = [
        {"poll_id": 1, "question": "Test Poll?", "options": [{"name": "Yes", "votes": 5}, {"name": "No", "votes": 3}], "total_votes": 8, "timestamp": "2026-07-10 12:00:00"},
        {"poll_id": 2, "question": "Second Poll?", "options": [{"name": "A", "votes": 2}, {"name": "B", "votes": 4}], "total_votes": 6, "timestamp": "2026-07-10 13:00:00"},
    ]
    mock_mgr.get_poll_stats.side_effect = lambda pid: (
        {"total_votes": 8, "question": "Test Poll?", "choices": {"Yes": 5, "No": 3}, "voters_by_choice": {"Yes": ["Alice", "Bob"], "No": ["Charlie"]}}
        if pid == 1 else None
    )
    mock_mgr.get_all_votes.return_value = [
        {"Timestamp": "2026-07-10 12:00:00", "Username": "Alice", "User_ID": 100, "Question": "Test Poll?", "Choice": "Yes", "Poll_ID": 1},
        {"Timestamp": "2026-07-10 12:05:00", "Username": "Bob", "User_ID": 101, "Question": "Test Poll?", "Choice": "Yes", "Poll_ID": 1},
        {"Timestamp": "2026-07-10 12:10:00", "Username": "Charlie", "User_ID": 102, "Question": "Test Poll?", "Choice": "No", "Poll_ID": 1},
        {"Timestamp": "2026-07-10 13:00:00", "Username": "Dave", "User_ID": 103, "Question": "Second Poll?", "Choice": "Option A", "Poll_ID": 2},
        {"Timestamp": "2026-07-10 13:05:00", "Username": "Eve", "User_ID": 104, "Question": "Second Poll?", "Choice": "Option B", "Poll_ID": 2},
        {"Timestamp": "2026-07-10 13:10:00", "Username": "Frank", "User_ID": 105, "Question": "Second Poll?", "Choice": "Option B", "Poll_ID": 2},
    ]
    mock_mgr.get_summary_by_question.return_value = {
        "Test Poll?": {"Total_Votes": 3, "choices": {"Yes": 2, "No": 1}},
        "Second Poll?": {"Total_Votes": 3, "choices": {"Option A": 1, "Option B": 2}},
    }
    yield


# Now we can safely import dashboard (which imports api -> excel_manager)
with patch("dashboard.bot") as mock_bot, patch("dashboard.start_bot") as _:
    mock_bot.is_ready.return_value = True
    mock_bot.latency = 0.05
    mock_bot.user = MagicMock()
    mock_bot.user.avatar = MagicMock()
    mock_bot.user.avatar.url = "https://example.com/avatar.png"
    mock_bot.loop = MagicMock()

    import dashboard as _dv
    _dv.app.config["TESTING"] = True


@pytest.fixture
def client():
    with _dv.app.test_client() as c:
        yield c


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["service"] == "Bridge 2026 Dashboard API"


class TestPolls:
    def test_list_polls_success(self, client):
        resp = client.get("/api/polls")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_poll_detail_success(self, client):
        resp = client.get("/api/polls/1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["poll_id"] == 1
        assert data["question"] == "Test Poll?"
        assert len(data["options"]) == 2
        assert data["total_votes"] == 8

    def test_get_poll_detail_not_found(self, client):
        resp = client.get("/api/polls/999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_get_poll_detail_invalid_id(self, client):
        resp = client.get("/api/polls/abc")
        assert resp.status_code == 404

    def test_poll_stats_success(self, client):
        resp = client.get("/api/polls/stats?poll_id=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_votes"] == 8

    def test_poll_stats_missing_param(self, client):
        resp = client.get("/api/polls/stats")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_poll_stats_not_found(self, client):
        resp = client.get("/api/polls/stats?poll_id=999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


class TestVotes:
    def test_list_votes_default_pagination(self, client):
        resp = client.get("/api/votes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 6
        assert data["page"] == 1
        assert data["limit"] == 25
        assert "votes" in data

    def test_list_votes_with_pagination(self, client):
        resp = client.get("/api/votes?page=1&limit=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["votes"]) == 2

    def test_list_votes_invalid_page(self, client):
        resp = client.get("/api/votes?page=-1")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_list_votes_invalid_limit(self, client):
        resp = client.get("/api/votes?limit=abc")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_list_votes_limit_too_high(self, client):
        resp = client.get("/api/votes?limit=200")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_get_all_votes(self, client):
        resp = client.get("/api/votes/all")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 6
        assert len(data["votes"]) == 6

    def test_get_all_votes_with_limit(self, client):
        resp = client.get("/api/votes/all?limit=3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3
        assert len(data["votes"]) == 3

    def test_get_all_votes_invalid_limit(self, client):
        resp = client.get("/api/votes/all?limit=2000")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_get_user_votes(self, client):
        resp = client.get("/api/votes/by-user/100")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user_id"] == 100
        assert data["vote_count"] == 1

    def test_get_user_votes_invalid_id(self, client):
        resp = client.get("/api/votes/by-user/abc")
        assert resp.status_code == 404


class TestBotStatus:
    def test_bot_status_online(self, client):
        resp = client.get("/api/bot-status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "online" in data
        assert "uptime" in data
        assert "votes_total" in data

    def test_bot_status_offline(self, client):
        from dashboard import bot as dv_bot
        dv_bot.is_ready.return_value = False
        resp = client.get("/api/bot-status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["online"] is False


class TestDataStatus:
    def test_data_status(self, client):
        resp = client.get("/api/data/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_records" in data
        assert "status" in data
        assert data["status"] == "healthy"

    def test_dashboard_overview(self, client):
        resp = client.get("/api/dashboard/overview")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_votes" in data
        assert "unique_voters" in data
        assert "engagement_rate" in data


class TestSummary:
    def test_summary(self, client):
        resp = client.get("/api/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "summary" in data
        assert "total_questions" in data


class TestErrorHandlers:
    def test_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_create_poll_redirect(self, client):
        resp = client.get("/create-poll")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data
