"""GLSL sources for the built-in library functions. Loops and branches are
free *inside* library functions; the expression layer stays branch-free."""

from __future__ import annotations

from ..lib import LIBRARY

LIBRARY.register(
    "smooth01",
    """
float smooth01(float edge0, float edge1, float x) {
    float t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}
""",
)

LIBRARY.register(
    "rounded_rect_sdf",
    """
float rounded_rect_sdf(vec2 p, vec2 p_min, vec2 p_max, float rounding) {
    vec2 center = (p_min + p_max) * 0.5;
    vec2 half_size = (p_max - p_min) * 0.5;
    float r = clamp(rounding, 0.0, min(half_size.x, half_size.y));
    vec2 q = abs(p - center) - (half_size - vec2(r));
    return length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - r;
}
""",
)

LIBRARY.register(
    "hsv2rgb",
    """
vec3 hsv2rgb(float h, float s, float v) {
    vec3 k = mod(vec3(5.0, 3.0, 1.0) + h * 6.0, 6.0);
    return v - v * s * clamp(min(k, 4.0 - k), 0.0, 1.0);
}
""",
)

# Perimeter parameterization matching vfx_rounded_rect_point_at():
# top edge -> tr arc -> right edge -> br arc -> bottom edge -> bl arc ->
# left edge -> tl arc.
# Every `else` body below must stay braced: Blender 5.2's GLSL preprocessor
# (shader_tool grammar, upstream #161299) corrupts the heap on `else <stmt>;`.
LIBRARY.register(
    "rect_path_t",
    """
float rect_path_t(vec2 p, vec2 p_min, vec2 p_max, float rounding) {
    vec2 size = p_max - p_min;
    float r = clamp(rounding, 0.0, min(size.x, size.y) * 0.5);
    float top_len = max(size.x - 2.0 * r, 0.0);
    float side_len = max(size.y - 2.0 * r, 0.0);
    float arc_len = HALF_PI * r;
    float per = 2.0 * top_len + 2.0 * side_len + 4.0 * arc_len;
    if (per <= 0.0) return 0.0;

    vec2 ic_min = p_min + vec2(r);
    vec2 ic_max = p_max - vec2(r);
    bool corner_x = p.x < ic_min.x || p.x > ic_max.x;
    bool corner_y = p.y < ic_min.y || p.y > ic_max.y;
    float s;

    if (corner_x && corner_y && r > 0.0) {
        bool right = p.x > ic_max.x;
        bool bottom = p.y > ic_max.y;
        vec2 cc = vec2(right ? ic_max.x : ic_min.x, bottom ? ic_max.y : ic_min.y);
        float a = atan(p.y - cc.y, p.x - cc.x);
        if (right && !bottom) {
            s = top_len + (a + HALF_PI) / HALF_PI * arc_len;
        } else if (right && bottom) {
            s = top_len + arc_len + side_len + a / HALF_PI * arc_len;
        } else if (!right && bottom) {
            s = 2.0 * top_len + 2.0 * arc_len + side_len + (a - HALF_PI) / HALF_PI * arc_len;
        } else {
            s = 2.0 * top_len + 3.0 * arc_len + 2.0 * side_len + (a + PI) / HALF_PI * arc_len;
        }
    } else {
        float dt = p.y - p_min.y;
        float db = p_max.y - p.y;
        float dl = p.x - p_min.x;
        float dr = p_max.x - p.x;
        float m = min(min(dt, db), min(dl, dr));
        if (m == dt) {
            s = clamp(p.x - ic_min.x, 0.0, top_len);
        } else if (m == dr) {
            s = top_len + arc_len + clamp(p.y - ic_min.y, 0.0, side_len);
        } else if (m == db) {
            s = top_len + 2.0 * arc_len + side_len + clamp(ic_max.x - p.x, 0.0, top_len);
        } else {
            s = 2.0 * top_len + 3.0 * arc_len + side_len + clamp(ic_max.y - p.y, 0.0, side_len);
        }
    }
    return fract(s / per);
}
""",
)

