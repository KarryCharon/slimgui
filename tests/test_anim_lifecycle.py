import pytest

from slimgui import anim, imgui


@pytest.fixture
def imgui_context():
    imgui.set_nanobind_leak_warnings(True)
    ctx = imgui.create_context()
    imgui.get_io().ini_filename = None
    yield ctx
    anim.clip_shutdown()
    anim.pool_clear()
    imgui.destroy_context(ctx)


def test_hash_str_is_stable():
    assert anim.hash_str("button.shimmer") == anim.hash_str("button.shimmer")
    assert anim.hash_str("button.shimmer") != anim.hash_str("button.other")


def test_tween_float_advances_with_imgui_delta_time(imgui_context):
    io = imgui.get_io()
    ease = anim.ease_preset(anim.EASE_LINEAR)
    item_id = anim.hash_str("test.item")
    channel = anim.hash_str("alpha")

    io.delta_time = 0.0
    anim.update_begin_frame()
    start = anim.tween_float(item_id, channel, 1.0, 1.0, ease, anim.POLICY_CROSSFADE, io.delta_time)
    assert start == pytest.approx(0.0)

    io.delta_time = 0.5
    anim.update_begin_frame()
    halfway = anim.tween_float(item_id, channel, 1.0, 1.0, ease, anim.POLICY_CROSSFADE, io.delta_time)
    assert halfway == pytest.approx(0.5)


def test_path_and_clip_basic_flow(imgui_context):
    path_id = anim.hash_str("path.basic")
    anim.Path.begin(path_id, (0.0, 0.0)).line_to((10.0, 0.0)).end()

    assert anim.path_exists(path_id)
    assert anim.path_evaluate(path_id, 0.5) == pytest.approx((5.0, 0.0))

    clip_id = anim.hash_str("clip.basic")
    instance_id = anim.hash_str("clip.instance")
    channel = anim.hash_str("x")

    anim.Clip.begin(clip_id).key_float(channel, 0.0, 0.0).key_float(channel, 1.0, 10.0).end()
    inst = anim.play(clip_id, instance_id)
    assert inst.valid

    anim.clip_update(0.5)
    value = inst.get_float(channel)
    assert value is not None
    assert 0.0 <= value <= 10.0
