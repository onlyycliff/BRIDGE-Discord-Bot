# Domain Glossary — BRIDGE 2026

## Core Domain

- **Poll** — A multiple-choice question posted to Discord. Has 2–5 options, a channel, and an optional description. States: active, ended.
- **Vote** — A user's selection on a poll option. One vote per user per poll. Stored in-memory (poll_state) and persisted to PostgreSQL.
- **PollState** — In-memory cache of active polls and their vote tallies. Backed by DB fallback on cache miss.
- **Tour** — An industry tour (company visit). Has a name and metadata. Coaches create tours; participants submit feedback.
- **TourFeedback** — A participant's response to a tour: star rating, free-text response, GitHub profile link.
- **Coach** — An authenticated dashboard user. Linked to a Discord user ID. Can manage polls and view analytics.

## Infrastructure Modules

- **BotAdapter** — The seam between the Flask API and the Discord bot. Abstract base class with methods for every bot interaction. RealBotAdapter calls Discord; StubBotAdapter records calls for tests.
- **AsyncBridge** — Background event loop thread that bridges sync Flask handlers to async SQLAlchemy operations.
- **PollState** — In-memory active poll cache with DB fallback. Accessed through the adapter seam.
- **AppFactory** — `create_app()` factory for the Flask application. Replaces module-level side effects in dashboard.py.
- **BotContext** — Dataclass holding bot state (bot instance, channel ID, start time, caches). Injected into extracted modules.
- **RateLimiter** — Single class with pluggable backend (DictBackend / RedisBackend). Replaces dual in-memory rate limiters.
- **ChannelCache** — Manages Discord channel and role lookups. Refreshed on bot ready.
- **PollOrchestrator** — Poll lifecycle management (`send_poll`, `end_poll_and_send_results`). Uses BotContext.

## Repository Layer

- **PollRepository** — Data access for polls, votes, poll stats, poll metadata.
- **TourRepository** — Data access for tours and feedback.
- **CoachRepository** — Data access for coach authentication and lookup.

## Decisions

- **C1 — App factory**: Two-tier pattern. `create_app()` with `BOT_START` env var gate. `app = create_app()` kept at module level for gunicorn.
- **C2 — Repository split**: Each repo takes a `session` via constructor. Old `repository.py` kept as backward-compatible facade.
- **C3 — Adapter seam**: `record_vote()` added to BotAdapter ABC. RealBotAdapter delegates to PollState + DB. StubBotAdapter has in-memory dedup.
- **C4 — bot.py decomposition**: Embeds extracted to `embeds.py`. Channel cache to `ChannelCache` class. Poll orchestration to `poll_orchestrator.py`. `BotContext` replaces module-level globals.
- **C5 — Rate limiter**: `RateLimiter` class with `RateLimitBackend` ABC. `DictBackend` for dev/test, `RedisBackend` for production. Pluggable via constructor.