LIBRARY.register(
    "rect_point_at",
    """
vec2 rect_point_at(vec2 p_min, vec2 p_max, float rounding, float t) {
    vec2 size = p_max - p_min;
    float r = clamp(rounding, 0.0, min(size.x, size.y) * 0.5);
    float top_len = max(size.x - 2.0 * r, 0.0);
    float side_len = max(size.y - 2.0 * r, 0.0);
    float arc_len = HALF_PI * r;
    float per = 2.0 * top_len + 2.0 * side_len + 4.0 * arc_len;
    if (per <= 0.0) return (p_min + p_max) * 0.5;

    float s = fract(t) * per;
    if (s < top_len) return vec2(p_min.x + r + s, p_min.y);
    s -= top_len;
    if (s < arc_len) {
        float a = -HALF_PI + (arc_len > 0.0 ? s / arc_len : 0.0) * HALF_PI;
        return vec2(p_max.x - r + cos(a) * r, p_min.y + r + sin(a) * r);
    }
    s -= arc_len;
    if (s < side_len) return vec2(p_max.x, p_min.y + r + s);
    s -= side_len;
    if (s < arc_len) {
        float a = (arc_len > 0.0 ? s / arc_len : 0.0) * HALF_PI;
        return vec2(p_max.x - r + cos(a) * r, p_max.y - r + sin(a) * r);
    }
    s -= arc_len;
    if (s < top_len) return vec2(p_max.x - r - s, p_max.y);
    s -= top_len;
    if (s < arc_len) {
        float a = HALF_PI + (arc_len > 0.0 ? s / arc_len : 0.0) * HALF_PI;
        return vec2(p_min.x + r + cos(a) * r, p_max.y - r + sin(a) * r);
    }
    s -= arc_len;
    if (s < side_len) return vec2(p_min.x, p_max.y - r - s);
    s -= side_len;
    float a = PI + (arc_len > 0.0 ? s / arc_len : 0.0) * HALF_PI;
    return vec2(p_min.x + r + cos(a) * r, p_min.y + r + sin(a) * r);
}
""",
)

LIBRARY.register(
    "rounded_rect_sdf_flags",
    """
float square_rect_sdf(vec2 p, vec2 p_min, vec2 p_max) {
    vec2 center = (p_min + p_max) * 0.5;
    vec2 half_size = (p_max - p_min) * 0.5;
    vec2 q = abs(p - center) - half_size;
    return length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0);
}

int fix_corner_flags(int flags) {
    flags = flags & 240;
    if (flags == 0) return 240;
    if ((flags & 256) != 0) return 256;
    return flags;
}

float rounded_rect_sdf_flags(vec2 p, vec2 p_min, vec2 p_max, float rounding, int flags) {
    float w = p_max.x - p_min.x;
    float h = p_max.y - p_min.y;
    rounding = clamp(rounding, 0.0, min(w, h) * 0.5);
    flags = fix_corner_flags(flags);

    if (rounding <= 0.0 || flags == 256)
        return square_rect_sdf(p, p_min, p_max);
    if (flags == 240) {
        vec2 center = (p_min + p_max) * 0.5;
        vec2 half_size = (p_max - p_min) * 0.5;
        vec2 q = abs(p - center) - (half_size - vec2(rounding));
        return length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - rounding;
    }

    float left = p_min.x + rounding;
    float right = p_max.x - rounding;
    float top = p_min.y + rounding;
    float bottom = p_max.y - rounding;

    if ((flags & 16) != 0 && p.x < left && p.y < top)
        return length(p - vec2(left, top)) - rounding;
    if ((flags & 32) != 0 && p.x > right && p.y < top)
        return length(p - vec2(right, top)) - rounding;
    if ((flags & 128) != 0 && p.x > right && p.y > bottom)
        return length(p - vec2(right, bottom)) - rounding;
    if ((flags & 64) != 0 && p.x < left && p.y > bottom)
        return length(p - vec2(left, bottom)) - rounding;

    return square_rect_sdf(p, p_min, p_max);
}
""",
)

