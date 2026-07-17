"""Tests for shared repository operation helpers."""

import sys
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from unittest.mock import AsyncMock, patch, MagicMock
from db.operations import poll_op, tour_op


class TestPollOp:
    @pytest.mark.asyncio
    async def test_calls_correct_method(self):
        mock_repo = MagicMock()
        mock_repo.get_all_polls = AsyncMock(return_value=["poll1"])

        with patch("db.operations.PollRepository", return_value=mock_repo):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with patch("db.operations.get_session", return_value=mock_session):
                result = await poll_op("get_all_polls")

        assert result == ["poll1"]
        mock_repo.get_all_polls.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        mock_repo = MagicMock()
        mock_repo.get_poll_stats = AsyncMock(return_value={"count": 5})

        with patch("db.operations.PollRepository", return_value=mock_repo):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with patch("db.operations.get_session", return_value=mock_session):
                await poll_op("get_poll_stats", 42, include_voters=True)

        mock_repo.get_poll_stats.assert_called_once_with(42, include_voters=True)


class TestTourOp:
    @pytest.mark.asyncio
    async def test_calls_correct_method(self):
        mock_repo = MagicMock()
        mock_repo.get_all_tours = AsyncMock(return_value=["tour1"])

        with patch("db.operations.TourRepository", return_value=mock_repo):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with patch("db.operations.get_session", return_value=mock_session):
                result = await tour_op("get_all_tours")

        assert result == ["tour1"]
        mock_repo.get_all_tours.assert_called_once()
