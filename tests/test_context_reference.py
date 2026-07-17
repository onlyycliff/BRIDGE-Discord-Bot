"""Tests that BotContext dict references survive on_ready population.

The bug: on_ready() reassigns ctx.available_channels = channel_cache.channels,
which replaces the dict object. Any code that captured a reference to the
original dict now points at a stale empty dict.

The fix: mutate the existing dict in place (clear + update) instead of
reassigning. This requires a helper function called from on_ready().
"""

import pytest
from bridge_bot.context import BotContext, populate_from_cache
from bridge_bot.channel_cache import ChannelCache


class FakeChannel:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class FakeRole:
    def __init__(self, id, name, default=False):
        self.id = id
        self.name = name
        self._default = default

    def is_default(self):
        return self._default


class FakeGuild:
    def __init__(self, channels=None, roles=None):
        self.text_channels = channels or []
        self.roles = roles or []

    async def fetch_channels(self):
        pass


class TestPopulateFromCachePreservesReferences:
    """populate_from_cache must mutate dicts in place, not reassign."""

    @pytest.mark.asyncio
    async def test_captured_channels_ref_sees_populated_data(self):
        ctx = BotContext()
        cache = ChannelCache()

        # Capture a reference before population — this is what any
        # early consumer (e.g. RealBotAdapter) would hold.
        channels_ref = ctx.available_channels
        roles_ref = ctx.available_roles

        # Populate the cache.
        ch = FakeChannel(111, "general")
        role = FakeRole(222, "Coach")
        guild = FakeGuild(channels=[ch], roles=[role])
        await cache.refresh([guild])

        # Populate ctx from the cache.
        populate_from_cache(ctx, cache)

        # The captured reference must see the populated data.
        assert channels_ref == {111: "general"}
        assert roles_ref == {222: "Coach"}
        # The ctx attributes must also be correct.
        assert ctx.available_channels == {111: "general"}
        assert ctx.available_roles == {222: "Coach"}
        # Crucially, the captured ref must BE the same object.
        assert channels_ref is ctx.available_channels
        assert roles_ref is ctx.available_roles

    @pytest.mark.asyncio
    async def test_empty_cache_clears_previous_data(self):
        ctx = BotContext()
        cache = ChannelCache()

        channels_ref = ctx.available_channels

        # First population.
        ch = FakeChannel(111, "general")
        guild = FakeGuild(channels=[ch])
        await cache.refresh([guild])
        populate_from_cache(ctx, cache)
        assert channels_ref == {111: "general"}

        # Second population with different data.
        await cache.refresh([])
        populate_from_cache(ctx, cache)

        # The ref must reflect the new (empty) state.
        assert channels_ref == {}
        assert channels_ref is ctx.available_channels
