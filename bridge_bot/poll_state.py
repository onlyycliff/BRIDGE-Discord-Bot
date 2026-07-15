import logging
from typing import Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


class PollState:
    """Centralized poll state management.

    The in-memory dicts serve as a fast cache. When a poll isn't found
    in memory (e.g. after a bot restart), the optional DB checkers are
    consulted as source of truth.
    """

    def __init__(self):
        self.polls: Dict[int, object] = {}
        self.user_votes: Dict[int, Set[int]] = {}
        self.active: Dict[int, bool] = {}
        self._db_is_active: Optional[Callable] = None
        self._db_has_voted: Optional[Callable] = None

    def set_db_checkers(
        self,
        is_active_fn: Optional[Callable] = None,
        has_voted_fn: Optional[Callable] = None,
    ) -> None:
        self._db_is_active = is_active_fn
        self._db_has_voted = has_voted_fn

    def add_poll(self, poll_id: int, poll_view: object) -> None:
        self.polls[poll_id] = poll_view
        self.user_votes[poll_id] = set()
        self.active[poll_id] = True
        logger.info(f"Poll {poll_id} registered")

    def has_voted(self, poll_id: int, user_id: int) -> bool:
        if user_id in self.user_votes.get(poll_id, set()):
            return True
        if self._db_has_voted:
            from bridge_bot.async_bridge import run_sync
            try:
                result = run_sync(self._db_has_voted(poll_id, user_id))
                if result:
                    self.user_votes.setdefault(poll_id, set()).add(user_id)
                return result
            except Exception as e:
                logger.warning(f"DB has_voted check failed for poll {poll_id}: {e}")
        return False

    def record_vote(self, poll_id: int, user_id: int) -> bool:
        if self.has_voted(poll_id, user_id):
            return False
        self.user_votes.setdefault(poll_id, set()).add(user_id)
        return True

    def end_poll(self, poll_id: int) -> bool:
        self.active[poll_id] = False
        self.user_votes.pop(poll_id, None)
        logger.info(f"Poll {poll_id} ended")
        return True

    def is_active(self, poll_id: int) -> bool:
        if self.active.get(poll_id, False):
            return True
        if self._db_is_active:
            from bridge_bot.async_bridge import run_sync
            try:
                result = run_sync(self._db_is_active(poll_id))
                if result:
                    self.active[poll_id] = True
                return result
            except Exception as e:
                logger.warning(f"DB is_active check failed for poll {poll_id}: {e}")
        return False

    def rehydrate(self, active_poll_ids: set) -> None:
        """Load active poll IDs from DB on startup."""
        for poll_id in active_poll_ids:
            if poll_id not in self.active:
                self.active[poll_id] = True
                logger.info(f"Rehydrated poll {poll_id} as active")

    def get_poll_data(self, poll_id: int) -> Optional[Dict]:
        poll = self.polls.get(poll_id)
        if not poll:
            return None
        return {
            "poll_id": poll_id,
            "question": poll.question,
            "options": poll.options,
            "votes": poll.votes,
            "total_votes": sum(poll.votes.values()),
            "voters": list(self.user_votes.get(poll_id, set()))
        }


poll_state = PollState()
