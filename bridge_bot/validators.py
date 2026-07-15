import re
from bridge_bot.rate_limiter import RateLimiter

MENTION_PATTERN = re.compile(r'@(everyone|here)', re.IGNORECASE)

_message_rate_limiter = RateLimiter(window_seconds=1.0, max_hits=1)


def check_rate_limit(key: str) -> bool:
    return _message_rate_limiter.allow(key)


def sanitize_mentions(text: str) -> str:
    return MENTION_PATTERN.sub('\u200b@\\1', text)
