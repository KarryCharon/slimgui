#include <array>
#include <optional>
#include <string>

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string.h>

#include "imgui.h"
#include "imgui_internal.h"
#include "type_casts.h" // IWYU pragma: keep
#include "im_anim.h"

namespace nb = nanobind;
using namespace nb::literals;

namespace {

void bind_constants(nb::module_& m) {
    m.attr("IMANIM_VERSION") = IMANIM_VERSION;
    m.attr("IMANIM_VERSION_NUM") = IMANIM_VERSION_NUM;

    m.attr("EASE_LINEAR") = (int)iam_ease_linear;
    m.attr("EASE_IN_QUAD") = (int)iam_ease_in_quad;
    m.attr("EASE_OUT_QUAD") = (int)iam_ease_out_quad;
    m.attr("EASE_IN_OUT_QUAD") = (int)iam_ease_in_out_quad;
    m.attr("EASE_IN_CUBIC") = (int)iam_ease_in_cubic;
    m.attr("EASE_OUT_CUBIC") = (int)iam_ease_out_cubic;
    m.attr("EASE_IN_OUT_CUBIC") = (int)iam_ease_in_out_cubic;
    m.attr("EASE_IN_QUART") = (int)iam_ease_in_quart;
    m.attr("EASE_OUT_QUART") = (int)iam_ease_out_quart;
    m.attr("EASE_IN_OUT_QUART") = (int)iam_ease_in_out_quart;
    m.attr("EASE_IN_QUINT") = (int)iam_ease_in_quint;
    m.attr("EASE_OUT_QUINT") = (int)iam_ease_out_quint;
    m.attr("EASE_IN_OUT_QUINT") = (int)iam_ease_in_out_quint;
    m.attr("EASE_IN_SINE") = (int)iam_ease_in_sine;
    m.attr("EASE_OUT_SINE") = (int)iam_ease_out_sine;
    m.attr("EASE_IN_OUT_SINE") = (int)iam_ease_in_out_sine;
    m.attr("EASE_IN_EXPO") = (int)iam_ease_in_expo;
    m.attr("EASE_OUT_EXPO") = (int)iam_ease_out_expo;
    m.attr("EASE_IN_OUT_EXPO") = (int)iam_ease_in_out_expo;
    m.attr("EASE_IN_CIRC") = (int)iam_ease_in_circ;
    m.attr("EASE_OUT_CIRC") = (int)iam_ease_out_circ;
    m.attr("EASE_IN_OUT_CIRC") = (int)iam_ease_in_out_circ;
    m.attr("EASE_IN_BACK") = (int)iam_ease_in_back;
    m.attr("EASE_OUT_BACK") = (int)iam_ease_out_back;
    m.attr("EASE_IN_OUT_BACK") = (int)iam_ease_in_out_back;
    m.attr("EASE_IN_ELASTIC") = (int)iam_ease_in_elastic;
    m.attr("EASE_OUT_ELASTIC") = (int)iam_ease_out_elastic;
    m.attr("EASE_IN_OUT_ELASTIC") = (int)iam_ease_in_out_elastic;
    m.attr("EASE_IN_BOUNCE") = (int)iam_ease_in_bounce;
    m.attr("EASE_OUT_BOUNCE") = (int)iam_ease_out_bounce;
    m.attr("EASE_IN_OUT_BOUNCE") = (int)iam_ease_in_out_bounce;
    m.attr("EASE_STEPS") = (int)iam_ease_steps;
    m.attr("EASE_CUBIC_BEZIER") = (int)iam_ease_cubic_bezier;
    m.attr("EASE_SPRING") = (int)iam_ease_spring;

    m.attr("POLICY_CROSSFADE") = (int)iam_policy_crossfade;
    m.attr("POLICY_CUT") = (int)iam_policy_cut;
    m.attr("POLICY_QUEUE") = (int)iam_policy_queue;

    m.attr("COLOR_SRGB") = (int)iam_col_srgb;
    m.attr("COLOR_SRGB_LINEAR") = (int)iam_col_srgb_linear;
    m.attr("COLOR_HSV") = (int)iam_col_hsv;
    m.attr("COLOR_OKLAB") = (int)iam_col_oklab;
    m.attr("COLOR_OKLCH") = (int)iam_col_oklch;

    m.attr("ANCHOR_WINDOW_CONTENT") = (int)iam_anchor_window_content;
    m.attr("ANCHOR_WINDOW") = (int)iam_anchor_window;
    m.attr("ANCHOR_VIEWPORT") = (int)iam_anchor_viewport;
    m.attr("ANCHOR_LAST_ITEM") = (int)iam_anchor_last_item;

    m.attr("WAVE_SINE") = (int)iam_wave_sine;
    m.attr("WAVE_TRIANGLE") = (int)iam_wave_triangle;
    m.attr("WAVE_SAWTOOTH") = (int)iam_wave_sawtooth;
    m.attr("WAVE_SQUARE") = (int)iam_wave_square;

    m.attr("ROTATION_SHORTEST") = (int)iam_rotation_shortest;
    m.attr("ROTATION_LONGEST") = (int)iam_rotation_longest;
    m.attr("ROTATION_CW") = (int)iam_rotation_cw;
    m.attr("ROTATION_CCW") = (int)iam_rotation_ccw;
    m.attr("ROTATION_DIRECT") = (int)iam_rotation_direct;

    m.attr("DIRECTION_NORMAL") = (int)iam_dir_normal;
    m.attr("DIRECTION_REVERSE") = (int)iam_dir_reverse;
    m.attr("DIRECTION_ALTERNATE") = (int)iam_dir_alternate;
}

std::optional<float> instance_get_float(const iam_instance& self, ImGuiID channel) {
    float value = 0.0f;
    if (!self.get_float(channel, &value))
        return std::nullopt;
    return value;
}

std::optional<ImVec2> instance_get_vec2(const iam_instance& self, ImGuiID channel) {
    ImVec2 value;
    if (!self.get_vec2(channel, &value))
        return std::nullopt;
    return value;
}

std::optional<ImVec4> instance_get_vec4(const iam_instance& self, ImGuiID channel) {
    ImVec4 value;
    if (!self.get_vec4(channel, &value))
        return std::nullopt;
    return value;
}

std::optional<int> instance_get_int(const iam_instance& self, ImGuiID channel) {
    int value = 0;
    if (!self.get_int(channel, &value))
        return std::nullopt;
    return value;
}

std::optional<ImVec4> instance_get_color(const iam_instance& self, ImGuiID channel, int color_space) {
    ImVec4 value;
    if (!self.get_color(channel, &value, color_space))
        return std::nullopt;
    return value;
}

std::optional<float> get_blended_float(ImGuiID instance_id, ImGuiID channel) {
    float value = 0.0f;
    if (!iam_get_blended_float(instance_id, channel, &value))
        return std::nullopt;
    return value;
}

std::optional<ImVec2> get_blended_vec2(ImGuiID instance_id, ImGuiID channel) {
    ImVec2 value;
    if (!iam_get_blended_vec2(instance_id, channel, &value))
        return std::nullopt;
    return value;
}

std::optional<ImVec4> get_blended_vec4(ImGuiID instance_id, ImGuiID channel) {
    ImVec4 value;
    if (!iam_get_blended_vec4(instance_id, channel, &value))
        return std::nullopt;
    return value;
}

std::optional<int> get_blended_int(ImGuiID instance_id, ImGuiID channel) {
    int value = 0;
    if (!iam_get_blended_int(instance_id, channel, &value))
        return std::nullopt;
    return value;
}

} // namespace

