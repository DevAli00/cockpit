from datetime import UTC, datetime, timedelta

import pytest

from app.domain.tasks import (
    REBALANCE_GAP,
    done_at_for_move,
    is_visible_on_board,
    needs_rebalance,
    position_between,
)

NOW = datetime(2026, 3, 20, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("prev", "nxt", "expected"),
    [(None, None, 1.0), (None, 5.0, 4.0), (5.0, None, 6.0), (2.0, 4.0, 3.0)],
)
def test_position_between(prev: float | None, nxt: float | None, expected: float) -> None:
    assert position_between(prev, nxt) == expected


def test_position_between_rejects_inverted_neighbours() -> None:
    with pytest.raises(ValueError):
        position_between(5.0, 2.0)


def test_needs_rebalance_when_gap_collapses() -> None:
    assert needs_rebalance(1.0, 1.0 + REBALANCE_GAP / 2)
    assert not needs_rebalance(1.0, 2.0)
    assert not needs_rebalance(None, 2.0)


def test_done_at_set_on_entering_done_and_cleared_on_leaving() -> None:
    assert done_at_for_move("todo", "done", None, NOW) == NOW
    assert done_at_for_move("done", "todo", NOW, NOW) is None


def test_done_at_untouched_when_staying_in_done_or_elsewhere() -> None:
    earlier = NOW - timedelta(days=2)
    assert done_at_for_move("done", "done", earlier, NOW) == earlier
    assert done_at_for_move("todo", "ongoing", None, NOW) is None


def test_done_tasks_hidden_after_a_week_but_others_always_visible() -> None:
    assert is_visible_on_board("todo", None, NOW)
    assert is_visible_on_board("done", NOW - timedelta(days=6), NOW)
    assert not is_visible_on_board("done", NOW - timedelta(days=8), NOW)
    assert is_visible_on_board("done", None, NOW)  # legacy row without timestamp stays visible
