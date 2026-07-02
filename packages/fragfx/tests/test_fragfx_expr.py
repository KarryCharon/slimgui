"""Unit tests for the fragfx expression layer (no GPU required)."""

import pytest

import fragfx as fx
from fragfx import FRAG, DType, Effect, Template, TemplateParams, Vec, wrap
from fragfx.color import rgba
from fragfx.fields import RoundedRect
from fragfx.noise import fbm, noise, simplex
from fragfx.profiles import gauss, smoothfall


def _key_of(color):
    order, index = fx.linearize(color)
    return fx.structure_key(order, index), fx.collect_params(order)


# -- type system -------------------------------------------------------------


def test_binop_type_inference():
    v3 = wrap((1.0, 2.0, 3.0))
    f = wrap(0.5)
    assert (v3 * f).type is DType.VEC3
    assert (f * v3).type is DType.VEC3
    assert (f + 1.0).type is DType.FLOAT


def test_binop_type_mismatch_raises():
    with pytest.raises(TypeError, match="type mismatch"):
        _ = wrap((1.0, 2.0)) + wrap((1.0, 2.0, 3.0))


def test_vec_constructor_sizes():
    assert rgba((1.0, 1.0, 1.0), 0.5).type is DType.VEC4
    with pytest.raises(TypeError):
        Vec(wrap((1.0, 2.0, 3.0)), wrap((1.0, 2.0)))  # 5 components


def test_swizzle_types():
    v4 = wrap((1.0, 2.0, 3.0, 4.0))
    assert v4.rgb.type is DType.VEC3
    assert v4.a.type is DType.FLOAT
    with pytest.raises(TypeError):
        _ = wrap(1.0).x


# -- structure key -------------------------------------------------------------


def _glow(p_min, p_max, rounding, spread, intensity):
    rect = RoundedRect(p_min, p_max, rounding)
    t = fx.math.clamp(rect.sdf / spread, 0.0, 1.0)
    return rgba((0.3, 0.6, 1.0), smoothfall(t) * intensity)


def test_structure_key_value_independent():
    key_a, params_a = _key_of(_glow((0, 0), (100, 50), 10.0, 16.0, 0.5))
    key_b, params_b = _key_of(_glow((5, 5), (90, 40), 8.0, 22.0, 0.3))
    assert key_a == key_b
    assert len(params_a) == len(params_b) and params_a != params_b


def test_structure_key_distinguishes_shapes():
    key_a, _ = _key_of(_glow((0, 0), (100, 50), 10.0, 16.0, 0.5))
    key_b, _ = _key_of(rgba((1.0, 1.0, 1.0), gauss(wrap(0.5))))
    assert key_a != key_b


def test_fbm_octaves_are_structural():
    key_4, _ = _key_of(rgba((1.0, 1.0, 1.0), fbm(FRAG * 0.1, octaves=4)))
    key_6, _ = _key_of(rgba((1.0, 1.0, 1.0), fbm(FRAG * 0.1, octaves=6)))
    assert key_4 != key_6


def test_dag_cse_emits_shared_node_once():
    rect = RoundedRect((0, 0), (10, 10), 2.0)
    color = rgba((1.0, 1.0, 1.0), rect.sdf * rect.sdf)  # sdf reused
    source = fx.dump_glsl(color)
    assert source.count("rounded_rect_sdf(") == 2  # 1 definition + 1 call


# -- noise ---------------------------------------------------------------------


def test_noise_sources_and_dependency_order():
    source = fx.dump_glsl(rgba((1.0, 1.0, 1.0), noise(FRAG * 0.1)))
    assert "float value_noise(vec2 p)" in source
    assert source.index("float hash21") < source.index("float value_noise")

    source = fx.dump_glsl(rgba((1.0, 1.0, 1.0), fbm(FRAG * 0.1, 3)))
    assert "float fbm(vec2 p, int octaves)" in source
    assert " = 3;" in source  # octaves baked as a compile-time int constant
    assert "fbm(" in source

    source = fx.dump_glsl(rgba((1.0, 1.0, 1.0), simplex(FRAG * 0.1)))
    assert "float simplex_noise(vec2 v)" in source


def test_fbm_octave_range_validated():
    with pytest.raises(ValueError):
        fbm(FRAG, octaves=0)
    with pytest.raises(ValueError):
        fbm(FRAG, octaves=9)


# -- library registration --------------------------------------------------------


def test_register_lib_and_lib_call():
    fx.lib.register("test_double_it", """
float test_double_it(float x) { return x * 2.0; }
""")
    color = rgba((1.0, 1.0, 1.0), fx.lib.call("test_double_it", DType.FLOAT, 0.4))
    source = fx.dump_glsl(color)
    assert "float test_double_it(float x)" in source
    assert "test_double_it(" in source


def test_register_lib_rejects_duplicates_and_unknown_deps():
    fx.lib.register("test_once", "float test_once(float x) { return x; }")
    with pytest.raises(ValueError, match="already registered"):
        fx.lib.register("test_once", "float test_once(float x) { return x + 1.0; }")
    with pytest.raises(ValueError, match="unknown"):
        fx.lib.register("test_bad_dep", "float test_bad_dep(float x) { return x; }", deps=("nope",))


def test_lib_call_unknown_name_raises():
    with pytest.raises(KeyError, match="unknown library function"):
        fx.lib.call("definitely_not_registered", DType.FLOAT, 1.0)


# -- dump_glsl & templates ----------------------------------------------------------


def test_dump_glsl_annotates_template_params():
    p = TemplateParams()
    rect = RoundedRect(p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"))
    t = fx.math.clamp(rect.sdf / p.f("spread"), 0.0, 1.0)
    template = Template(rgba(p.vec3("rgb"), smoothfall(t)), p)

    source = fx.dump_glsl(template)
    for name in ("p_min", "p_max", "rounding", "spread", "rgb"):
        assert f"// {name}" in source, f"missing slot annotation for {name}"
    assert "// smooth01" in source  # function call annotation


def test_dump_glsl_accepts_effect_and_expr():
    color = _glow((0, 0), (100, 50), 10.0, 16.0, 0.5)
    assert "void main()" in fx.dump_glsl(color)
    assert "void main()" in fx.dump_glsl(Effect(color, (0, 0), (100, 50)))
    with pytest.raises(TypeError):
        fx.dump_glsl("not an effect")  # type: ignore[arg-type]


def test_template_value_binding_validation():
    p = TemplateParams()
    template = Template(rgba(p.vec3("rgb"), p.f("alpha")), p)
    effect = template.effect((0, 0), (10, 10), rgb=(1, 0, 0), alpha=0.5)
    assert effect.key == template.key
    assert effect.values is not None and 0.5 in effect.values

    with pytest.raises(TypeError, match="missing"):
        template.effect((0, 0), (10, 10), rgb=(1, 0, 0))
    with pytest.raises(TypeError, match="unknown"):
        template.effect((0, 0), (10, 10), rgb=(1, 0, 0), alpha=0.5, bogus=1.0)


def test_template_rejects_unused_params():
    p = TemplateParams()
    p.f("orphan")
    with pytest.raises(ValueError, match="orphan"):
        Template(rgba((1.0, 1.0, 1.0), wrap(0.5)), p)
