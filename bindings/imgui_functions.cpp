// imgui 函数绑定：生成的 .inl + 手写复杂绑定，由 slimgui_ext.cpp 拆分而来。
#include "imgui_common.h"

void register_imgui_functions(nb::module_& m) {
#include "generated/imgui_enums.inl"
#include "generated/imgui_funcs.inl"

    m.def("clear_active_id", []() {
        ImGui::ClearActiveID();
    }, "Clear the active item id (e.g. unfocus InputText so overlapping widgets can capture mouse). Uses Dear ImGui internal API.");

    m.def("temp_input_is_active", [](std::optional<ImGuiID> id) {
        ImGuiID target_id = id.value_or(ImGui::GetItemID());
        return ImGui::TempInputIsActive(target_id);
    }, "id"_a = nb::none(),
    "Return true when an item's temporary scalar/text input is active. If id is None, checks the last submitted item.");

    m.def("is_item_active_as_input_text", []() {
        return ImGui::IsItemActiveAsInputText();
    }, "Return true when the last submitted item is currently active as an InputText field. Uses Dear ImGui internal API.");

    m.def("get_active_id", []() {
        return ImGui::GetActiveID();
    }, "Return the currently active item id, or 0 if none. Uses Dear ImGui internal API.");

    m.def("get_hovered_id", []() {
        return ImGui::GetHoveredID();
    }, "Return the currently hovered item id, or 0 if none. Uses Dear ImGui internal API.");

    m.def("get_focus_id", []() {
        return ImGui::GetFocusID();
    }, "Return the current navigation/focus item id, or 0 if none. Uses Dear ImGui internal API.");

    m.def("get_temp_input_id", []() {
        ImGuiContext& g = *GImGui;
        return g.TempInputId;
    }, "Return the current temporary input id, or 0 if none. Uses Dear ImGui internal state.");

    m.def("get_last_active_id", []() {
        ImGuiContext& g = *GImGui;
        return g.LastActiveId;
    }, "Return the last non-zero active item id. Uses Dear ImGui internal state.");

    m.def("get_last_active_id_timer", []() {
        ImGuiContext& g = *GImGui;
        return g.LastActiveIdTimer;
    }, "Return seconds since the last active item became active. Uses Dear ImGui internal state.");

    m.def("get_item_flags", []() {
        return ImGui::GetItemFlags();
    }, "Return flags for the last submitted item. Uses Dear ImGui internal API.");

    m.def("get_item_status_flags", []() {
        return ImGui::GetItemStatusFlags();
    }, "Return status flags for the last submitted item as an integer bitmask. Uses Dear ImGui internal API.");

    m.def("keep_alive_id", [](ImGuiID id) {
        ImGui::KeepAliveID(id);
    }, "id"_a,
    "Mark an item id as alive for the current frame. Useful for custom widgets using ButtonBehavior-like state. Uses Dear ImGui internal API.");

    m.def("focus_item", []() {
        ImGui::FocusItem();
    }, "Focus the last submitted item without activating it. Uses Dear ImGui internal API.");

    m.def("activate_item_by_id", [](ImGuiID id) {
        ImGui::ActivateItemByID(id);
    }, "id"_a,
    "Queue activation for an item id on the next frame when that item is submitted. Uses Dear ImGui internal API.");

    m.def("set_active_id_using_all_keyboard_keys", []() {
        ImGui::SetActiveIdUsingAllKeyboardKeys();
    }, "Declare that the current active item wants to own all keyboard keys. Uses Dear ImGui internal API.");

    m.def("is_active_id_using_nav_dir", [](ImGuiDir dir) {
        return ImGui::IsActiveIdUsingNavDir(dir);
    }, "dir"_a,
    "Return true when the active item is using the given navigation direction. Uses Dear ImGui internal API.");

    m.def("consume_io_mouse_clicked", [](ImGuiMouseButton_ button) {
        ImGuiIO& io = ImGui::GetIO();
        io.MouseClicked[button] = false;
    }, "button"_a,
    "Clear io.MouseClicked[button] for the current frame so widgets submitted afterward (e.g. InputText) do not treat it as a new click.\n"
    "MouseDown stays true; pair with clear_active_id() when stealing mouse drags from an overlapping InputText.");

    // "Internal" object getters that receive a context pointer.  Such functions
    // don't exist in the public ImGui API, but we provide them so that we
    // can correctly model object ownership in Python.
    nb::class_<Context>(m, "Context")
        .def("get_io_internal", [](Context* ctx) -> ImGuiIO* {
            auto prev = ctx->setCurrent();
            ImGuiIO& io = ImGui::GetIO();
            ImGui::SetCurrentContext(prev);
            return &io;
        }, nb::rv_policy::reference_internal)
        .def("get_platform_io_internal", [](Context* ctx) -> ImGuiPlatformIO* {
            auto prev = ctx->setCurrent();
            ImGuiPlatformIO& plat_io = ImGui::GetPlatformIO();
            ImGui::SetCurrentContext(prev);
            return &plat_io;
        }, nb::rv_policy::reference_internal)
        .def("get_style_internal", [](Context* ctx) -> ImGuiStyle* {
            auto prev = ctx->setCurrent();
            ImGuiStyle& s = ImGui::GetStyle();
            ImGui::SetCurrentContext(prev);
            return &s;
        }, nb::rv_policy::reference_internal)
        .def("get_font_internal", [](Context* ctx) -> ImFont* {
            auto prev = ctx->setCurrent();
            ImFont* font = ImGui::GetFont();
            ImGui::SetCurrentContext(prev);
            return font;
        }, nb::rv_policy::reference_internal)
        .def("get_background_draw_list_internal", [](Context* ctx) -> ImDrawList* {
            auto prev = ctx->setCurrent();
            ImDrawList* drawList = ImGui::GetBackgroundDrawList();
            ImGui::SetCurrentContext(prev);
            return drawList;
        }, nb::rv_policy::reference)
        .def("get_foreground_draw_list_internal", [](Context* ctx) -> ImDrawList* {
            auto prev = ctx->setCurrent();
            ImDrawList* drawList = ImGui::GetForegroundDrawList();
            ImGui::SetCurrentContext(prev);
            return drawList;
        }, nb::rv_policy::reference)
        .def("get_window_draw_list_internal", [](Context* ctx) -> ImDrawList* {
            auto prev = ctx->setCurrent();
            ImDrawList* drawList = ImGui::GetWindowDrawList();
            ImGui::SetCurrentContext(prev);
            return drawList;
        }, nb::rv_policy::reference)
        .def("accept_drag_drop_payload_internal", [](Context* ctx, const char* type, ImGuiDragDropFlags_ flags) -> std::optional<const ImGuiPayload*> {
            auto prev = ctx->setCurrent();
            const ImGuiPayload* ret = ImGui::AcceptDragDropPayload(type, flags);
            ImGui::SetCurrentContext(prev);
            return ret;
        }, "type"_a, "flags"_a.sig("DragDropFlags.NONE") = ImGuiDragDropFlags_None, nb::rv_policy::reference_internal)
        .def("get_drag_drop_payload_internal", [](Context* ctx) -> std::optional<const ImGuiPayload*> {
            auto prev = ctx->setCurrent();
            const ImGuiPayload* ret = ImGui::GetDragDropPayload();
            ImGui::SetCurrentContext(prev);
            if (ret) {
                return ret;
            }
            return std::nullopt;
        }, nb::rv_policy::reference_internal)
        .def("new_frame_internal", [](Context* ctx) {
            auto prev = ctx->setCurrent();
            ImGui::NewFrame();
            ImGui::SetCurrentContext(prev);
        }, "Internal ImGui::NewFrame(), don't use directly.");

    m.def("create_context_internal", [](ImFontAtlas* shared_font_atlas) -> Context {
        ImGuiContext* ctx = ImGui::CreateContext(shared_font_atlas);
        ImGuiIO& io = ImGui::GetIO(ctx);
        io.BackendLanguageUserData = new ContextBackendData();
        return Context(ctx);
    }, "shared_font_atlas"_a = nullptr, nb::rv_policy::reference);
    m.def("set_current_context_internal", [](Context* ctx) { ImGui::SetCurrentContext(ctx->ctx); }, nb::rv_policy::reference);
    m.def("destroy_context_internal", [](Context* context) {
        ImGuiContext* ctx = context->ctx;
        ContextBackendData* backend_data = static_cast<ContextBackendData*>(ImGui::GetIO(ctx).BackendLanguageUserData);
        delete backend_data;
        ImGui::DestroyContext(ctx);
    });
    m.def("get_draw_data", &ImGui::GetDrawData, nb::rv_policy::reference);
    m.def("get_main_viewport", &ImGui::GetMainViewport, nb::rv_policy::reference);

    m.def("set_initial_fringe_scale", [](float scale) {
        ImGui::GetDrawListSharedData()->InitialFringeScale = scale;
    }, "scale"_a,
    "Set the anti-aliasing fringe scale (default 1.0) applied to draw lists reset after this call "
    "within the current frame. Call right after new_frame() and before any window/draw submission. "
    "When the draw output is upscaled by a model matrix of factor S, pass 1.0/S so the AA fringe and "
    "line/border edges stay ~1 physical pixel wide instead of being stretched (blurry). "
    "Note: any value != 1.0 disables the baked-texture AA line path, so AA lines use the polygon path.");

    // Error recovery: save/restore imgui stack state
    m.def("error_recovery_store_state", []() {
        ImGuiErrorRecoveryState* state = new ImGuiErrorRecoveryState();
        ImGui::ErrorRecoveryStoreState(state);
        return (uintptr_t)state;
    }, "Save current imgui stack sizes for later recovery. Returns an opaque handle.");
    m.def("error_recovery_try_to_recover_state", [](uintptr_t state_handle, bool free_handle) {
        ImGuiErrorRecoveryState* state = (ImGuiErrorRecoveryState*)state_handle;
        ImGui::ErrorRecoveryTryToRecoverState(state);
        if (free_handle)
            delete state;
    }, "state_handle"_a, "free_handle"_a = true,
    "Recover imgui state to a previously saved snapshot. Automatically calls missing End/Pop functions. Optionally frees the handle.");
    m.def("error_recovery_free_state", [](uintptr_t state_handle) {
        delete (ImGuiErrorRecoveryState*)state_handle;
    }, "state_handle"_a, "Free a previously saved state handle without recovering.");
    m.def("error_recovery_try_to_recover_window_state", [](uintptr_t state_handle, bool free_handle) {
        ImGuiErrorRecoveryState* state = (ImGuiErrorRecoveryState*)state_handle;
        ImGui::ErrorRecoveryTryToRecoverWindowState(state);
        if (free_handle)
            delete state;
    }, "state_handle"_a, "free_handle"_a = false,
    "Recover window-level state only (style, font, id stacks etc). Optionally frees the handle.");

    // Demo, Debug, Information
#ifndef IMGUI_DISABLE_DEMO_WINDOWS
    m.def("show_demo_window", [](bool closable) {
        bool open = true;
        ImGui::ShowDemoWindow(closable ? &open : nullptr);
        return open;
    }, "closable"_a = false);
    m.def("show_metrics_window", [](bool closable) {
        bool open = true;
        ImGui::ShowMetricsWindow(closable ? &open : nullptr);
        return open;
    }, "closable"_a = false);
    m.def("show_debug_log_window", [](bool closable) {
        bool open = true;
        ImGui::ShowDebugLogWindow(closable ? &open : nullptr);
        return open;
    }, "closable"_a = false);
    m.def("show_id_stack_tool_window", [](bool closable) {
        bool open = true;
        ImGui::ShowIDStackToolWindow(closable ? &open : nullptr);
        return open;
    }, "closable"_a = false);
    m.def("show_about_window", [](bool closable) {
        bool open = true;
        ImGui::ShowAboutWindow(closable ? &open : nullptr);
        return open;
    }, "closable"_a = false);
    m.def("show_style_editor", []() {
        ImGui::ShowStyleEditor(nullptr); // TODO styleref
    });
    m.def("show_style_selector", &ImGui::ShowStyleSelector, "label"_a,
        "Add style selector block (not a window), essentially a combo listing the default styles.");
    m.def("show_font_selector", &ImGui::ShowFontSelector, "label"_a,
        "Add font selector block (not a window), essentially a combo listing the loaded fonts.");
    m.def("show_user_guide", &ImGui::ShowUserGuide,
        "Add basic help/info block (not a window): how to manipulate ImGui as an end-user (mouse/keyboard controls).");
#endif

    // Styles
    m.def("style_colors_dark_internal", &ImGui::StyleColorsDark, "dst"_a);
    m.def("style_colors_light_internal", &ImGui::StyleColorsLight, "dst"_a);
    m.def("style_colors_classic_internal", &ImGui::StyleColorsClassic, "dst"_a);

    // ...
    m.def("begin", [](const char* name, bool closable, ImGuiWindowFlags_ flags) {
        bool open = true;
        bool visible = ImGui::Begin(name, closable ? &open : NULL, flags);
        return std::pair(visible, open);
    }, "name"_a, "closable"_a = false, "flags"_a.sig("WindowFlags.NONE") = ImGuiWindowFlags_None);
    // IMGUI_API bool          BeginChild(ImGuiID id, const ImVec2& size = ImVec2(0, 0), ImGuiChildFlags child_flags = 0, ImGuiWindowFlags window_flags = 0);
    m.def("begin_child", [](const char* str_id, const ImVec2& size, ImGuiChildFlags_ child_flags, ImGuiWindowFlags_ window_flags) {
        return ImGui::BeginChild(str_id, size, child_flags, window_flags);
    }, "str_id"_a, "size"_a =  ImVec2(0, 0), "child_flags"_a.sig("ChildFlags.NONE") = ImGuiChildFlags_None, "window_flags"_a.sig("WindowFlags.NONE") = ImGuiWindowFlags_None);

    // Windows Utilities
    m.def("is_window_focused", [](ImGuiFocusedFlags_ flags) { return ImGui::IsWindowFocused(flags); }, "flags"_a.sig("FocusedFlags.NONE") = ImGuiFocusedFlags_None);
    m.def("is_window_hovered", [](ImGuiHoveredFlags_ flags) { return ImGui::IsWindowHovered(flags); }, "flags"_a.sig("HoveredFlags.NONE") = ImGuiHoveredFlags_None);
    // IMGUI_API ImDrawList*   GetWindowDrawList();                        // get draw list associated to the current window, to append your own drawing primitives

    // Window manipulation
    // - Prefer using SetNextXXX functions (before Begin) rather that SetXXX functions (after Begin).
    m.def("set_next_window_pos", [](const ImVec2 &pos, ImGuiCond_ cond, const ImVec2 &pivot) {
        ImGui::SetNextWindowPos(pos, cond, pivot);
    }, "pos"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None, "pivot"_a = ImVec2(0,0));
    m.def("set_next_window_size", [](const ImVec2 &size, ImGuiCond_ cond) {
        ImGui::SetNextWindowSize(size, cond);
    }, "size"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);

    // Note: the Python callback reference should be kept alive by the WrapperContext on the Python wrapper side.
    m.def("set_next_window_size_constraints_internal", [](const ImVec2& size_min, const ImVec2& size_max, std::optional<nb::callable> cb) {
        ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
        ContextBackendData* bd = (ContextBackendData*)io.BackendLanguageUserData;
        if (cb) {
            bd->size_constraints_callback = nb::cast(cb.value());
            ImGui::SetNextWindowSizeConstraints(size_min, size_max, &window_size_constraints_callback_py_wrapper, bd);
        } else {
            bd->size_constraints_callback = nb::none();
            ImGui::SetNextWindowSizeConstraints(size_min, size_max, nullptr, nullptr);
        }
    }, "size_min"_a, "size_max"_a, "cb"_a = nb::none());

    m.def("set_next_window_collapsed", [](bool collapsed, ImGuiCond_ cond) {
        ImGui::SetNextWindowCollapsed(collapsed, cond);
    }, "collapsed"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_pos", [](const ImVec2& pos, ImGuiCond_ cond) { ImGui::SetWindowPos(pos, cond); }, "pos"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_size", [](const ImVec2& size, ImGuiCond_ cond) { ImGui::SetWindowSize(size, cond); }, "size"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_collapsed", [](bool collapsed, ImGuiCond_ cond) { ImGui::SetWindowCollapsed(collapsed, cond); }, "collapsed"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_focus", []() { ImGui::SetWindowFocus(); });
    m.def("set_window_pos", [](const char* name, const ImVec2& pos, ImGuiCond_ cond) { ImGui::SetWindowPos(name, pos, cond); }, "name"_a, "pos"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_size", [](const char* name, const ImVec2& size, ImGuiCond_ cond) { ImGui::SetWindowSize(name, size, cond); }, "name"_a, "size"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_collapsed", [](const char* name, bool collapsed, ImGuiCond_ cond) { ImGui::SetWindowCollapsed(name, collapsed, cond); }, "name"_a, "collapsed"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("set_window_focus", [](const char* name) { ImGui::SetWindowFocus(name); }, "name"_a);

    // Content region

    // Windows Scrolling
    m.def("set_scroll_x", [](float scroll_x) { ImGui::SetScrollX(scroll_x); }, "scroll_x"_a);
    m.def("set_scroll_y", [](float scroll_y) { ImGui::SetScrollY(scroll_y); }, "scroll_y"_a);
    m.def("set_scroll_from_pos_x", [](float local_x, float center_x_ratio) {
        ImGui::SetScrollFromPosX(local_x, center_x_ratio);
    }, "local_x"_a, "center_x_ratio"_a = 0.5f);
    m.def("set_scroll_from_pos_y", [](float local_y, float center_y_ratio) {
        ImGui::SetScrollFromPosY(local_y, center_y_ratio);
    }, "local_y"_a, "center_y_ratio"_a = 0.5f);

    // Parameters stacks (shared)
    m.def("push_font", [](ImFont* font, float font_size_base) {
        ImGui::PushFont(font, font_size_base);
    }, "font"_a.none(), "font_size_base"_a, "Use `None` as a shortcut to keep current font.  Use 0.0 for `font_size_base` to keep the current font size.");

    m.def("push_style_color", [](ImGuiCol_ idx, ImU32 col) { ImGui::PushStyleColor(idx, col); }, "idx"_a, "col"_a);
    m.def("push_style_color", [](ImGuiCol_ idx, const ImVec4& col) { ImGui::PushStyleColor(idx, col); }, "idx"_a, "col"_a);
    m.def("push_style_color", [](ImGuiCol_ idx, const Vec3& col) {
        ImVec4 c(col.x, col.y, col.z, 1.0f);
        ImGui::PushStyleColor(idx, c);
    }, "idx"_a, "col"_a);
    m.def("push_style_var", [](ImGuiStyleVar_ idx, float val) { ImGui::PushStyleVar(idx, val); }, "idx"_a, "val"_a);
    m.def("push_style_var", [](ImGuiStyleVar_ idx, const ImVec2& val) { ImGui::PushStyleVar(idx, val); }, "idx"_a, "val"_a);
    m.def("push_style_var_x", [](ImGuiStyleVar_ idx, float val_x) { ImGui::PushStyleVarX(idx, val_x); }, "idx"_a, "val_x"_a);
    m.def("push_style_var_y", [](ImGuiStyleVar_ idx, float val_y) { ImGui::PushStyleVarY(idx, val_y); }, "idx"_a, "val_y"_a);
    m.def("push_item_flag", [](ImGuiItemFlags_ option, bool enabled) { ImGui::PushItemFlag(option, enabled); }, "option"_a, "enabled"_a);

    // Parameters stacks (current window)

    // Style read access
    // IMGUI_API ImFont*       GetFont();                                                      // get current font

    m.def("get_color_u32", [](ImGuiCol_ idx, float alpha_mul) { return ImGui::GetColorU32(idx, alpha_mul);}, "idx"_a, "alpha_mul"_a = 1.0f);
    m.def("get_color_u32", [](ImVec4 col)                     { return ImGui::GetColorU32(col);}, "col"_a);
    m.def("get_color_u32", [](ImU32 col, float alpha_mul)     { return ImGui::GetColorU32(col, alpha_mul);}, "col"_a, "alpha_mul"_a = 1.0f);
    // get_style_color_vec4 (manual: uses "col" param name for API compat)
    m.def("get_style_color_vec4", [](ImGuiCol_ idx) { return ImGui::GetStyleColorVec4(idx);}, "col"_a);

    // ID stack/scopes
    m.def("push_id", [](const char* str_id) {  ImGui::PushID(str_id); }, "str_id"_a);
    m.def("push_id", [](int int_id) {  ImGui::PushID(int_id); }, "int_id"_a);
    m.def("get_id", [](const char* str_id) {  ImGui::GetID(str_id); }, "str_id"_a);
    m.def("get_id", [](int int_id)         {  ImGui::GetID(int_id); }, "int_id"_a);
    m.def("pop_id", &ImGui::PopID);

    // Widgets: Text
    m.def("text", [](const char* text) { ImGui::TextUnformatted(text); }, "text"_a);
    m.def("text_colored", [](const ImVec4& col, const char* text) { ImGui::TextColored(col, "%s", text); }, "col"_a, "text"_a);
    m.def("text_disabled", [](const char* text) { ImGui::TextDisabled("%s", text); }, "text"_a);
    m.def("text_wrapped", [](const char* text) { ImGui::TextWrapped("%s", text); }, "text"_a);
    m.def("bullet_text", [](const char* text) { ImGui::BulletText("%s", text); }, "text"_a);
    m.def("label_text", [](const char* label, const char* text) { ImGui::LabelText(label, "%s", text); }, "label"_a, "text"_a);
    // separator_text (manual: uses "text" param name for API compat)
    m.def("separator_text", &ImGui::SeparatorText, "text"_a);

    // Widgets: Main
    // invisible_button (manual: .sig() for flags)
    m.def("invisible_button", [](const char* str_id, const ImVec2 &size, ImGuiButtonFlags_ flags) {
        return ImGui::InvisibleButton(str_id, size, flags);
    }, "str_id"_a, "size"_a, "flags"_a.sig("ButtonFlags.NONE") = ImGuiButtonFlags_None);
    m.def("checkbox", [](const char* label, bool v) {
        bool pressed = ImGui::Checkbox(label, &v);
        return std::tuple(pressed, v);
    }, "label"_a, "v"_a);
    m.def("checkbox_flags", [](const char* label, ImU64 flags, ImU64 flags_value) {
        bool pressed = ImGui::CheckboxFlags(label, &flags, flags_value);
        return std::tuple(pressed, flags);
    }, "label"_a, "flags"_a, "flags_value"_a);
    m.def("radio_button", [](const char* label, bool active) {
        return ImGui::RadioButton(label, active);
    }, "label"_a, "active"_a);
    m.def("radio_button", [](const char* label, int v, int v_button) {
        bool pressed = ImGui::RadioButton(label, &v, v_button);
        return std::tuple(pressed, v);
    }, "label"_a, "v"_a, "v_button"_a);
    m.def("progress_bar", [](float fraction, ImVec2 size_arg, std::optional<std::string> overlay) {
        ImGui::ProgressBar(fraction, size_arg, overlay ? overlay.value().c_str() : nullptr);
    }, "fraction"_a, "size_arg"_a.sig("(-FLT_MIN, 0)") = ImVec2(-FLT_MIN, 0), "overlay"_a = nb::none());
    m.def("text_link", [](const char* label) { ImGui::TextLink(label); }, "label"_a);
    m.def("text_link_open_url", [](const char* label, std::optional<const char*> url) { ImGui::TextLinkOpenURL(label, url ? url.value() : nullptr); }, "label"_a, "url"_a = nb::none());

    // Widgets: Images
    m.def("image", [](TextureRefOrID tex_ref, const ImVec2 image_size, const ImVec2 uv0, const ImVec2 uv1) {
        return ImGui::Image(to_texture_ref(tex_ref), image_size, uv0, uv1);
    }, "tex_ref"_a, "image_size"_a, "uv0"_a = ImVec2(0, 0), "uv1"_a = ImVec2(1, 1));
    m.def("image_with_bg", [](TextureRefOrID tex_ref, const ImVec2& image_size, const ImVec2& uv0, const ImVec2& uv1, const ImVec4& bg_col, const ImVec4& tint_col) {
        return ImGui::ImageWithBg(to_texture_ref(tex_ref), image_size, uv0, uv1, bg_col, tint_col);
    }, "tex_ref"_a, "image_size"_a, "uv0"_a = ImVec2(0, 0), "uv1"_a = ImVec2(1, 1), "bg_col"_a = ImVec4(0, 0, 0, 0), "tint_col"_a = ImVec4(1, 1, 1, 1));
    m.def("image_button", [](const char* str_id, TextureRefOrID tex_ref, const ImVec2& image_size, const ImVec2& uv0, const ImVec2& uv1, const ImVec4& bg_col, const ImVec4& tint_col) {
        return ImGui::ImageButton(str_id, to_texture_ref(tex_ref), image_size, uv0, uv1, bg_col, tint_col);
    }, "str_id"_a, "tex_ref"_a, "image_size"_a, "uv0"_a = ImVec2(0, 0), "uv1"_a = ImVec2(1, 1), "bg_col"_a = ImVec4(0, 0, 0, 0), "tint_col"_a = ImVec4(1, 1, 1, 1));

    // Widgets: Combo Box (Dropdown)
    m.def("begin_combo", [](const char *label, const char *preview_value, ImGuiComboFlags_ flags) {
        return ImGui::BeginCombo(label, preview_value, flags);
    }, "label"_a, "preview_value"_a, "flags"_a.sig("ComboFlags.NONE") = ImGuiComboFlags_None);
    m.def("end_combo", &ImGui::EndCombo);
    m.def("combo", [](const char* label, int current_item, const std::vector<const char*>& items, int popup_max_height_in_items) {
        bool changed = ImGui::Combo(label, &current_item, &items[0], items.size(), popup_max_height_in_items);
        return std::tuple(changed, current_item);
    }, "label"_a, "current_item"_a, "items"_a, "popup_max_height_in_items"_a = -1);
    m.def("combo", [](const char* label, int current_item, nb::callable getter, int items_count, int popup_max_height_in_items) {
        struct GetterData { nb::callable* fn; };
        GetterData gd { &getter };
        auto c_getter = [](void* user_data, int idx) -> const char* {
            GetterData* gd = (GetterData*)user_data;
            try {
                nb::object result = (*gd->fn)(idx);
                return nb::cast<const char*>(result);
            } catch (nb::python_error& e) {
                e.discard_as_unraisable("combo getter callback");
                return "";
            }
        };
        bool changed = ImGui::Combo(label, &current_item, c_getter, &gd, items_count, popup_max_height_in_items);
        return std::tuple(changed, current_item);
    }, "label"_a, "current_item"_a, "getter"_a, "items_count"_a, "popup_max_height_in_items"_a = -1);

    // get_cursor_screen_pos, set_cursor_screen_pos, get_cursor_pos, get_cursor_pos_x, get_cursor_pos_y
    // set_cursor_pos, set_cursor_pos_x, set_cursor_pos_y, get_cursor_start_pos

    // separator, same_line, new_line, spacing, dummy, indent, unindent
    // begin_group, end_group, align_text_to_frame_padding
    // get_text_line_height, get_text_line_height_with_spacing
    // get_frame_height, get_frame_height_with_spacing

    m.def("begin_menu", &ImGui::BeginMenu, "label"_a, "enabled"_a = true);
    m.def("menu_item", [](const char* label, std::optional<std::string> shortcut, bool selected, bool enabled) {
        bool mut_selected = selected;
        bool clicked = ImGui::MenuItem(label, shortcut ? shortcut.value().c_str() : nullptr, &mut_selected, enabled);
        return std::pair(clicked, mut_selected);
    }, "label"_a, "shortcut"_a = nb::none(), "selected"_a = false, "enabled"_a = true);

    // Tooltips
    m.def("set_tooltip", [](const char* text) { ImGui::SetTooltip("%s", text);}, "text"_a);
    m.def("set_item_tooltip", [](const char* text) { ImGui::SetItemTooltip("%s", text);}, "text"_a);

    m.def("begin_popup", [](const char *str_id, ImGuiWindowFlags_ flags) {
        return ImGui::BeginPopup(str_id, flags);
    }, "str_id"_a, "flags"_a.sig("WindowFlags.NONE") = ImGuiWindowFlags_None);
    m.def("begin_popup_modal", [](const char *str_id, bool closable, ImGuiWindowFlags_ flags) {
        bool open = true;
        bool ret = ImGui::BeginPopupModal(str_id, closable ? &open : nullptr, flags);
        return std::pair(ret, open);
    }, "str_id"_a, "closable"_a = false, "flags"_a.sig("WindowFlags.NONE") = ImGuiWindowFlags_None,
    "Returns a tuple of bools.  If the first returned bool is `True`, the modal is open and you can start outputting to it.");
    m.def("open_popup", [](const char* str_id, ImGuiPopupFlags_ flags) {
        ImGui::OpenPopup(str_id, flags);
    }, "str_id"_a, "flags"_a.sig("PopupFlags.NONE") = ImGuiPopupFlags_None);
    // IMGUI_API void          OpenPopup(ImGuiID id, ImGuiPopupFlags popup_flags = 0);                             // id overload to facilitate calling from nested stacks
    m.def("open_popup_on_item_click", [](std::optional<std::string> str_id, ImGuiPopupFlags_ flags) {
        ImGui::OpenPopupOnItemClick(str_id ? str_id.value().c_str() : nullptr, flags);
    }, "str_id"_a = nb::none(), "flags"_a.sig("PopupFlags.MOUSE_BUTTON_RIGHT") = ImGuiPopupFlags_MouseButtonRight);

    // // Popups: open+begin combined functions helpers
    // //  - Helpers to do OpenPopup+BeginPopup where the Open action is triggered by e.g. hovering an item and right-clicking.
    // //  - They are convenient to easily create context menus, hence the name.
    // //  - IMPORTANT: Notice that BeginPopupContextXXX takes ImGuiPopupFlags just like OpenPopup() and unlike BeginPopup(). For full consistency, we may add ImGuiWindowFlags to the BeginPopupContextXXX functions in the future.
    // //  - IMPORTANT: Notice that we exceptionally default their flags to 1 (== ImGuiPopupFlags_MouseButtonRight) for backward compatibility with older API taking 'int mouse_button = 1' parameter, so if you add other flags remember to re-add the ImGuiPopupFlags_MouseButtonRight.
    m.def("begin_popup_context_item", [](std::optional<const char*> str_id, ImGuiPopupFlags_ flags) {
        return ImGui::BeginPopupContextItem(str_id ? str_id.value() : nullptr, flags);
    }, "str_id"_a = nb::none(), "flags"_a.sig("PopupFlags.MOUSE_BUTTON_RIGHT") = ImGuiPopupFlags_MouseButtonRight);
    m.def("begin_popup_context_window", [](std::optional<const char*> str_id, ImGuiPopupFlags_ flags) {
        return ImGui::BeginPopupContextWindow(str_id ? str_id.value() : nullptr, flags);
    }, "str_id"_a = nb::none(), "flags"_a.sig("PopupFlags.MOUSE_BUTTON_RIGHT") = ImGuiPopupFlags_MouseButtonRight);
    m.def("begin_popup_context_void", [](std::optional<const char*> str_id, ImGuiPopupFlags_ flags) {
        return ImGui::BeginPopupContextVoid(str_id ? str_id.value() : nullptr, flags);
    }, "str_id"_a = nb::none(), "flags"_a.sig("PopupFlags.MOUSE_BUTTON_RIGHT") = ImGuiPopupFlags_MouseButtonRight);
    // // Popups: query functions
    // //  - IsPopupOpen(): return true if the popup is open at the current BeginPopup() level of the popup stack.
    // //  - IsPopupOpen() with ImGuiPopupFlags_AnyPopupId: return true if any popup is open at the current BeginPopup() level of the popup stack.
    // //  - IsPopupOpen() with ImGuiPopupFlags_AnyPopupId + ImGuiPopupFlags_AnyPopupLevel: return true if any popup is open.
    m.def("is_popup_open", [](const char* str_id, ImGuiPopupFlags_ flags) {
        return ImGui::IsPopupOpen(str_id, flags);
    }, "str_id"_a, "flags"_a.sig("PopupFlags.NONE") = ImGuiPopupFlags_None);

    // Widgets: Trees
    m.def("tree_node", [](const char* label, ImGuiTreeNodeFlags_ flags) {
        return ImGui::TreeNodeEx(label, flags);
    }, "label"_a, "flags"_a.sig("TreeNodeFlags.NONE") = ImGuiTreeNodeFlags_None);
    m.def("tree_node", [](const char* str_id, const char* text, ImGuiTreeNodeFlags_ flags) {
        return ImGui::TreeNodeEx(str_id, flags, "%s", text);
    }, "str_id"_a, "text"_a, "flags"_a.sig("TreeNodeFlags.NONE") = ImGuiTreeNodeFlags_None);
    m.def("set_next_item_open", [](bool is_open, ImGuiCond_ cond) {
        ImGui::SetNextItemOpen(is_open, cond);
    }, "is_open"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);
    m.def("collapsing_header", [](const char* label, std::optional<bool> visible, ImGuiTreeNodeFlags_ flags) {
        if (!visible) {
            bool clicked = ImGui::CollapsingHeader(label, nullptr, flags);
            return std::pair(clicked, std::optional<bool>{});
        }
        bool inout_visible = visible.value();
        bool open = ImGui::CollapsingHeader(label, &inout_visible, flags);
        return std::pair(open, std::optional<bool>{inout_visible});
    }, "label"_a, "visible"_a = nb::none(), "flags"_a.sig("TreeNodeFlags.NONE") = ImGuiTreeNodeFlags_None);

    // Widgets: Selectables
    m.def("selectable", [](const char* label, bool selected, ImGuiSelectableFlags_ flags, const ImVec2& size) {
        bool clicked = ImGui::Selectable(label, &selected, flags, size);
        return std::pair(clicked, selected);
    }, "label"_a, "selected"_a = false, "flags"_a.sig("SelectableFlags.NONE") = ImGuiSelectableFlags_None, "size"_a = ImVec2(0, 0),
    "The `selected` argument indicates whether the item is selected or not.\n"
    "\n"
    "When `size[0] == 0.0` use remaining width.  Use `size[0] > 0.0` to specify width.\n"
    "When `size[1] == 0.0` use label height.  Use `size[1] > 0.0` to specify height.\n"
    "\n"
    "The returned pair contains:\n"
    "\n"
    "- first element: a boolean indicating whether the item was clicked.\n"
    "- second element: the updated selection state of the item.\n");

    // Widgets: List Boxes
    m.def("begin_list_box", &ImGui::BeginListBox, "label"_a, "size"_a = ImVec2(0, 0));
    m.def("end_list_box", &ImGui::EndListBox);
    m.def("list_box", [](const char* label, int current_item, const std::vector<const char*>& items, int height_in_items) {
        bool changed = ImGui::ListBox(label, &current_item, &items[0], items.size(), height_in_items);
        return std::tuple(changed, current_item);
    }, "label"_a, "current_item"_a, "items"_a, "height_in_items"_a = -1);
    m.def("list_box", [](const char* label, int current_item, nb::callable getter, int items_count, int height_in_items) {
        struct GetterData { nb::callable* fn; };
        GetterData gd { &getter };
        auto c_getter = [](void* user_data, int idx) -> const char* {
            GetterData* gd = (GetterData*)user_data;
            try {
                nb::object result = (*gd->fn)(idx);
                return nb::cast<const char*>(result);
            } catch (nb::python_error& e) {
                e.discard_as_unraisable("list_box getter callback");
                return "";
            }
        };
        bool changed = ImGui::ListBox(label, &current_item, c_getter, &gd, items_count, height_in_items);
        return std::tuple(changed, current_item);
    }, "label"_a, "current_item"_a, "getter"_a, "items_count"_a, "height_in_items"_a = -1);

    // Multi-Select API
    m.def("begin_multi_select", [](ImGuiMultiSelectFlags_ flags, int selection_size, int items_count) {
        return ImGui::BeginMultiSelect(flags, selection_size, items_count);
    }, "flags"_a, "selection_size"_a = -1, "items_count"_a = -1, nb::rv_policy::reference);
    m.def("end_multi_select", &ImGui::EndMultiSelect, nb::rv_policy::reference);
    m.def("set_next_item_selection_user_data", &ImGui::SetNextItemSelectionUserData, "selection_user_data"_a);
    m.def("is_item_toggled_selection", &ImGui::IsItemToggledSelection);

    m.def("plot_lines", [](const char* label, const nb::ndarray<const float, nb::ndim<1>, nb::device::cpu>& arr, std::optional<std::string> overlay_text, float scale_min, float scale_max, ImVec2 graph_size) {
        ImGui::PlotLines(label, arr.data(), arr.shape(0), 0, overlay_text ? overlay_text.value().c_str() : nullptr, scale_min, scale_max, graph_size);
    }, "label"_a, "values"_a, "overlay_text"_a = nb::none(), "scale_min"_a.sig("FLT_MAX") = FLT_MAX, "scale_max"_a.sig("FLT_MAX") = FLT_MAX, "graph_size"_a = ImVec2(0,0));
    m.def("plot_lines", [](const char* label, nb::callable values_getter, int values_count, int values_offset, std::optional<std::string> overlay_text, float scale_min, float scale_max, ImVec2 graph_size) {
        struct GetterData { nb::callable* fn; };
        GetterData gd { &values_getter };
        auto c_getter = [](void* user_data, int idx) -> float {
            GetterData* gd = (GetterData*)user_data;
            try {
                return nb::cast<float>((*gd->fn)(idx));
            } catch (nb::python_error& e) {
                e.discard_as_unraisable("plot_lines values_getter callback");
                return 0.0f;
            }
        };
        ImGui::PlotLines(label, c_getter, &gd, values_count, values_offset, overlay_text ? overlay_text.value().c_str() : nullptr, scale_min, scale_max, graph_size);
    }, "label"_a, "values_getter"_a, "values_count"_a, "values_offset"_a = 0, "overlay_text"_a = nb::none(), "scale_min"_a.sig("FLT_MAX") = FLT_MAX, "scale_max"_a.sig("FLT_MAX") = FLT_MAX, "graph_size"_a = ImVec2(0,0));
    m.def("plot_histogram", [](const char* label, const nb::ndarray<const float, nb::ndim<1>, nb::device::cpu>& arr, std::optional<std::string> overlay_text, float scale_min, float scale_max, ImVec2 graph_size) {
        ImGui::PlotHistogram(label, arr.data(), arr.shape(0), 0, overlay_text ? overlay_text.value().c_str() : nullptr, scale_min, scale_max, graph_size);
    }, "label"_a, "values"_a, "overlay_text"_a = nb::none(), "scale_min"_a.sig("FLT_MAX") = FLT_MAX, "scale_max"_a.sig("FLT_MAX") = FLT_MAX, "graph_size"_a = ImVec2(0,0));
    m.def("plot_histogram", [](const char* label, nb::callable values_getter, int values_count, int values_offset, std::optional<std::string> overlay_text, float scale_min, float scale_max, ImVec2 graph_size) {
        struct GetterData { nb::callable* fn; };
        GetterData gd { &values_getter };
        auto c_getter = [](void* user_data, int idx) -> float {
            GetterData* gd = (GetterData*)user_data;
            try {
                return nb::cast<float>((*gd->fn)(idx));
            } catch (nb::python_error& e) {
                e.discard_as_unraisable("plot_histogram values_getter callback");
                return 0.0f;
            }
        };
        ImGui::PlotHistogram(label, c_getter, &gd, values_count, values_offset, overlay_text ? overlay_text.value().c_str() : nullptr, scale_min, scale_max, graph_size);
    }, "label"_a, "values_getter"_a, "values_count"_a, "values_offset"_a = 0, "overlay_text"_a = nb::none(), "scale_min"_a.sig("FLT_MAX") = FLT_MAX, "scale_max"_a.sig("FLT_MAX") = FLT_MAX, "graph_size"_a = ImVec2(0,0));
    // // Widgets: Regular Sliders
    m.def("slider_float", [](const char* label, float v, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::SliderFloat(label, &v, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%.3f", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_float2", [](const char* label, std::tuple<float, float> v, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<float>(v);
        bool changed = ImGui::SliderFloat2(label, vals.data(), v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple<float>(vals));
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%.3f", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_float3", [](const char* label, std::tuple<float, float, float> v, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<float>(v);
        bool changed = ImGui::SliderFloat3(label, vals.data(), v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple<float>(vals));
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%.3f", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_float4", [](const char* label, std::tuple<float, float, float, float> v, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<float>(v);
        bool changed = ImGui::SliderFloat4(label, vals.data(), v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple<float>(vals));
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%.3f", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_angle", [](const char* label, float v_rad, float v_degrees_min, float v_degrees_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::SliderAngle(label, &v_rad, v_degrees_min, v_degrees_max, format, flags);
        return std::pair(changed, v_rad);
    }, "label"_a, "v"_a, "v_degrees_min"_a = -360.f, "v_degrees_max"_a = 360.f, "format"_a = "%.0f deg", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_int", [](const char* label, int v, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::SliderInt(label, &v, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%d", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_int2", [](const char* label, std::tuple<int, int> v, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::SliderInt2(label, vals.data(), v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple<int>(vals));
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%d", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_int3", [](const char* label, std::tuple<int, int, int> v, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::SliderInt3(label, vals.data(), v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple<int>(vals));
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%d", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("slider_int4", [](const char* label, std::tuple<int, int, int, int> v, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::SliderInt4(label, vals.data(), v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple<int>(vals));
    }, "label"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%d", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    // IMGUI_API bool          SliderScalar(const char* label, ImGuiDataType data_type, void* p_data, const void* p_min, const void* p_max, const char* format = NULL, ImGuiSliderFlags flags = 0);
    // IMGUI_API bool          SliderScalarN(const char* label, ImGuiDataType data_type, void* p_data, int components, const void* p_min, const void* p_max, const char* format = NULL, ImGuiSliderFlags flags = 0);
    m.def("vslider_float", [](const char* label, ImVec2 size, float v, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::VSliderFloat(label, size, &v, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "size"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%.3f", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("vslider_int", [](const char* label, ImVec2 size, int v, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::VSliderInt(label, size, &v, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "size"_a, "v"_a, "v_min"_a, "v_max"_a, "format"_a = "%d", "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    // IMGUI_API bool          VSliderScalar(const char* label, const ImVec2& size, ImGuiDataType data_type, void* p_data, const void* p_min, const void* p_max, const char* format = NULL, ImGuiSliderFlags flags = 0);

    // Widgets: Drag Sliders
    // IMGUI_API bool          DragScalar(const char* label, ImGuiDataType data_type, void* p_data, float v_speed = 1.0f, const void* p_min = NULL, const void* p_max = NULL, const char* format = NULL, ImGuiSliderFlags flags = 0);
    // IMGUI_API bool          DragScalarN(const char* label, ImGuiDataType data_type, void* p_data, int components, float v_speed = 1.0f, const void* p_min = NULL, const void* p_max = NULL, const char* format = NULL, ImGuiSliderFlags flags = 0);
    m.def("drag_float", [](const char* label, float v, float v_speed, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragFloat(label, &v, v_speed, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0.0f, "v_max"_a = 0.0f, "format"_a = "%.3f",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_float2", [](const char* label, ImVec2 v, float v_speed, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragFloat2(label, &v.x, v_speed, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0.0f, "v_max"_a = 0.0f, "format"_a = "%.3f",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_float3", [](const char* label, Vec3 v, float v_speed, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragFloat3(label, &v.x, v_speed, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0.0f, "v_max"_a = 0.0f, "format"_a = "%.3f",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_float4", [](const char* label, ImVec4 v, float v_speed, float v_min, float v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragFloat4(label, &v.x, v_speed, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0.0f, "v_max"_a = 0.0f, "format"_a = "%.3f",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_float_range2", [](const char* label, float v_current_min, float v_current_max, float v_speed, float v_min, float v_max, const char* format, std::optional<const char*> format_max, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragFloatRange2(label, &v_current_min, &v_current_max, v_speed, v_min, v_max, format, format_max ? format_max.value() : nullptr, flags);
        return std::tuple(changed, v_current_min, v_current_max);
    }, "label"_a, "v_current_min"_a, "v_current_max"_a, "v_speed"_a = 1.0f, "v_min"_a = 0.0f, "v_max"_a = 0.0f, "format"_a = "%.3f", "format_max"_a = nb::none(), "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    m.def("drag_int", [](const char* label, int v, float v_speed, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragInt(label, &v, v_speed, v_min, v_max, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0, "v_max"_a = 0, "format"_a = "%d",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_int2", [](const char* label, std::tuple<int, int> v, float v_speed, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::DragInt2(label, vals.data(), v_speed, v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple(vals));
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0, "v_max"_a = 0, "format"_a = "%d",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_int3", [](const char* label, std::tuple<int, int, int> v, float v_speed, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::DragInt3(label, vals.data(), v_speed, v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple(vals));
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0, "v_max"_a = 0, "format"_a = "%d",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_int4", [](const char* label, std::tuple<int, int, int, int> v, float v_speed, int v_min, int v_max, const char* format, ImGuiSliderFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::DragInt4(label, vals.data(), v_speed, v_min, v_max, format, flags);
        return std::pair(changed, array_to_tuple(vals));
    }, "label"_a, "v"_a, "v_speed"_a = 1.0f, "v_min"_a = 0, "v_max"_a = 0, "format"_a = "%d",  "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);
    m.def("drag_int_range2", [](const char* label, int v_current_min, int v_current_max, float v_speed, int v_min, int v_max, const char* format, std::optional<const char*> format_max, ImGuiSliderFlags_ flags) {
        bool changed = ImGui::DragIntRange2(label, &v_current_min, &v_current_max, v_speed, v_min, v_max, format, format_max ? format_max.value() : nullptr, flags);
        return std::tuple(changed, v_current_min, v_current_max);
    }, "label"_a, "v_current_min"_a, "v_current_max"_a, "v_speed"_a = 1.0f, "v_min"_a = 0, "v_max"_a = 0, "format"_a = "%d", "format_max"_a = nb::none(), "flags"_a.sig("SliderFlags.NONE") = ImGuiSliderFlags_None);

    // Widgets: Input with Keyboard
    auto input_text_handler = [](const char* label, const char* hint, std::string text, ImGuiInputTextFlags flags, bool multiline, std::optional<nb::callable> py_callback, ImVec2 size = ImVec2(0, 0)) {
        IM_ASSERT((flags & ImGuiInputTextFlags_CallbackResize) == 0);
        flags |= ImGuiInputTextFlags_CallbackResize;

        InputTextCallback_UserData cb_user_data;
        cb_user_data.Str = &text;
        cb_user_data.ChainCallback = py_callback ? &py_callback.value() : nullptr;

        bool changed;
        if (!multiline) {
            changed = hint == nullptr ?
                ImGui::InputText(label, (char*)text.c_str(), text.capacity() + 1, flags, InputTextCallback, &cb_user_data) :
                ImGui::InputTextWithHint(label, hint, (char*)text.c_str(), text.capacity() + 1, flags, InputTextCallback, &cb_user_data);
        } else {
            changed = ImGui::InputTextMultiline(label, (char*)text.c_str(), text.capacity() + 1, size, flags, InputTextCallback, &cb_user_data);
        }
        return std::pair(changed, text);
    };
    m.def("input_text", [&](const char* label, std::string text, ImGuiInputTextFlags_ flags, std::optional<nb::callable> callback) {
        return input_text_handler(label, nullptr, text, flags, false, callback);
    }, "label"_a, "text"_a, "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None, "callback"_a = nb::none());
    m.def("input_text_with_hint", [&](const char* label, const char* hint, std::string text, ImGuiInputTextFlags_ flags, std::optional<nb::callable> callback) {
        return input_text_handler(label, hint, text, flags, false, callback);
    }, "label"_a, "hint"_a, "text"_a, "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None, "callback"_a = nb::none());
    m.def("input_text_multiline", [&](const char* label, std::string text, ImVec2 size, ImGuiInputTextFlags_ flags, std::optional<nb::callable> callback) {
        return input_text_handler(label, nullptr, text, flags, true, callback, size);
    }, "label"_a, "text"_a, "size"_a = ImVec2(0, 0), "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None, "callback"_a = nb::none());

    m.def("input_int", [](const char* label, int v, int step, int step_fast, ImGuiInputTextFlags_ flags) {
        bool changed = ImGui::InputInt(label, &v, step, step_fast, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "step"_a = 1, "step_fast"_a = 100, "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);
    m.def("input_int2", [](const char* label, std::tuple<int, int> v, ImGuiInputTextFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::InputInt2(label, vals.data(), flags);
        return std::pair(changed, array_to_tuple(vals));
    }, "label"_a, "v"_a, "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);
    m.def("input_int3", [](const char* label, std::tuple<int, int, int> v, ImGuiInputTextFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::InputInt3(label, vals.data(), flags);
        return std::pair(changed, array_to_tuple(vals));
    }, "label"_a, "v"_a, "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);
    m.def("input_int4", [](const char* label, std::tuple<int, int, int, int> v, ImGuiInputTextFlags_ flags) {
        auto vals = tuple_to_array<int>(v);
        bool changed = ImGui::InputInt4(label, vals.data(), flags);
        return std::pair(changed, array_to_tuple(vals));
    }, "label"_a, "v"_a, "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);

    m.def("input_float", [](const char* label, float v, float step, float step_fast, const char* format, ImGuiInputTextFlags_ flags) {
        bool changed = ImGui::InputFloat(label, &v, step, step_fast, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "step"_a = 0.f, "step_fast"_a = 0.f, "format"_a = "%.3f", "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);

    m.def("input_float2", [](const char* label, ImVec2 v, const char* format, ImGuiInputTextFlags_ flags) {
        bool changed = ImGui::InputFloat2(label, &v.x, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "format"_a = "%.3f", "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);

    m.def("input_float3", [](const char* label, Vec3 v, const char* format, ImGuiInputTextFlags_ flags) {
        bool changed = ImGui::InputFloat3(label, &v.x, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "format"_a = "%.3f", "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);

    m.def("input_float4", [](const char* label, ImVec4 v, const char* format, ImGuiInputTextFlags_ flags) {
        bool changed = ImGui::InputFloat4(label, &v.x, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "format"_a = "%.3f", "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);

    m.def("input_double", [](const char* label, double v, double step, double step_fast, const char* format, ImGuiInputTextFlags_ flags) {
        bool changed = ImGui::InputDouble(label, &v, step, step_fast, format, flags);
        return std::pair(changed, v);
    }, "label"_a, "v"_a, "step"_a = 0.0, "step_fast"_a = 0.0, "format"_a = "%.6f", "flags"_a.sig("InputTextFlags.NONE") = ImGuiInputTextFlags_None);

    // IMGUI_API bool          InputScalar(const char* label, ImGuiDataType data_type, void* p_data, const void* p_step = NULL, const void* p_step_fast = NULL, const char* format = NULL, ImGuiInputTextFlags flags = 0);
    // IMGUI_API bool          InputScalarN(const char* label, ImGuiDataType data_type, void* p_data, int components, const void* p_step = NULL, const void* p_step_fast = NULL, const char* format = NULL, ImGuiInputTextFlags flags = 0);

    // Widgets: Color Editor/Picker (tip: the ColorEdit* functions have a little color square that can be left-clicked to open a picker, and right-clicked to open an option menu.)
    m.def("color_edit3", [](const char* label, const Vec3& col, ImGuiColorEditFlags_ flags) {
        Vec3 c(col);
        bool changed = ImGui::ColorEdit3(label, &c.x, flags);
        return std::tuple(changed, c);
    }, "label"_a, "col"_a, "flags"_a.sig("ColorEditFlags.NONE") = ImGuiColorEditFlags_None);
    m.def("color_edit4", [](const char* label, const ImVec4& col, ImGuiColorEditFlags_ flags) {
        ImVec4 c(col);
        bool changed = ImGui::ColorEdit4(label, &c.x, flags);
        return std::tuple(changed, c);
    }, "label"_a, "col"_a, "flags"_a.sig("ColorEditFlags.NONE") = ImGuiColorEditFlags_None);
    m.def("color_picker3", [](const char* label, const Vec3& col, ImGuiColorEditFlags_ flags) {
        Vec3 c(col);
        bool changed = ImGui::ColorPicker3(label, &c.x, flags);
        return std::tuple(changed, c);
    }, "label"_a, "col"_a, "flags"_a.sig("ColorEditFlags.NONE") = ImGuiColorEditFlags_None);
    m.def("color_picker4", [](const char* label, const ImVec4& col, ImGuiColorEditFlags_ flags, std::optional<ImVec4> ref_col) {
        ImVec4 c(col);
        ImVec4 ref = ref_col ? ref_col.value() : ImVec4(0, 1, 0, 0);
        bool changed = ImGui::ColorPicker4(label, &c.x, flags, ref_col ? &ref.x : nullptr);
        return std::tuple(changed, c);
    }, "label"_a, "col"_a, "flags"_a.sig("ColorEditFlags.NONE") = ImGuiColorEditFlags_None, "ref_col"_a = nb::none());
    m.def("color_button", [](const char* desc_id, const ImVec4& col, ImGuiColorEditFlags_ flags, const ImVec2& size) {
        return ImGui::ColorButton(desc_id, col, flags, size);
    }, "desc_id"_a, "col"_a, "flags"_a.sig("ColorEditFlags.NONE") = ImGuiColorEditFlags_None, "size"_a = ImVec2(0, 0));
    m.def("set_color_edit_options", [](ImGuiColorEditFlags_ flags) { ImGui::SetColorEditOptions(flags); }, "flags"_a);

    // Tables
    m.def("begin_table", [](const char *str_id, int column, ImGuiTableFlags_ flags, const ImVec2 &outer_size, float inner_width) {
        return ImGui::BeginTable(str_id, column, flags, outer_size, inner_width);
    }, "str_id"_a, "column"_a, "flags"_a.sig("TableFlags.NONE") = ImGuiTableFlags_None, "outer_size"_a = ImVec2(0.f, 0.f), "inner_width"_a = 0.0f);
    // table_next_row (manual: .sig() for flags)
    m.def("table_next_row", [](ImGuiTableRowFlags_ row_flags, float min_row_height) {
        ImGui::TableNextRow(row_flags, min_row_height);
    }, "flags"_a.sig("TableRowFlags.NONE") = ImGuiTableRowFlags_None, "min_row_height"_a = 0.0f);

    // Tables: Headers & Columns declaration
    m.def("table_setup_column", [](const char *label, ImGuiTableColumnFlags_ flags, float init_width_or_weight, ImGuiID user_id) {
        ImGui::TableSetupColumn(label, flags, init_width_or_weight, user_id);
    }, "label"_a, "flags"_a.sig("TableColumnFlags.NONE") = ImGuiTableColumnFlags_None, "init_width_or_weight"_a = 0.f, "user_id"_a = 0);
    m.def("table_angled_headers_row", &ImGui::TableAngledHeadersRow);

    // Tables: Sorting & Miscellaneous functions
    m.def("table_get_column_name", [](int column_n) { return nb::str(ImGui::TableGetColumnName(column_n)); }, "column_n"_a = -1);
    m.def("table_get_column_flags", [](int column_n) { return (ImGuiTableColumnFlags_)ImGui::TableGetColumnFlags(column_n); }, "column_n"_a = -1);
    m.def("table_get_hovered_column", &ImGui::TableGetHoveredColumn);
    m.def("table_set_bg_color", [](ImGuiTableBgTarget_ target, const ImVec4& col, int column_n) {
        ImGui::TableSetBgColor(target, ImGui::ColorConvertFloat4ToU32(col), column_n);
    }, "target"_a, "color"_a, "column_n"_a = -1);

    // Legacy Columns API (prefer using Tables!)
    // - You can also use SameLine(pos_x) to mimic simplified columns.
    m.def("columns", [](int count, std::optional<std::string> id, bool border) {
        return ImGui::Columns(count, id ? id.value().c_str() : nullptr, border);
    }, "count"_a = 1, "id"_a = nb::none(), "border"_a = true);
    m.def("next_column", &ImGui::NextColumn);
    m.def("get_column_index", &ImGui::GetColumnIndex);
    m.def("get_column_width", &ImGui::GetColumnWidth, "column_index"_a = -1);
    m.def("set_column_width", &ImGui::SetColumnWidth, "column_index"_a, "width"_a);
    m.def("get_column_offset", &ImGui::GetColumnOffset, "column_index"_a = -1);
    m.def("set_column_offset", &ImGui::SetColumnOffset, "column_index"_a, "offset_x"_a);
    m.def("get_columns_count", &ImGui::GetColumnsCount);

    // Tab bar
    m.def("begin_tab_bar", [](const char* str_id, ImGuiTabBarFlags_ flags) {
        return ImGui::BeginTabBar(str_id, flags);
    }, "str_id"_a, "flags"_a.sig("TabBarFlags.NONE") = ImGuiTabBarFlags_None);

    m.def("begin_tab_item", [](const char* label, bool closable, ImGuiTabItemFlags_ flags) {
        bool open = true;
        bool selected = ImGui::BeginTabItem(label, closable ? &open : NULL, flags);
        return std::pair(selected, open);
    }, "str_id"_a, "closable"_a = false, "flags"_a.sig("TabItemFlags.NONE") = ImGuiTabItemFlags_None);

    m.def("tab_item_button", [](const char* label, ImGuiTabItemFlags_ flags) {
        return ImGui::TabItemButton(label, flags);
    }, "label"_a, "flags"_a.sig("TabItemFlags.NONE") = ImGuiTabItemFlags_None);
    m.def("set_tab_item_closed", &ImGui::SetTabItemClosed, "label"_a);

    // Logging/Capture
    m.def("log_to_tty", &ImGui::LogToTTY, "auto_open_depth"_a = -1);
    m.def("log_to_file", &ImGui::LogToFile, "auto_open_depth"_a = -1, "filename"_a = nullptr);
    m.def("log_to_clipboard", &ImGui::LogToClipboard, "auto_open_depth"_a = -1);
    m.def("log_finish", &ImGui::LogFinish);
    m.def("log_buttons", &ImGui::LogButtons);
    m.def("log_text", [](const char* text) { ImGui::LogText("%s", text); }, "text"_a);

    // Drag and Drop
    // Note: Accept* and Get* are members of Context.
    m.def("begin_drag_drop_source", [](ImGuiDragDropFlags_ flags) { return ImGui::BeginDragDropSource(flags); }, "flags"_a.sig("DragDropFlags.NONE") = ImGuiDragDropFlags_None);
    m.def("set_drag_drop_payload", [](const char* type, nb::bytes data, ImGuiCond_ cond) {
        return ImGui::SetDragDropPayload(type, data.data(), data.size(), cond);
    }, "type"_a, "data"_a, "cond"_a.sig("Cond.NONE") = ImGuiCond_None);

    // Disabling [BETA API]
    m.def("begin_disabled", &ImGui::BeginDisabled, "disabled"_a = true);

    // Clipping
    // - Mouse hovering is affected by ImGui::PushClipRect() calls, unlike direct calls to ImDrawList::PushClipRect() which are render only.
    m.def("push_clip_rect", &ImGui::PushClipRect, "clip_rect_min"_a, "clip_rect_max"_a, "intersect_with_current_clip_rect"_a);
    m.def("pop_clip_rect", &ImGui::PopClipRect);

    // // Focus, Activation

    // Keyboard/Gamepad Navigation
    m.def("set_nav_cursor_visible", &ImGui::SetNavCursorVisible, "visible"_a);

    // Overlapping mode

    // Item/Widgets Utilities and Query Functions
    m.def("is_item_hovered", [](ImGuiHoveredFlags_ flags) {
        return ImGui::IsItemHovered(flags);
    }, "flags"_a.sig("HoveredFlags.NONE") = ImGuiHoveredFlags_None);
    m.def("is_item_clicked", [](ImGuiMouseButton_ mouse_button) {
        return ImGui::IsItemClicked(mouse_button);
    }, "mouse_button"_a.sig("MouseButton.LEFT") = ImGuiMouseButton_Left);

    // Miscellaneous Utilities
    m.def("is_rect_visible", [](const ImVec2& size) {
        return ImGui::IsRectVisible(size);
    }, "size"_a);
    m.def("is_rect_visible", [](const ImVec2& rect_min, const ImVec2& rect_max) {
        return ImGui::IsRectVisible(rect_min, rect_max);
    }, "rect_min"_a, "rect_max"_a);
    // IMGUI_API ImDrawListSharedData* GetDrawListSharedData();                                    // you may use this when creating your own ImDrawList instances.
    m.def("get_style_color_name", [](ImGuiCol_ idx) { return ImGui::GetStyleColorName(idx); }, "col"_a);
    // IMGUI_API void          SetStateStorage(ImGuiStorage* storage);                             // replace current window storage with our own (if you want to manipulate it yourself, typically clear subsection of it)
    // IMGUI_API ImGuiStorage* GetStateStorage();

    // Text Utilities
    m.def("calc_text_size", [](const char* text, bool hide_text_after_double_hash, float wrap_width) {
        return ImGui::CalcTextSize(text, nullptr, hide_text_after_double_hash, wrap_width);
    }, "text"_a, "hide_text_after_double_hash"_a = false, "wrap_width"_a = -1.0f);

    // Color utilities
    m.def("color_convert_u32_to_float4", &ImGui::ColorConvertU32ToFloat4);
    m.def("color_convert_float4_to_u32", &ImGui::ColorConvertFloat4ToU32);
    m.def("color_convert_hsv_to_rgb", [](const ImVec4& hsv) {
        ImVec4 rgb(hsv);
        ImGui::ColorConvertHSVtoRGB(hsv.x, hsv.y, hsv.z, rgb.x, rgb.y, rgb.z);
        return rgb;
    }, "hsv"_a);
    m.def("color_convert_rgb_to_hsv", [](const ImVec4& rgba) {
        ImVec4 hsv(rgba);
        ImGui::ColorConvertHSVtoRGB(rgba.x, rgba.y, rgba.z, hsv.x, hsv.y, hsv.z);
        return hsv;
    }, "rgba"_a);

    // Inputs Utilities: Keyboard/Mouse/Gamepad
    m.def("is_key_down", [](ImGuiKey key) { return ImGui::IsKeyDown(key); }, "key"_a);
    m.def("is_key_pressed", [](ImGuiKey key, bool repeat) { return ImGui::IsKeyPressed(key, repeat); }, "key"_a, "repeat"_a = true);
    m.def("is_key_released", [](ImGuiKey key) { return ImGui::IsKeyReleased(key); }, "key"_a);
    m.def("is_key_chord_pressed", [](std::variant<ImGuiKey, int> key) { return ImGui::IsKeyChordPressed(variant_to_int(key)); }, "key_chord"_a);
    m.def("get_key_pressed_amount", &ImGui::GetKeyPressedAmount, "key"_a, "repeat_delay"_a, "rate"_a);
    m.def("get_key_name", &ImGui::GetKeyName, "key"_a);
    m.def("set_next_frame_want_capture_keyboard", &ImGui::SetNextFrameWantCaptureKeyboard, "want_capture_keyboard"_a);

    // Inputs Utilities: Shortcut Testing & Routing [BETA]
    // - ImGuiKeyChord = a ImGuiKey + optional ImGuiMod_Alt/ImGuiMod_Ctrl/ImGuiMod_Shift/ImGuiMod_Super.
    // NOTE: bindings code models 'ImGuiKeyChord' as `Key | int`.  Not sure what'd be a better way to
    // model it in python types.
    m.def("shortcut", [](std::variant<ImGuiKey, int> key_chord, ImGuiInputFlags_ flags) {
        return ImGui::Shortcut(variant_to_int(key_chord), flags);
    }, "key_chord"_a, "flags"_a.sig("InputFlags.NONE") = ImGuiInputFlags_None,
    "Python bindings note: The original ImGui type for a ImGuiKeyChord is basically ImGuiKey that can be optionally bitwise-OR'd with a modifier key like ImGuiMod_Alt, ImGuiMod_Ctrl, etc.  In Python, this is modeled as a union of `Key` and int.  The int value is the modifier key.  You can use the `|` operator to combine them, e.g. `Key.A | Key.MOD_CTRL`.");
    m.def("set_next_item_shortcut", [](std::variant<ImGuiKey, int> key_chord, ImGuiInputFlags_ flags) {
        return ImGui::SetNextItemShortcut(variant_to_int(key_chord), flags);
    }, "key_chord"_a, "flags"_a.sig("InputFlags.NONE") = ImGuiInputFlags_None,
    "Python bindings note: The original ImGui type for a ImGuiKeyChord is basically ImGuiKey that can be optionally bitwise-OR'd with a modifier key like ImGuiMod_Alt, ImGuiMod_Ctrl, etc.  In Python, this is modeled as a union of `Key` and int.  The int value is the modifier key.  You can use the `|` operator to combine them, e.g. `Key.A | Key.MOD_CTRL`.");

    m.def("set_item_key_owner", [](ImGuiKey key) { ImGui::SetItemKeyOwner(key); }, "key"_a, "Set key owner to last item ID if it is hovered or active.");

    // Input Utilities: Mouse
    m.def("is_mouse_down", [](ImGuiMouseButton_ button) { return ImGui::IsMouseDown(button); }, "button"_a);
    m.def("is_mouse_clicked", [](ImGuiMouseButton_ button, bool repeat) { return ImGui::IsMouseClicked(button, repeat); }, "button"_a, "repeat"_a = false);
    m.def("is_mouse_released", [](ImGuiMouseButton_ button) { return ImGui::IsMouseReleased(button); }, "button"_a);
    m.def("is_mouse_double_clicked", [](ImGuiMouseButton_ button) { return ImGui::IsMouseDoubleClicked(button); }, "button"_a);
    m.def("is_mouse_released_with_delay", [](ImGuiMouseButton_ button, float delay) { return ImGui::IsMouseReleasedWithDelay(button, delay); }, "button"_a, "delay"_a);
    m.def("get_mouse_clicked_count", [](ImGuiMouseButton_ button) { return ImGui::GetMouseClickedCount(button); }, "button"_a);
    m.def("is_mouse_pos_valid", [](std::optional<ImVec2> mouse_pos) {
        if (mouse_pos) {
            ImVec2 v = mouse_pos.value();
            return ImGui::IsMousePosValid(&v);
        }
        return ImGui::IsMousePosValid(NULL);
    }, "mouse_pos"_a.none() = std::nullopt);
    m.def("is_mouse_dragging", [](ImGuiMouseButton_ button, float lock_threshold) {
        return ImGui::IsMouseDragging(button, lock_threshold);
    }, "button"_a, "lock_threshold"_a = -1.0f);
    m.def("get_mouse_drag_delta", [](ImGuiMouseButton_ button, float lock_threshold) {
        return ImGui::GetMouseDragDelta(button, lock_threshold);
    }, "button"_a.sig("MouseButton.LEFT") = ImGuiMouseButton_Left, "lock_threshold"_a = -1.0f);
    m.def("reset_mouse_drag_delta", [](ImGuiMouseButton_ button) {
        return ImGui::ResetMouseDragDelta(button);
    }, "button"_a.sig("MouseButton.LEFT") = ImGuiMouseButton_Left);
    m.def("get_mouse_cursor", []() { return (ImGuiMouseCursor_)ImGui::GetMouseCursor(); });
    m.def("set_mouse_cursor", [](ImGuiMouseCursor_ cursor_type) { ImGui::SetMouseCursor(cursor_type); }, "cursor_type"_a);
    // set_next_frame_want_capture_mouse (manual: uses "capture" param name for API compat)
    m.def("set_next_frame_want_capture_mouse", &ImGui::SetNextFrameWantCaptureMouse, "capture"_a);

    // Value() helpers
    m.def("value", [](const char* prefix, bool b) { ImGui::Value(prefix, b); }, "prefix"_a, "b"_a);
    m.def("value", [](const char* prefix, int v) { ImGui::Value(prefix, v); }, "prefix"_a, "v"_a);
    m.def("value", [](const char* prefix, float v, std::optional<const char*> float_format) {
        ImGui::Value(prefix, v, float_format ? float_format.value() : nullptr);
    }, "prefix"_a, "v"_a, "float_format"_a = nb::none());

    // Settings/.Ini Utilities
    m.def("load_ini_settings_from_memory", [](const char* ini_data) {
        ImGui::LoadIniSettingsFromMemory(ini_data, 0);
    }, "ini_data"_a);
    m.def("save_ini_settings_to_memory", []() {
        return std::string(ImGui::SaveIniSettingsToMemory());
    });
}
