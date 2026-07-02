// 共享的绑定 helper：结构体、回调包装器与小工具。
// 函数用 inline（外部链接）保证跨编译单元地址唯一——
// decode_drawlist_py_callback 依赖 &drawlist_callback_py_wrapper 的地址比较。
#pragma once

#include <nanobind/nanobind.h>
#include <nanobind/make_iterator.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/variant.h>
#include <iterator>
#include <vector>
#include <array>
#include <unordered_map>

#include "imgui.h"
#include "imgui_internal.h"

namespace nb = nanobind;
using namespace nb::literals;

#include "type_casts.h"

using DrawListCallbackCallable = nb::typed<nb::callable, void(ImDrawList*, ImDrawCmd*, nb::object)>;

template<typename T, typename... Args>
auto tuple_to_array(const std::tuple<Args...>& tpl) {
    return std::apply([](auto&&... args) { return std::array<T, sizeof...(Args)>{args...}; }, tpl);
}

template<typename Array, std::size_t... I>
auto array_to_tuple_impl(const Array& arr, std::index_sequence<I...>) {
    return std::make_tuple(arr[I]...);
}

template<typename T, std::size_t N>
auto array_to_tuple(const std::array<T, N>& arr) {
    return array_to_tuple_impl(arr, std::make_index_sequence<N>{});
}

struct InputTextCallback_UserData
{
    std::string*            Str;
    nb::callable*           ChainCallback;  // Python callable or nullptr
};

// Function to find the Nth occurrence of '/' or '\' from the end of the string
// Returns the original string if none are found.
inline const char* shortenPath(const char* str, int n) {
    int count = 0;
    const char* end = str + strlen(str) - 1;

    // Traverse the string backwards
    while (end >= str) {
        if (*end == '/' || *end == '\\') {
            count++;
            if (count == n) {
                return end + 1;
            }
        }
        end--;
    }
    return str;
}

void slimgui_assert(const char* file, int line, const char* expr);

inline int InputTextCallback(ImGuiInputTextCallbackData* data)
{
    InputTextCallback_UserData* user_data = (InputTextCallback_UserData*)data->UserData;
    if (data->EventFlag == ImGuiInputTextFlags_CallbackResize)
    {
        // Resize string callback (internal, always handled)
        std::string* str = user_data->Str;
        IM_ASSERT(data->Buf == str->c_str());
        str->resize(data->BufTextLen);
        data->Buf = (char*)str->c_str();
    }
    else if (user_data->ChainCallback)
    {
        // Forward to user Python callback
        try {
            auto result = (*user_data->ChainCallback)(data);
            if (!result.is_none()) {
                return nb::cast<int>(result);
            }
        } catch (nb::python_error& e) {
            e.discard_as_unraisable("InputTextCallback python callback");
        } catch (nb::cast_error& e) {
            nb::raise_python_error();
        }
    }
    return 0;
}

struct ContextBackendData {
    nb::object size_constraints_callback = nb::none();
    // PlatformIO hook callable pointers (prevent GC via WrappedContext Python side)
    nb::object platform_get_clipboard_text_fn = nb::none();
    nb::object platform_set_clipboard_text_fn = nb::none();
    nb::object platform_open_in_shell_fn = nb::none();
    nb::object platform_set_ime_data_fn = nb::none();
    // Stored clipboard text returned by get_clipboard callback (must outlive the returned const char*)
    std::string clipboard_text_buf;
    // Selection adapter callable refs (prevent GC, keyed by Selection* pointer)
    std::unordered_map<void*, nb::object> selection_adapter_refs;
};

