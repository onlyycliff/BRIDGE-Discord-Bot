import re
import time
from typing import Dict


MENTION_PATTERN = re.compile(r'@(everyone|here)', re.IGNORECASE)

_rate_limit_store: Dict[str, float] = {}
RATE_LIMIT_WINDOW = 1.0


def check_rate_limit(key: str) -> bool:
    now = time.time()
    last = _rate_limit_store.get(key)
    if last and now - last < RATE_LIMIT_WINDOW:
        return False
    _rate_limit_store[key] = now
    return True


def sanitize_mentions(text: str) -> str:
    return MENTION_PATTERN.sub('\u200b@\\1', text)
