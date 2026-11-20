import math

import pytest

from hub_app.gestures import HoldConfirm, PinchDetector, pinch_ratio


def make_landmarks(thumb_tip, index_tip, wrist=(0.0, 0.0), middle_mcp=(0.0, 1.0)):
    lms = [(0.5, 0.5)] * 21
    lms[0] = wrist
    lms[4] = thumb_tip
    lms[8] = index_tip
    lms[9] = middle_mcp
    return lms


def test_pinch_ratio_is_thumb_index_distance_over_palm_size():
    lms = make_landmarks(thumb_tip=(0.0, 0.0), index_tip=(0.3, 0.0))

    assert pinch_ratio(lms) == pytest.approx(0.3)


def test_pinch_ratio_is_scale_invariant():
    lms = make_landmarks(thumb_tip=(0.0, 0.0), index_tip=(0.6, 0.0), middle_mcp=(0.0, 2.0))

    assert pinch_ratio(lms) == pytest.approx(0.3)


def test_pinch_ratio_survives_zero_palm_size():
    lms = make_landmarks(
        thumb_tip=(0.0, 0.0), index_tip=(0.1, 0.0), wrist=(0.2, 0.2), middle_mcp=(0.2, 0.2)
    )

    assert math.isfinite(pinch_ratio(lms))


def test_pinch_detector_hysteresis_sequence():
    detector = PinchDetector(on=0.35, off=0.50)

    observed = [detector.update(r) for r in (0.4, 0.3, 0.45, 0.55)]

    assert observed == [False, True, True, False]


def test_pinch_detector_none_resets_state():
    detector = PinchDetector(on=0.35, off=0.50)
    assert detector.update(0.3) is True

    assert detector.update(None) is False
    assert detector.pinched is False
    # Ratio between on and off no longer keeps it pinched after a reset.
    assert detector.update(0.45) is False


def test_hold_confirm_does_not_fire_before_hold_time():
    hold = HoldConfirm(hold_s=0.8)

    assert hold.update(True, 0.0) is False
    assert hold.update(True, 0.79) is False


def test_hold_confirm_fires_once_at_hold_time_and_not_while_held():
    hold = HoldConfirm(hold_s=0.8)
    hold.update(True, 0.0)

    assert hold.update(True, 0.8) is True
    assert hold.update(True, 0.9) is False
    assert hold.update(True, 1.5) is False


def test_hold_confirm_fires_again_after_release_and_rehold():
    hold = HoldConfirm(hold_s=0.8)
    hold.update(True, 0.0)
    assert hold.update(True, 0.8) is True

    assert hold.update(False, 1.0) is False
    assert hold.update(True, 1.1) is False
    assert hold.update(True, 2.0) is True


def test_hold_confirm_progress_is_clamped():
    hold = HoldConfirm(hold_s=0.8)
    assert hold.progress(5.0) == 0.0

    hold.update(True, 0.0)

    assert hold.progress(0.4) == pytest.approx(0.5)
    assert hold.progress(5.0) == 1.0
    assert 0.0 <= hold.progress(-1.0) <= 1.0


def test_hold_confirm_reset_clears_progress():
    hold = HoldConfirm(hold_s=0.8)
    hold.update(True, 0.0)

    hold.reset()

    assert hold.progress(0.4) == 0.0
