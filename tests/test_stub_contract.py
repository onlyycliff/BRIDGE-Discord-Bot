"""Tests for StubBotAdapter — contract fidelity with RealBotAdapter."""

import concurrent.futures
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from bridge_bot.adapter import StubBotAdapter


class TestStubBotAdapterContract:
    """StubBotAdapter must match RealBotAdapter's return types."""

    def test_schedule_coroutine_returns_future(self):
        """RED: schedule_coroutine must return a concurrent.futures.Future.

        RealBotAdapter uses asyncio.run_coroutine_threadsafe() which returns
        a Future. poll_create.py calls future.result(timeout=10) on it.
        StubBotAdapter must match this contract.
        """
        stub = StubBotAdapter()

        async def sample():
            return True

        result = stub.schedule_coroutine(sample())

        assert isinstance(result, concurrent.futures.Future), (
            f"Expected concurrent.futures.Future, got {type(result).__name__}. "
            "poll_create.py calls future.result(timeout=10) on this."
        )

    def test_schedule_coroutine_future_resolves_to_value(self):
        """The Future must resolve to the coroutine's return value."""
        stub = StubBotAdapter()

        async def sample():
            return 42

        future = stub.schedule_coroutine(sample())
        assert future.result(timeout=1) == 42

    def test_schedule_coroutine_future_resolves_false(self):
        """The Future must handle False return values (poll creation failure)."""
        stub = StubBotAdapter()

        async def sample():
            return False

        future = stub.schedule_coroutine(sample())
        assert future.result(timeout=1) is False

    def test_get_event_loop_returns_loop(self):
        """Stub returns an event loop so route guards pass."""
        stub = StubBotAdapter()
        loop = stub.get_event_loop()
        assert loop is not None
        assert not loop.is_closed()