inline void window_size_constraints_callback_py_wrapper(ImGuiSizeCallbackData* cb_data) {
    ContextBackendData* bd = static_cast<ContextBackendData*>(cb_data->UserData);
    try {
        nb::borrow<nb::callable>(bd->size_constraints_callback)(cb_data);
    } catch (nb::python_error& e) {
        e.discard_as_unraisable("window_size_constraints_callback_py_wrapper callback");
        return;
    } catch (nb::cast_error& e) {
        nb::chain_error(PyExc_RuntimeError, "window_size_constraints_callback_py_wrapper callback cast error");
        nb::raise_python_error();
    }
}
// PlatformIO hook wrappers
inline const char* platform_get_clipboard_text_py_wrapper(ImGuiContext* ctx) {
    ImGuiIO& io = ImGui::GetIO(ctx);
    ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
    try {
        nb::object result = nb::borrow<nb::callable>(bd->platform_get_clipboard_text_fn)(/* no args */);
        bd->clipboard_text_buf = nb::cast<std::string>(result);
        return bd->clipboard_text_buf.c_str();
    } catch (nb::python_error& e) {
        e.discard_as_unraisable("platform_get_clipboard_text_fn callback");
        return "";
    }
}
inline void platform_set_clipboard_text_py_wrapper(ImGuiContext* ctx, const char* text) {
    ImGuiIO& io = ImGui::GetIO(ctx);
    ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
    try {
        nb::borrow<nb::callable>(bd->platform_set_clipboard_text_fn)(text);
    } catch (nb::python_error& e) {
        e.discard_as_unraisable("platform_set_clipboard_text_fn callback");
    }
}
inline bool platform_open_in_shell_py_wrapper(ImGuiContext* ctx, const char* path) {
    ImGuiIO& io = ImGui::GetIO(ctx);
    ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
    try {
        return nb::cast<bool>(nb::borrow<nb::callable>(bd->platform_open_in_shell_fn)(path));
    } catch (nb::python_error& e) {
        e.discard_as_unraisable("platform_open_in_shell_fn callback");
        return false;
    }
}
inline void platform_set_ime_data_py_wrapper(ImGuiContext* ctx, ImGuiViewport* viewport, ImGuiPlatformImeData* data) {
    ImGuiIO& io = ImGui::GetIO(ctx);
    ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
    if (!bd || !bd->platform_set_ime_data_fn.ptr() || bd->platform_set_ime_data_fn.is_none()) {
        ImGui::GetPlatformIO(ctx).Platform_SetImeDataFn = nullptr;
        return;
    }
    try {
        nb::borrow<nb::callable>(bd->platform_set_ime_data_fn)(viewport, data);
    } catch (nb::python_error& e) {
        e.discard_as_unraisable("platform_set_ime_data_fn callback");
    } catch (nb::cast_error& e) {
        nb::chain_error(PyExc_RuntimeError, "platform_set_ime_data_fn callback cast error");
        nb::raise_python_error();
    }
}
inline void drawlist_callback_py_wrapper(const ImDrawList* parent_list, const ImDrawCmd* cmd);

// Decode a Python callback stored by `DrawList.add_callback`.
//
// Stored userdata format (see add_callback):
//
//   int64 [0]: callable PyObject* (borrowed)
//   int64 [1]: userdata PyObject* (borrowed; any Python object, None default)
//
// Both references are kept alive by the Python-side DrawList wrapper until
// the next new_frame().
//
// Returns false if the command doesn't carry a Python callback (regular draw,
// reset-render-state token, or a native callback installed by other code).
inline bool decode_drawlist_py_callback(const ImDrawCmd* cmd, nb::object* out_callable, nb::object* out_userdata) {
    if (cmd->UserCallback != &drawlist_callback_py_wrapper || cmd->UserCallbackData == nullptr ||
        cmd->UserCallbackDataSize < (int)(sizeof(intptr_t) * 2)) {
        return false;
    }
    const intptr_t* data = (const intptr_t*)cmd->UserCallbackData;
    if (out_callable) {
        *out_callable = nb::borrow((PyObject*)data[0]);
    }
    if (out_userdata) {
        *out_userdata = nb::borrow((PyObject*)data[1]);
    }
    return true;
}

