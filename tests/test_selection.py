import pytest

from hub_app.selection import SelectionTracker, x_to_index


def test_x_to_index_two_cards_boundaries():
    expected = {0.0: 0, 0.15: 0, 0.49: 0, 0.51: 1, 0.85: 1, 1.0: 1}
    for x, index in expected.items():
        assert x_to_index(x, 2, 0.15, 0.85) == index, x


def test_x_to_index_three_cards():
    assert x_to_index(0.15, 3, 0.15, 0.85) == 0
    assert x_to_index(0.5, 3, 0.15, 0.85) == 1
    assert x_to_index(0.85, 3, 0.15, 0.85) == 2
    assert x_to_index(1.0, 3, 0.15, 0.85) == 2


def test_x_to_index_single_card_always_zero():
    assert x_to_index(0.0, 1, 0.15, 0.85) == 0
    assert x_to_index(1.0, 1, 0.15, 0.85) == 0


def test_x_to_index_zero_cards_raises():
    with pytest.raises(ValueError):
        x_to_index(0.5, 0, 0.15, 0.85)


def test_tracker_does_not_switch_just_past_midpoint():
    tracker = SelectionTracker(2, start=0)

    assert tracker.update_from_x(0.52) == 0


def test_tracker_switches_past_midpoint_plus_margin():
    tracker = SelectionTracker(2, start=0)

    assert tracker.update_from_x(0.56) == 1


def test_tracker_switches_back_only_past_margin():
    tracker = SelectionTracker(2, start=1)

    assert tracker.update_from_x(0.48) == 1
    assert tracker.update_from_x(0.44) == 0


def test_tracker_none_keeps_index():
    tracker = SelectionTracker(2, start=1)

    assert tracker.update_from_x(None) == 1
    assert tracker.index == 1


def test_tracker_start_index_is_kept():
    assert SelectionTracker(3, start=2).index == 2


def test_tracker_step_clamps_without_wrap():
    tracker = SelectionTracker(2, start=0)

    assert tracker.step(-1) == 0
    assert tracker.step(1) == 1
    assert tracker.step(1) == 1
    assert tracker.step(-5) == 0


def test_tracker_zero_cards_raises():
    with pytest.raises(ValueError):
        SelectionTracker(0)