# Principled-lite material pad. The surface model is fixed: a flat plateau
# and a convex quarter-circle shoulder at the border, lit by a directional
# light. Each material (glass, metal, ...) is a point in the (metallic,
# roughness, specular) parameter space. No backdrop sampling.
LIBRARY.register(
    "material_pad",
    """
vec4 material_pad(vec2 p, vec2 p_min, vec2 p_max, float rounding, float intensity,
                  vec4 tint, float thickness, float angle, float metallic,
                  float roughness, float specular, float shoulder_soft) {
    vec2 size = max(p_max - p_min, vec2(1.0));
    float th = clamp(thickness, 2.0, 0.5 * min(size.x, size.y));

    float sd = rounded_rect_sdf(p, p_min, p_max, rounding);
    float aa = 1.0 - smooth01(-1.5, 0.0, sd);
    if (aa <= 0.0) return vec4(0.0);

    vec2 g = normalize(vec2(
        rounded_rect_sdf(p + vec2(1.0, 0.0), p_min, p_max, rounding)
            - rounded_rect_sdf(p - vec2(1.0, 0.0), p_min, p_max, rounding),
        rounded_rect_sdf(p + vec2(0.0, 1.0), p_min, p_max, rounding)
            - rounded_rect_sdf(p - vec2(0.0, 1.0), p_min, p_max, rounding))
        + vec2(1e-5, 0.0));

    float x = clamp((th + sd) / th, 0.0, 1.0);
    float n_cos = x * smooth01(0.0, max(shoulder_soft, 1e-3), x);
    float n_sin = sqrt(max(1.0 - n_cos * n_cos, 0.0));
    vec3 N = vec3(g * n_cos, n_sin);

    vec3 L = normalize(vec3(sin(angle) * 0.6, -cos(angle) * 0.6, 0.8));
    vec3 Hv = normalize(L + vec3(0.0, 0.0, 1.0));
    float ndl = dot(N, L);
    float ndh = max(dot(N, Hv), 0.0);

    float k = clamp(intensity, 0.0, 1.0);
    float met = clamp(metallic, 0.0, 1.0);
    float rough = clamp(roughness, 0.05, 1.0);
    vec3 base = tint.rgb;
    vec3 col = base;

    vec2 ldir = normalize(L.xy + vec2(1e-5, 0.0));
    vec2 rel_p = (p - 0.5 * (p_min + p_max)) / (0.5 * length(size));
    col *= 1.0 + clamp(dot(rel_p, ldir), -1.0, 1.0) * mix(0.08, 0.20, met) * k;

    float rel = ndl - L.z;
    float lit_t = clamp(rel / (1.0 - L.z), 0.0, 1.0);
    float dark_t = clamp(-rel / (L.z + 0.6), 0.0, 1.0);
    col = mix(col, vec3(1.0), pow(lit_t, 1.5) * 0.85 * (1.0 - 0.65 * met) * k);
    col = mix(col, vec3(0.0), pow(dark_t, 1.2) * mix(0.5, 0.75, met) * k);

    float spec_t = clamp((ndh - Hv.z) / max(1.0 - Hv.z, 1e-4), 0.0, 1.0);
    float expo = mix(10.0, 1.6, rough);
    vec3 spec_col = mix(vec3(1.0), base, met * 0.85);
    col += spec_col * pow(spec_t, expo) * specular * mix(1.0, 0.55, rough) * k;

    return vec4(col, tint.a * aa);
}
""",
    deps=("smooth01", "rounded_rect_sdf"),
)

LIBRARY.register(
    "particles_path",
    """
vec4 particles_path(vec2 frag, vec2 p_min, vec2 p_max, float rounding, float progress,
                    float trail, float inset, float count_f, float radius,
                    float intensity, vec4 tint) {
    vec4 acc = vec4(0.0);
    int count = min(int(count_f + 0.5), MAX_PARTICLES);
    vec2 pmn = p_min + vec2(inset);
    vec2 pmx = p_max - vec2(inset);
    float r = max(rounding - inset, 0.0);
    for (int i = 0; i < MAX_PARTICLES; ++i) {
        if (i >= count) break;
        float pt = count > 1 ? float(i) / float(count - 1) : 0.0;
        float fade = 1.0 - smooth01(0.0, 1.0, pt);
        float pr = max(radius * (0.45 + 0.55 * fade), 0.1);
        vec2 c = rect_point_at(pmn, pmx, r, progress - pt * trail);
        float a = intensity * fade * fade * max(0.0, 1.0 - distance(frag, c) / pr) * tint.a;
        acc.rgb += (1.0 - acc.a) * a * tint.rgb;
        acc.a += (1.0 - acc.a) * a;
    }
    return vec4(acc.a > 0.0001 ? acc.rgb / acc.a : vec3(0.0), acc.a);
}
""",
    deps=("smooth01", "rect_point_at"),
)