inline void drawlist_callback_py_wrapper(const ImDrawList* parent_list, const ImDrawCmd* cmd) {
    nb::object callable, userdata;
    if (!decode_drawlist_py_callback(cmd, &callable, &userdata)) {
        return;
    }
    try {
        nb::borrow<nb::callable>(callable)(parent_list, cmd, userdata);
    } catch (nb::python_error& e) {
        e.discard_as_unraisable("drawlist_callback_py_wrapper callback");
        return;
    } catch (nb::cast_error&) {
        nb::chain_error(PyExc_RuntimeError, "drawlist_callback_py_wrapper callback cast error");
        nb::raise_python_error();
    }
}
// Used as the type for nanobind instead of binding ImGuiContext directly.  Binding
// ImGuiContext directly triggers ocornut/imgui#7676
struct Context {
    ImGuiContext* ctx;
    explicit Context(ImGuiContext* c) : ctx(c) {}
    Context() = delete;

    ImGuiContext* setCurrent() {
        ImGuiContext* prev = ImGui::GetCurrentContext();
        ImGui::SetCurrentContext(this->ctx);
        return prev;
    }
};

enum DrawListCallbackResult
{
    DRAW = 0,
    CALLBACK = 1,
    RESET_RENDER_STATE = 2,
};

inline ImVec4 lerp_color(const ImVec4& a, const ImVec4& b, float t)
{
    return ImVec4(
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t,
        a.w + (b.w - a.w) * t
    );
}

inline ImU32 bilinear_color(ImVec2 p, ImVec2 p_min, ImVec2 p_max, ImVec4 col_ul, ImVec4 col_ur, ImVec4 col_br, ImVec4 col_bl, float alpha_mul)
{
    const float w = ImMax(p_max.x - p_min.x, 1.0f);
    const float h = ImMax(p_max.y - p_min.y, 1.0f);
    const float u = ImClamp((p.x - p_min.x) / w, 0.0f, 1.0f);
    const float v = ImClamp((p.y - p_min.y) / h, 0.0f, 1.0f);
    ImVec4 top = lerp_color(col_ul, col_ur, u);
    ImVec4 bottom = lerp_color(col_bl, col_br, u);
    ImVec4 out = lerp_color(top, bottom, v);
    out.w *= alpha_mul;
    return ImGui::ColorConvertFloat4ToU32(out);
}

inline void AddRectFilledMultiColorRounded(ImDrawList* draw_list, ImVec2 p_min, ImVec2 p_max, ImU32 col_ul, ImU32 col_ur, ImU32 col_br, ImU32 col_bl, float rounding, ImDrawFlags flags)
{
    if (((col_ul | col_ur | col_br | col_bl) & IM_COL32_A_MASK) == 0)
        return;

    if (rounding < 0.5f || (flags & ImDrawFlags_RoundCornersMask_) == ImDrawFlags_RoundCornersNone)
    {
        draw_list->AddRectFilledMultiColor(p_min, p_max, col_ul, col_ur, col_br, col_bl);
        return;
    }

    const int vert_start = draw_list->VtxBuffer.Size;
    draw_list->PathClear();
    draw_list->PathRect(p_min, p_max, rounding, flags);
    draw_list->PathFillConvex(IM_COL32_WHITE);
    const int vert_end = draw_list->VtxBuffer.Size;

    const ImVec4 c_ul = ImGui::ColorConvertU32ToFloat4(col_ul);
    const ImVec4 c_ur = ImGui::ColorConvertU32ToFloat4(col_ur);
    const ImVec4 c_br = ImGui::ColorConvertU32ToFloat4(col_br);
    const ImVec4 c_bl = ImGui::ColorConvertU32ToFloat4(col_bl);

    for (int i = vert_start; i < vert_end; ++i)
    {
        ImDrawVert& v = draw_list->VtxBuffer[i];
        const float aa_alpha = (float)((v.col & IM_COL32_A_MASK) >> IM_COL32_A_SHIFT) / 255.0f;
        v.col = bilinear_color(v.pos, p_min, p_max, c_ul, c_ur, c_br, c_bl, aa_alpha);
    }
}
