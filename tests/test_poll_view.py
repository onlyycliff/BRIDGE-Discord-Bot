"""Tests for PollView vote handling — adapter delegation and dedup."""

import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import discord

from bridge_bot.poll_state import poll_state
from bridge_bot import poll_view as pv


class SpyAdapter:
    """Records calls to record_vote and updates poll_state for dedup consistency."""

    def __init__(self):
        self.calls = []

    def record_vote(self, poll_id, user_id, username, question_id, option_id, question_type):
        self.calls.append({
            "poll_id": poll_id,
            "user_id": user_id,
            "username": username,
            "question_id": question_id,
            "option_id": option_id,
            "question_type": question_type,
        })
        poll_state.record_vote(poll_id, user_id)
        return True


class RealisticAdapter:
    """Mimics RealBotAdapter.record_vote — dedup via poll_state, then persist.

    This is the adapter that exposes the real bug: if PollView already called
    poll_state.record_vote() before us, the user is already in the set, so we
    return False and skip the DB write.
    """

    def __init__(self):
        self.db_writes = []
        self.poll_state = poll_state

    def record_vote(self, poll_id, user_id, username, question_id, option_id, question_type):
        if not self.poll_state.record_vote(poll_id, user_id):
            return False
        self.db_writes.append({
            "poll_id": poll_id,
            "user_id": user_id,
            "question_id": question_id,
            "option_id": option_id,
        })
        return True


def _make_interaction(user_id=111, user_name="TestUser", is_bot=False):
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = user_id
    interaction.user.display_name = user_name
    interaction.user.bot = is_bot
    interaction.message = MagicMock()
    interaction.message.embeds = [MagicMock()]
    return interaction


def _make_view(adapter):
    view = pv.PollView("Test?", ["A", "B"])
    view.question_id = 1
    view.option_map = {"A": 10, "B": 11}
    pv.set_adapter(adapter)
    return view


class TestVoteDelegatesToAdapter:
    """PollView must delegate vote recording to the adapter seam."""

    @pytest.mark.asyncio
    async def test_adapter_record_vote_is_called(self):
        """RED: adapter.record_vote should be called for a new vote."""
        spy = SpyAdapter()
        view = _make_view(spy)
        interaction = _make_interaction(user_id=111)

        await view.handle_vote(interaction, "A")

        assert len(spy.calls) == 1
        assert spy.calls[0]["user_id"] == 111
        assert spy.calls[0]["poll_id"] == view.poll_id
        assert spy.calls[0]["question_id"] == 1
        assert spy.calls[0]["option_id"] == 10

    @pytest.mark.asyncio
    async def test_adapter_not_called_for_duplicate(self):
        """Duplicate vote should not reach adapter."""
        spy = SpyAdapter()
        view = _make_view(spy)
        interaction1 = _make_interaction(user_id=111)
        interaction2 = _make_interaction(user_id=111)

        await view.handle_vote(interaction1, "A")
        await view.handle_vote(interaction2, "A")

        assert len(spy.calls) == 1

    @pytest.mark.asyncio
    async def test_adapter_not_called_for_bot_user(self):
        """Bot users should not reach adapter."""
        spy = SpyAdapter()
        view = _make_view(spy)
        interaction = _make_interaction(user_id=999, is_bot=True)

        await view.handle_vote(interaction, "A")

        assert len(spy.calls) == 0

    @pytest.mark.asyncio
    async def test_adapter_not_called_for_ended_poll(self):
        """Ended poll should not reach adapter."""
        spy = SpyAdapter()
        view = _make_view(spy)
        poll_state.active[view.poll_id] = False
        interaction = _make_interaction(user_id=111)

        await view.handle_vote(interaction, "A")

        assert len(spy.calls) == 0


class TestVotePersistenceBug:
    """The critical bug: PollView + adapter both call poll_state.record_vote(),
    causing the DB write to be skipped."""

    @pytest.mark.asyncio
    async def test_vote_reaches_db_through_adapter(self):
        """RED: With a realistic adapter, the DB write must not be skipped.

        Before the fix: PollView calls poll_state.record_vote() (adds user),
        then adapter calls it again (finds user, returns False), skipping DB.
        After the fix: PollView only checks has_voted(), adapter does everything.
        """
        adapter = RealisticAdapter()
        view = _make_view(adapter)
        interaction = _make_interaction(user_id=222)

        await view.handle_vote(interaction, "A")

        assert len(adapter.db_writes) == 1, (
            "Vote must reach the DB. If this fails, PollView is double-calling "
            "poll_state.record_vote() and the adapter's dedup gate returns False."
        )
        assert adapter.db_writes[0]["user_id"] == 222

    @pytest.mark.asyncio
    async def test_duplicate_vote_still_rejected(self):
        """After first vote, duplicate must be rejected by adapter's dedup."""
        adapter = RealisticAdapter()
        view = _make_view(adapter)

        await view.handle_vote(_make_interaction(user_id=333), "A")
        await view.handle_vote(_make_interaction(user_id=333), "B")

        assert len(adapter.db_writes) == 1

    @pytest.mark.asyncio
    async def test_different_users_both_persisted(self):
        """Two different users voting must both reach DB."""
        adapter = RealisticAdapter()
        view = _make_view(adapter)

        await view.handle_vote(_make_interaction(user_id=444), "A")
        await view.handle_vote(_make_interaction(user_id=555), "B")

        assert len(adapter.db_writes) == 2
        user_ids = {w["user_id"] for w in adapter.db_writes}
        assert user_ids == {444, 555}
