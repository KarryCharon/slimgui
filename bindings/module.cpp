// slimgui_ext 模块入口：常量与各域注册。
#include "imgui_common.h"

void register_anim_bindings(nb::module_& top);
void register_imgui_types(nb::module_& m);
void register_imgui_functions(nb::module_& m);

// imconfig.h 的 IM_ASSERT 挂钩（imgui 各编译单元 extern 引用，须唯一定义）
void slimgui_assert(const char* file, int line, const char* expr)
{
    static char expr_buf[1024];
    snprintf(expr_buf, sizeof(expr_buf), "%s:%d: Assertion failed: %s", shortenPath(file, 4), line, expr);
    throw std::runtime_error(expr_buf);
}

NB_MODULE(slimgui_ext, top) {
    nb::module_ m = top.def_submodule("imgui", "Dear ImGui bindings");
    register_anim_bindings(top);

    m.attr("IMGUI_VERSION") = IMGUI_VERSION;
    m.attr("IMGUI_VERSION_NUM") = IMGUI_VERSION_NUM;
    m.attr("VERTEX_SIZE") = sizeof(ImDrawVert);
    m.attr("INDEX_SIZE") = sizeof(ImDrawIdx);
    m.attr("VERTEX_BUFFER_POS_OFFSET") = offsetof(ImDrawVert, pos);
    m.attr("VERTEX_BUFFER_UV_OFFSET") = offsetof(ImDrawVert, uv);
    m.attr("VERTEX_BUFFER_COL_OFFSET") = offsetof(ImDrawVert, col);

    m.attr("DRAW_CALLBACK_RESET_RENDER_STATE") = (intptr_t)ImDrawCallback_ResetRenderState;

    m.attr("FLT_MIN") = FLT_MIN;
    m.attr("FLT_MAX") = FLT_MAX;
    m.attr("FLOAT_MIN") = FLT_MIN;  // for compatibility with older versions
    m.attr("FLOAT_MAX") = FLT_MAX;  // for compatibility with older versions

    m.attr("COL32_WHITE") = IM_COL32_WHITE;
    m.attr("COL32_BLACK") = IM_COL32_BLACK;
    m.attr("COL32_BLACK_TRANS") = IM_COL32_BLACK_TRANS;

    m.attr("PAYLOAD_TYPE_COLOR_3F") = IMGUI_PAYLOAD_TYPE_COLOR_3F;
    m.attr("PAYLOAD_TYPE_COLOR_4F") = IMGUI_PAYLOAD_TYPE_COLOR_4F;

    register_imgui_types(m);
    register_imgui_functions(m);

    // Disable Nanobind leak warnings by default.
    nb::set_leak_warnings(false);
    m.def("set_nanobind_leak_warnings", &nb::set_leak_warnings, "enable"_a);
}
