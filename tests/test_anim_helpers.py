import pytest

from slimgui import anim


def test_eval_preset_endpoints():
    assert anim.eval_preset(anim.EASE_LINEAR, 0.0) == pytest.approx(0.0)
    assert anim.eval_preset(anim.EASE_LINEAR, 1.0) == pytest.approx(1.0)
    assert anim.eval_preset(anim.EASE_OUT_QUAD, 0.5) == pytest.approx(0.75)


def test_curve_helpers_return_vec2_tuples():
    p0 = (0.0, 0.0)
    p1 = (0.0, 1.0)
    p2 = (1.0, 1.0)
    p3 = (1.0, 0.0)

    assert anim.bezier_cubic(p0, p1, p2, p3, 0.0) == pytest.approx(p0)
    assert anim.bezier_cubic(p0, p1, p2, p3, 1.0) == pytest.approx(p3)

    mid = anim.catmull_rom(p0, p1, p2, p3, 0.5)
    assert isinstance(mid, tuple)
    assert len(mid) == 2


def test_color_gradient_and_transform_helpers():
    gradient = anim.Gradient.two_color((1.0, 0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0))
    assert gradient.stop_count == 2
    assert gradient.sample(0.0) == pytest.approx((1.0, 0.0, 0.0, 1.0))

    transform = anim.Transform((10.0, 20.0), 0.0, (2.0, 2.0))
    assert transform.apply((1.0, 1.0)) == pytest.approx((12.0, 22.0))