void register_anim_bindings(nb::module_& top) {
    nb::module_ m = top.def_submodule("anim", "ImAnim animation bindings");

    bind_constants(m);

    nb::class_<iam_ease_desc>(m, "EaseDesc")
        .def(nb::init<>())
        .def_rw("type", &iam_ease_desc::type)
        .def_rw("p0", &iam_ease_desc::p0)
        .def_rw("p1", &iam_ease_desc::p1)
        .def_rw("p2", &iam_ease_desc::p2)
        .def_rw("p3", &iam_ease_desc::p3);

    nb::class_<iam_ease_per_axis>(m, "EasePerAxis")
        .def(nb::init<>())
        .def(nb::init<iam_ease_desc>())
        .def(nb::init<iam_ease_desc, iam_ease_desc>())
        .def(nb::init<iam_ease_desc, iam_ease_desc, iam_ease_desc, iam_ease_desc>())
        .def_rw("x", &iam_ease_per_axis::x)
        .def_rw("y", &iam_ease_per_axis::y)
        .def_rw("z", &iam_ease_per_axis::z)
        .def_rw("w", &iam_ease_per_axis::w);

    nb::class_<iam_spring_params>(m, "SpringParams")
        .def(nb::init<>())
        .def_rw("mass", &iam_spring_params::mass)
        .def_rw("stiffness", &iam_spring_params::stiffness)
        .def_rw("damping", &iam_spring_params::damping)
        .def_rw("initial_velocity", &iam_spring_params::initial_velocity);

    nb::class_<iam_morph_opts>(m, "MorphOptions")
        .def(nb::init<>())
        .def_rw("samples", &iam_morph_opts::samples)
        .def_rw("match_endpoints", &iam_morph_opts::match_endpoints)
        .def_rw("use_arc_length", &iam_morph_opts::use_arc_length);

    nb::class_<iam_gradient>(m, "Gradient")
        .def(nb::init<>())
        .def("add", [](iam_gradient& self, float position, ImVec4 color) -> iam_gradient& {
            return self.add(position, color);
        }, "position"_a, "color"_a, nb::rv_policy::reference_internal)
        .def("sample", &iam_gradient::sample, "t"_a, "color_space"_a = (int)iam_col_oklab)
        .def_prop_ro("stop_count", &iam_gradient::stop_count)
        .def_static("solid", &iam_gradient::solid, "color"_a)
        .def_static("two_color", &iam_gradient::two_color, "start"_a, "end"_a)
        .def_static("three_color", &iam_gradient::three_color, "start"_a, "mid"_a, "end"_a);

    nb::class_<iam_transform>(m, "Transform")
        .def(nb::init<>())
        .def(nb::init<ImVec2, float, ImVec2>(), "position"_a, "rotation"_a = 0.0f, "scale"_a = ImVec2(1.0f, 1.0f))
        .def_rw("position", &iam_transform::position)
        .def_rw("scale", &iam_transform::scale)
        .def_rw("rotation", &iam_transform::rotation)
        .def_static("identity", &iam_transform::identity)
        .def("combine", [](const iam_transform& self, const iam_transform& other) {
            return self * other;
        }, "other"_a)
        .def("apply", &iam_transform::apply, "point"_a)
        .def("inverse", &iam_transform::inverse);

    nb::class_<iam_path>(m, "Path")
        .def_static("begin", &iam_path::begin, "path_id"_a, "start"_a)
        .def("line_to", &iam_path::line_to, "end"_a, nb::rv_policy::reference_internal)
        .def("quadratic_to", &iam_path::quadratic_to, "ctrl"_a, "end"_a, nb::rv_policy::reference_internal)
        .def("cubic_to", &iam_path::cubic_to, "ctrl1"_a, "ctrl2"_a, "end"_a, nb::rv_policy::reference_internal)
        .def("catmull_to", &iam_path::catmull_to, "end"_a, "tension"_a = 0.5f, nb::rv_policy::reference_internal)
        .def("close", &iam_path::close, nb::rv_policy::reference_internal)
        .def("end", &iam_path::end)
        .def_prop_ro("id", &iam_path::id);

    nb::class_<iam_clip>(m, "Clip")
        .def_static("begin", &iam_clip::begin, "clip_id"_a)
        .def("key_float", [](iam_clip& self, ImGuiID channel, float time, float value, int ease_type) -> iam_clip& {
            return self.key_float(channel, time, value, ease_type);
        }, "channel"_a, "time"_a, "value"_a, "ease_type"_a = (int)iam_ease_linear, nb::rv_policy::reference_internal)
        .def("key_vec2", [](iam_clip& self, ImGuiID channel, float time, ImVec2 value, int ease_type) -> iam_clip& {
            return self.key_vec2(channel, time, value, ease_type);
        }, "channel"_a, "time"_a, "value"_a, "ease_type"_a = (int)iam_ease_linear, nb::rv_policy::reference_internal)
        .def("key_vec4", [](iam_clip& self, ImGuiID channel, float time, ImVec4 value, int ease_type) -> iam_clip& {
            return self.key_vec4(channel, time, value, ease_type);
        }, "channel"_a, "time"_a, "value"_a, "ease_type"_a = (int)iam_ease_linear, nb::rv_policy::reference_internal)
        .def("key_int", &iam_clip::key_int, "channel"_a, "time"_a, "value"_a, "ease_type"_a = (int)iam_ease_linear, nb::rv_policy::reference_internal)
        .def("key_color", [](iam_clip& self, ImGuiID channel, float time, ImVec4 value, int color_space, int ease_type) -> iam_clip& {
            return self.key_color(channel, time, value, color_space, ease_type);
        }, "channel"_a, "time"_a, "value"_a, "color_space"_a = (int)iam_col_oklab, "ease_type"_a = (int)iam_ease_linear, nb::rv_policy::reference_internal)
        .def("key_float_spring", &iam_clip::key_float_spring, "channel"_a, "time"_a, "target"_a, "spring"_a, nb::rv_policy::reference_internal)
        .def("seq_begin", &iam_clip::seq_begin, nb::rv_policy::reference_internal)
        .def("seq_end", &iam_clip::seq_end, nb::rv_policy::reference_internal)
        .def("par_begin", &iam_clip::par_begin, nb::rv_policy::reference_internal)
        .def("par_end", &iam_clip::par_end, nb::rv_policy::reference_internal)
        .def("set_loop", &iam_clip::set_loop, "loop"_a, "direction"_a = (int)iam_dir_normal, "loop_count"_a = -1, nb::rv_policy::reference_internal)
        .def("set_delay", &iam_clip::set_delay, "delay_seconds"_a, nb::rv_policy::reference_internal)
        .def("set_stagger", &iam_clip::set_stagger, "count"_a, "each_delay"_a, "from_center_bias"_a = 0.0f, nb::rv_policy::reference_internal)
        .def("end", &iam_clip::end)
        .def_prop_ro("id", &iam_clip::id);

    nb::class_<iam_instance>(m, "Instance")
        .def(nb::init<>())
        .def(nb::init<ImGuiID>(), "instance_id"_a)
        .def("pause", &iam_instance::pause)
        .def("resume", &iam_instance::resume)
        .def("stop", &iam_instance::stop)
        .def("destroy", &iam_instance::destroy)
        .def("seek", &iam_instance::seek, "time"_a)
        .def("set_time_scale", &iam_instance::set_time_scale, "scale"_a)
        .def("set_weight", &iam_instance::set_weight, "weight"_a)
        .def("then", nb::overload_cast<ImGuiID>(&iam_instance::then), "next_clip_id"_a, nb::rv_policy::reference_internal)
        .def("then", nb::overload_cast<ImGuiID, ImGuiID>(&iam_instance::then), "next_clip_id"_a, "next_instance_id"_a, nb::rv_policy::reference_internal)
        .def("then_delay", &iam_instance::then_delay, "delay"_a, nb::rv_policy::reference_internal)
        .def_prop_ro("time", &iam_instance::time)
        .def_prop_ro("duration", &iam_instance::duration)
        .def_prop_ro("is_playing", &iam_instance::is_playing)
        .def_prop_ro("is_paused", &iam_instance::is_paused)
        .def_prop_ro("valid", &iam_instance::valid)
        .def_prop_ro("id", &iam_instance::id)
        .def("get_float", &instance_get_float, "channel"_a)
        .def("get_vec2", &instance_get_vec2, "channel"_a)
        .def("get_vec4", &instance_get_vec4, "channel"_a)
        .def("get_int", &instance_get_int, "channel"_a)
        .def("get_color", &instance_get_color, "channel"_a, "color_space"_a = (int)iam_col_oklab);

    m.def("hash_str", [](const std::string& value, ImGuiID seed) {
        return ImHashStr(value.c_str(), value.size(), seed);
    }, "value"_a, "seed"_a = 0, "Return the same hash primitive used by ImGui/ImAnim IDs.");

    m.def("update_begin_frame", &iam_update_begin_frame);
    m.def("gc", &iam_gc, "max_age_frames"_a = 600);
    m.def("pool_clear", &iam_pool_clear);
    m.def("reserve", &iam_reserve, "cap_float"_a, "cap_vec2"_a, "cap_vec4"_a, "cap_int"_a, "cap_color"_a);
    m.def("set_ease_lut_samples", &iam_set_ease_lut_samples, "count"_a);
    m.def("set_global_time_scale", &iam_set_global_time_scale, "scale"_a);
    m.def("get_global_time_scale", &iam_get_global_time_scale);
    m.def("set_lazy_init", &iam_set_lazy_init, "enable"_a);
    m.def("is_lazy_init_enabled", &iam_is_lazy_init_enabled);

    m.def("eval_preset", &iam_eval_preset, "type"_a, "t"_a);
    m.def("ease_preset", &iam_ease_preset, "type"_a);
    m.def("ease_bezier", &iam_ease_bezier, "x1"_a, "y1"_a, "x2"_a, "y2"_a);
    m.def("ease_steps", &iam_ease_steps_desc, "steps"_a, "mode"_a);
    m.def("ease_back", &iam_ease_back, "overshoot"_a);
    m.def("ease_elastic", &iam_ease_elastic, "amplitude"_a, "period"_a);
    m.def("ease_spring", &iam_ease_spring_desc, "mass"_a, "stiffness"_a, "damping"_a, "initial_velocity"_a);

    m.def("bezier_quadratic", &iam_bezier_quadratic, "p0"_a, "p1"_a, "p2"_a, "t"_a);
    m.def("bezier_cubic", &iam_bezier_cubic, "p0"_a, "p1"_a, "p2"_a, "p3"_a, "t"_a);
    m.def("catmull_rom", &iam_catmull_rom, "p0"_a, "p1"_a, "p2"_a, "p3"_a, "t"_a, "tension"_a = 0.5f);
    m.def("bezier_quadratic_deriv", &iam_bezier_quadratic_deriv, "p0"_a, "p1"_a, "p2"_a, "t"_a);
    m.def("bezier_cubic_deriv", &iam_bezier_cubic_deriv, "p0"_a, "p1"_a, "p2"_a, "p3"_a, "t"_a);
    m.def("catmull_rom_deriv", &iam_catmull_rom_deriv, "p0"_a, "p1"_a, "p2"_a, "p3"_a, "t"_a, "tension"_a = 0.5f);

    m.def("get_blended_color", &iam_get_blended_color, "a_srgb"_a, "b_srgb"_a, "t"_a, "color_space"_a = (int)iam_col_oklab);

    m.def("tween_float", &iam_tween_float, "id"_a, "channel_id"_a, "target"_a, "duration"_a,
          "ease"_a, "policy"_a, "dt"_a, "init_value"_a = 0.0f);
    m.def("tween_vec2", &iam_tween_vec2, "id"_a, "channel_id"_a, "target"_a, "duration"_a,
          "ease"_a, "policy"_a, "dt"_a, "init_value"_a = ImVec2(0, 0));
    m.def("tween_vec4", &iam_tween_vec4, "id"_a, "channel_id"_a, "target"_a, "duration"_a,
          "ease"_a, "policy"_a, "dt"_a, "init_value"_a = ImVec4(0, 0, 0, 0));
    m.def("tween_int", &iam_tween_int, "id"_a, "channel_id"_a, "target"_a, "duration"_a,
          "ease"_a, "policy"_a, "dt"_a, "init_value"_a = 0);
    m.def("tween_color", &iam_tween_color, "id"_a, "channel_id"_a, "target_srgb"_a, "duration"_a,
          "ease"_a, "policy"_a, "color_space"_a, "dt"_a, "init_value"_a = ImVec4(1, 1, 1, 1));

    m.def("tween_vec2_per_axis", &iam_tween_vec2_per_axis, "id"_a, "channel_id"_a, "target"_a,
          "duration"_a, "ease"_a, "policy"_a, "dt"_a);
    m.def("tween_vec4_per_axis", &iam_tween_vec4_per_axis, "id"_a, "channel_id"_a, "target"_a,
          "duration"_a, "ease"_a, "policy"_a, "dt"_a);
    m.def("tween_color_per_axis", &iam_tween_color_per_axis, "id"_a, "channel_id"_a, "target_srgb"_a,
          "duration"_a, "ease"_a, "policy"_a, "color_space"_a, "dt"_a);

    m.def("tween_float_rel", &iam_tween_float_rel, "id"_a, "channel_id"_a, "percent"_a, "px_bias"_a,
          "duration"_a, "ease"_a, "policy"_a, "anchor_space"_a, "axis"_a, "dt"_a);
    m.def("tween_vec2_rel", &iam_tween_vec2_rel, "id"_a, "channel_id"_a, "percent"_a, "px_bias"_a,
          "duration"_a, "ease"_a, "policy"_a, "anchor_space"_a, "dt"_a);
    m.def("tween_vec4_rel", &iam_tween_vec4_rel, "id"_a, "channel_id"_a, "percent"_a, "px_bias"_a,
          "duration"_a, "ease"_a, "policy"_a, "anchor_space"_a, "dt"_a);
    m.def("tween_color_rel", &iam_tween_color_rel, "id"_a, "channel_id"_a, "percent"_a, "px_bias"_a,
          "duration"_a, "ease"_a, "policy"_a, "color_space"_a, "anchor_space"_a, "dt"_a);

    m.def("anchor_size", &iam_anchor_size, "space"_a);
    m.def("rebase_float", &iam_rebase_float, "id"_a, "channel_id"_a, "new_target"_a, "dt"_a);
    m.def("rebase_vec2", &iam_rebase_vec2, "id"_a, "channel_id"_a, "new_target"_a, "dt"_a);
    m.def("rebase_vec4", &iam_rebase_vec4, "id"_a, "channel_id"_a, "new_target"_a, "dt"_a);
    m.def("rebase_color", &iam_rebase_color, "id"_a, "channel_id"_a, "new_target"_a, "dt"_a);
    m.def("rebase_int", &iam_rebase_int, "id"_a, "channel_id"_a, "new_target"_a, "dt"_a);

    m.def("oscillate", &iam_oscillate, "id"_a, "amplitude"_a, "frequency"_a, "wave_type"_a, "phase"_a, "dt"_a);
    m.def("oscillate_int", &iam_oscillate_int, "id"_a, "amplitude"_a, "frequency"_a, "wave_type"_a, "phase"_a, "dt"_a);
    m.def("oscillate_vec2", &iam_oscillate_vec2, "id"_a, "amplitude"_a, "frequency"_a, "wave_type"_a, "phase"_a, "dt"_a);
    m.def("oscillate_vec4", &iam_oscillate_vec4, "id"_a, "amplitude"_a, "frequency"_a, "wave_type"_a, "phase"_a, "dt"_a);
    m.def("oscillate_color", &iam_oscillate_color, "id"_a, "base_color"_a, "amplitude"_a, "frequency"_a, "wave_type"_a, "phase"_a, "color_space"_a, "dt"_a);
    m.def("shake", &iam_shake, "id"_a, "intensity"_a, "frequency"_a, "decay_time"_a, "dt"_a);
    m.def("shake_vec2", &iam_shake_vec2, "id"_a, "intensity"_a, "frequency"_a, "decay_time"_a, "dt"_a);
    m.def("shake_vec4", &iam_shake_vec4, "id"_a, "intensity"_a, "frequency"_a, "decay_time"_a, "dt"_a);
    m.def("wiggle", &iam_wiggle, "id"_a, "amplitude"_a, "frequency"_a, "dt"_a);
    m.def("wiggle_vec2", &iam_wiggle_vec2, "id"_a, "amplitude"_a, "frequency"_a, "dt"_a);
    m.def("wiggle_vec4", &iam_wiggle_vec4, "id"_a, "amplitude"_a, "frequency"_a, "dt"_a);
    m.def("trigger_shake", &iam_trigger_shake, "id"_a);

    m.def("path_exists", &iam_path_exists, "path_id"_a);
    m.def("path_length", &iam_path_length, "path_id"_a);
    m.def("path_evaluate", &iam_path_evaluate, "path_id"_a, "t"_a);
    m.def("path_tangent", &iam_path_tangent, "path_id"_a, "t"_a);
    m.def("path_angle", &iam_path_angle, "path_id"_a, "t"_a);
    m.def("path_build_arc_lut", &iam_path_build_arc_lut, "path_id"_a, "subdivisions"_a = 64);
    m.def("path_has_arc_lut", &iam_path_has_arc_lut, "path_id"_a);
    m.def("path_distance_to_t", &iam_path_distance_to_t, "path_id"_a, "distance"_a);
    m.def("path_evaluate_at_distance", &iam_path_evaluate_at_distance, "path_id"_a, "distance"_a);
    m.def("path_angle_at_distance", &iam_path_angle_at_distance, "path_id"_a, "distance"_a);
    m.def("path_tangent_at_distance", &iam_path_tangent_at_distance, "path_id"_a, "distance"_a);
    m.def("path_morph", [](ImGuiID path_a, ImGuiID path_b, float t, float blend, const iam_morph_opts& opts) {
        return iam_path_morph(path_a, path_b, t, blend, opts);
    }, "path_a"_a, "path_b"_a, "t"_a, "blend"_a, "opts"_a = iam_morph_opts());
    m.def("path_morph_tangent", [](ImGuiID path_a, ImGuiID path_b, float t, float blend, const iam_morph_opts& opts) {
        return iam_path_morph_tangent(path_a, path_b, t, blend, opts);
    }, "path_a"_a, "path_b"_a, "t"_a, "blend"_a, "opts"_a = iam_morph_opts());
    m.def("path_morph_angle", [](ImGuiID path_a, ImGuiID path_b, float t, float blend, const iam_morph_opts& opts) {
        return iam_path_morph_angle(path_a, path_b, t, blend, opts);
    }, "path_a"_a, "path_b"_a, "t"_a, "blend"_a, "opts"_a = iam_morph_opts());
    m.def("tween_path", &iam_tween_path, "id"_a, "channel_id"_a, "path_id"_a, "duration"_a, "ease"_a, "policy"_a, "dt"_a);
    m.def("tween_path_angle", &iam_tween_path_angle, "id"_a, "channel_id"_a, "path_id"_a, "duration"_a, "ease"_a, "policy"_a, "dt"_a);
    m.def("tween_path_morph", [](ImGuiID id, ImGuiID channel_id, ImGuiID path_a, ImGuiID path_b, float target_blend,
                                  float duration, const iam_ease_desc& path_ease, const iam_ease_desc& morph_ease,
                                  int policy, float dt, const iam_morph_opts& opts) {
        return iam_tween_path_morph(id, channel_id, path_a, path_b, target_blend, duration, path_ease, morph_ease, policy, dt, opts);
    }, "id"_a, "channel_id"_a, "path_a"_a, "path_b"_a, "target_blend"_a, "duration"_a,
       "path_ease"_a, "morph_ease"_a, "policy"_a, "dt"_a, "opts"_a = iam_morph_opts());
    m.def("get_morph_blend", &iam_get_morph_blend, "id"_a, "channel_id"_a);

    m.def("gradient_lerp", &iam_gradient_lerp, "a"_a, "b"_a, "t"_a, "color_space"_a = (int)iam_col_oklab);
    m.def("tween_gradient", &iam_tween_gradient, "id"_a, "channel_id"_a, "target"_a, "duration"_a, "ease"_a, "policy"_a, "color_space"_a, "dt"_a);
    m.def("transform_lerp", &iam_transform_lerp, "a"_a, "b"_a, "t"_a, "rotation_mode"_a = (int)iam_rotation_shortest);
    m.def("tween_transform", &iam_tween_transform, "id"_a, "channel_id"_a, "target"_a, "duration"_a, "ease"_a, "policy"_a, "rotation_mode"_a, "dt"_a);
    m.def("transform_from_matrix", &iam_transform_from_matrix, "m00"_a, "m01"_a, "m10"_a, "m11"_a, "tx"_a, "ty"_a);
    m.def("transform_to_matrix", [](const iam_transform& transform) {
        std::array<float, 6> matrix{};
        iam_transform_to_matrix(transform, matrix.data());
        return matrix;
    }, "transform"_a);

    m.def("clip_init", &iam_clip_init, "initial_clip_cap"_a = 256, "initial_inst_cap"_a = 4096);
    m.def("clip_shutdown", &iam_clip_shutdown);
    m.def("clip_update", &iam_clip_update, "dt"_a);
    m.def("clip_gc", &iam_clip_gc, "max_age_frames"_a = 600);
    m.def("play", &iam_play, "clip_id"_a, "instance_id"_a);
    m.def("get_instance", &iam_get_instance, "instance_id"_a);
    m.def("clip_duration", &iam_clip_duration, "clip_id"_a);
    m.def("clip_exists", &iam_clip_exists, "clip_id"_a);
    m.def("stagger_delay", &iam_stagger_delay, "clip_id"_a, "index"_a);
    m.def("play_stagger", &iam_play_stagger, "clip_id"_a, "instance_id"_a, "index"_a);
    m.def("layer_begin", &iam_layer_begin, "instance_id"_a);
    m.def("layer_add", &iam_layer_add, "instance"_a, "weight"_a);
    m.def("layer_end", &iam_layer_end, "instance_id"_a);
    m.def("get_blended_float", &get_blended_float, "instance_id"_a, "channel"_a);
    m.def("get_blended_vec2", &get_blended_vec2, "instance_id"_a, "channel"_a);
    m.def("get_blended_vec4", &get_blended_vec4, "instance_id"_a, "channel"_a);
    m.def("get_blended_int", &get_blended_int, "instance_id"_a, "channel"_a);
}