LIBRARY.register(
    "particles_burst",
    """
vec4 particles_burst(vec2 frag, vec2 center, float progress, float count_f,
                     float radius, float spread, float intensity, vec4 tint) {
    vec4 acc = vec4(0.0);
    int count = min(int(count_f + 0.5), MAX_PARTICLES);
    float p = clamp(progress, 0.0, 1.0);
    float flash_alpha = intensity * (1.0 - smooth01(0.0, 0.28, p));
    if (flash_alpha > 0.0) {
        float fr = radius * (4.0 + p * 6.0);
        float a = flash_alpha * 0.52 * max(0.0, 1.0 - distance(frag, center) / fr) * tint.a;
        acc.rgb += (1.0 - acc.a) * a * vec3(1.0, 0.96, 0.78);
        acc.a += (1.0 - acc.a) * a;
    }
    float sas = intensity * (1.0 - smooth01(0.58, 1.0, p)) * smooth01(0.0, 0.035, p);
    if (sas > 0.0) {
        float bp = 1.0 - (1.0 - p) * (1.0 - p);
        float len_env = 1.0 - smooth01(0.68, 1.0, p);
        float hw_env = 1.0 - smooth01(0.72, 1.0, p);
        float gravity = spread * 0.16 * p * p;
        for (int i = 0; i < MAX_PARTICLES; ++i) {
            if (i >= count) break;
            float pt = count > 1 ? float(i) / float(count - 1) : 0.0;
            float angle = float(i) * GOLDEN_ANGLE;
            float variance = fract(sin(float(i) * 12.9898) * 43758.5453);
            float speed = 0.55 + variance * 0.55;
            vec2 dir = vec2(cos(angle), sin(angle));
            vec2 head = center + dir * (spread * bp * speed) + vec2(0.0, gravity);
            float len = radius * (4.5 + 5.5 * speed) * len_env;
            float hw = radius * (0.45 + 0.55 * (1.0 - pt)) * hw_env;
            if (len <= 0.1 || hw <= 0.1) continue;
            vec2 rel = frag - head;
            float at = -dot(rel, dir) / len;
            if (at < 0.0 || at > 1.0) continue;
            float env = at < 0.38 ? at / 0.38 : (1.0 - at) / 0.62;
            float wlim = max(hw * env, 0.001);
            float across = dot(rel, vec2(-dir.y, dir.x));
            float ca = max(0.0, 1.0 - abs(across) / wlim);
            float la = sas * (0.55 + 0.45 * (1.0 - pt));
            vec3 rgb = mix(vec3(1.0, 0.94, 0.62), tint.rgb, smooth01(0.0, 0.3, at));
            float a = la * (1.0 - at) * ca * tint.a;
            acc.rgb += (1.0 - acc.a) * a * rgb;
            acc.a += (1.0 - acc.a) * a;
        }
    }
    return vec4(acc.a > 0.0001 ? acc.rgb / acc.a : vec3(0.0), acc.a);
}
""",
    deps=("smooth01",),
)

LIBRARY.register(
    "particles_trail",
    """
vec4 particles_trail(vec2 frag, vec2 start, vec2 end, float progress, float count_f,
                     float radius, float spacing, float intensity, vec4 tint) {
    vec4 acc = vec4(0.0);
    int count = min(int(count_f + 0.5), MAX_PARTICLES);
    vec2 delta = end - start;
    float plen = length(delta);
    if (plen > 0.001) {
        vec2 dir = delta / plen;
        float head = progress * plen;
        float efw = max(radius * 2.0, 1.0);
        for (int i = 0; i < MAX_PARTICLES; ++i) {
            if (i >= count) break;
            float dd = head - spacing * float(i);
            if (dd < 0.0 || dd > plen) continue;
            float t = count > 1 ? float(i) / float(count - 1) : 0.0;
            float fade = 1.0 - smooth01(0.0, 1.0, t);
            float ef = smooth01(0.0, efw, dd) * (1.0 - smooth01(plen - efw, plen, dd));
            float dr = max(radius * (0.35 + 0.65 * fade), 0.1);
            vec2 c = start + dir * dd;
            float a = intensity * fade * fade * ef * max(0.0, 1.0 - distance(frag, c) / dr) * tint.a;
            acc.rgb += (1.0 - acc.a) * a * tint.rgb;
            acc.a += (1.0 - acc.a) * a;
        }
    }
    return vec4(acc.a > 0.0001 ? acc.rgb / acc.a : vec3(0.0), acc.a);
}
""",
    deps=("smooth01",),
)

# -- noise ------------------------------------------------------------------------

LIBRARY.register(
    "hash21",
    """
float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}
""",
)

# Smoothly interpolated 2D value noise, output in [0, 1].
LIBRARY.register(
    "value_noise",
    """
float value_noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = hash21(i);
    float b = hash21(i + vec2(1.0, 0.0));
    float c = hash21(i + vec2(0.0, 1.0));
    float d = hash21(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
""",
    deps=("hash21",),
)

# 2D simplex noise (Ashima Arts / Ian McEwan, public domain), output ~[-1, 1].
LIBRARY.register(
    "simplex_noise",
    """
vec3 simplex_permute(vec3 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }

float simplex_noise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                        -0.577350269189626, 0.024390243902439);
    vec2 i = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod(i, 289.0);
    vec3 p = simplex_permute(simplex_permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
    m = m * m;
    m = m * m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
    vec3 g;
    g.x = a0.x * x0.x + h.x * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}
""",
)

# Fractal Brownian motion over value noise. `octaves` is a compile-time
# constant (1..8); output in [0, 1) (amplitude sum 1 - 0.5^octaves).
LIBRARY.register(
    "fbm",
    """
float fbm(vec2 p, int octaves) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 8; ++i) {
        if (i >= octaves) break;
        value += amplitude * value_noise(p);
        p = p * 2.03 + vec2(17.13, 9.57);
        amplitude *= 0.5;
    }
    return value;
}
""",
    deps=("value_noise",),
)
