"""Tests for ChannelCache — channel resolution module."""

import pytest
from bridge_bot.channel_cache import ChannelCache


class FakeChannel:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class FakeGuild:
    def __init__(self, channels=None, roles=None):
        self.text_channels = channels or []
        self.roles = roles or []

    async def fetch_channels(self):
        pass


class FakeRole:
    def __init__(self, id, name, default=False):
        self.id = id
        self.name = name
        self._default = default

    def is_default(self):
        return self._default


class FakeBot:
    def __init__(self, channels=None):
        self._channels = {ch.id: ch for ch in (channels or [])}

    def get_channel(self, channel_id):
        return self._channels.get(channel_id)

    async def fetch_channel(self, channel_id):
        ch = self._channels.get(channel_id)
        if ch is None:
            raise Exception(f"Channel {channel_id} not found")
        return ch


class TestChannelCacheRefresh:
    @pytest.mark.asyncio
    async def test_populates_channels_and_roles(self):
        cache = ChannelCache()
        ch = FakeChannel(111, "general")
        role = FakeRole(222, "Coach")
        default_role = FakeRole(333, "@everyone", default=True)
        guild = FakeGuild(channels=[ch], roles=[role, default_role])

        await cache.refresh([guild])

        assert cache.channels == {111: "general"}
        assert cache.roles == {222: "Coach"}
        assert 333 not in cache.roles

    @pytest.mark.asyncio
    async def test_clears_on_refresh(self):
        cache = ChannelCache()
        cache.channels = {999: "old"}
        await cache.refresh([])
        assert cache.channels == {}


class TestChannelCacheLookups:
    def test_get_channel_name(self):
        cache = ChannelCache()
        cache.channels = {111: "general"}
        assert cache.get_channel_name(111) == "general"
        assert cache.get_channel_name(999) == "Unknown"

    def test_get_role_name(self):
        cache = ChannelCache()
        cache.roles = {222: "Coach"}
        assert cache.get_role_name(222) == "Coach"
        assert cache.get_role_name(999) == "Unknown"

    def test_is_valid_role(self):
        cache = ChannelCache()
        cache.roles = {222: "Coach"}
        assert cache.is_valid_role(222) is True
        assert cache.is_valid_role(999) is False


class TestChannelCacheResolve:
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        cache = ChannelCache()
        ch = FakeChannel(111, "general")
        bot = FakeBot(channels=[ch])
        cache.set_bot(bot)
        await cache.refresh([FakeGuild(channels=[ch])])

        result = await cache.resolve(111)
        assert result is ch

    @pytest.mark.asyncio
    async def test_cache_miss_api_fallback(self):
        cache = ChannelCache()
        ch = FakeChannel(111, "general")
        bot = FakeBot(channels=[ch])
        cache.set_bot(bot)
        # Don't populate cache — should still find via fetch_channel
        result = await cache.resolve(111)
        assert result is ch

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        cache = ChannelCache()
        bot = FakeBot(channels=[])
        cache.set_bot(bot)

        result = await cache.resolve(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_bot_returns_none(self):
        cache = ChannelCache()
        result = await cache.resolve(111)
        assert result is None
