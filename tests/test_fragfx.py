"""Tests for the standalone fragfx library: namespaces, dialect injection,
per-dialect library registry, and slimgui-independence."""

import subprocess
import sys

import pytest

import fragfx as fx


def test_namespaced_vocabulary():
    rect = fx.fields.RoundedRect((0.0, 0.0), (100.0, 50.0), 8.0)
    sweep = fx.profiles.gauss(fx.profiles.wrap_delta(rect.path_t, 0.3) / 0.1)
    color = fx.color.rgba(fx.color.hsv2rgb(fx.math.fract(rect.path_t), 0.85, 1.0), sweep)
    assert color.type is fx.DType.VEC4
    src = fx.dump_glsl(color)
    assert "rect_path_t" in src and "hsv2rgb" in src


def test_presets_return_prebound_effects():
    e = fx.effects.glass_pad((0.0, 0.0), (100.0, 50.0), rounding=8.0)
    assert isinstance(e, fx.Effect)
    assert e.key is not None and e.values is not None
    assert len(fx.preset_templates()) == 23


def test_structure_key_is_dialect_independent():
    e = fx.effects.soft_glow_rect((0.0, 0.0), (10.0, 10.0))
    order, index = fx.linearize(e.color)
    assert fx.structure_key(order, index) == e.key


def test_dialect_injection_assemble_override():
    class EsDialect(fx.glsl.GlslDialect):
        def assemble(self, gen: fx.GeneratedSource) -> str:
            return "#version 300 es\nprecision highp float;\n" + gen.libs + "\nvoid main() {\n" + gen.body + "\n}\n"

    e = fx.effects.focus_ring((0.0, 0.0), (10.0, 10.0))
    order, index = fx.linearize(e.color)
    dialect = EsDialect()
    gen = fx.generate(order, index, dialect=dialect)
    src = dialect.assemble(gen)
    assert src.startswith("#version 300 es")
    # body is shared with the default dialect (only the shell differs)
    assert gen.body == fx.generate(order, index).body


def test_lib_registry_dialect_dimension():
    fx.lib.register("t_dialect_dim", "float t_dialect_dim(float x) { return x; }\n")
    fx.lib.register("t_dialect_dim", "fn t_dialect_dim(x: f32) -> f32 { return x; }\n", dialect="wgsl")
    assert "t_dialect_dim" in fx.lib.LIBRARY
    glsl_src = fx.lib.LIBRARY.sources(["t_dialect_dim"], "glsl")
    wgsl_src = fx.lib.LIBRARY.sources(["t_dialect_dim"], "wgsl")
    assert "float" in glsl_src and "f32" in wgsl_src
    with pytest.raises(ValueError, match="already registered"):
        fx.lib.register("t_dialect_dim", "...")
    node = fx.lib.call("t_dialect_dim", fx.DType.FLOAT, fx.FRAG.x)
    assert "t_dialect_dim" in fx.dump_glsl(fx.color.rgba((1.0, 1.0, 1.0), node))


def test_numbers_lift_to_uniforms():
    a = fx.fields.RoundedRect((0.0, 0.0), (10.0, 10.0), 1.0).sdf / 4.0
    b = fx.fields.RoundedRect((5.0, 5.0), (90.0, 40.0), 9.0).sdf / 7.5
    ca = fx.color.rgba((1.0, 1.0, 1.0), a)
    cb = fx.color.rgba((0.0, 0.5, 1.0), b)
    ka = fx.structure_key(*fx.linearize(ca))
    kb = fx.structure_key(*fx.linearize(cb))
    assert ka == kb  # values differ, shape identical -> same program


def test_fragfx_imports_without_slimgui():
    """fragfx must work in a process where slimgui can never be imported."""
    code = (
        "import sys; sys.modules['slimgui'] = None\n"
        "import fragfx as fx\n"
        "e = fx.effects.metal_pad((0, 0), (64, 32), rounding=6.0)\n"
        "assert fx.dump_glsl(e).startswith('#version 330')\n"
        "assert not any(n.split('.')[0] == 'imgui' for n in sys.modules)\n"
        "print('ok')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"
