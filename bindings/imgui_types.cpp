// imgui 类型绑定（nb::class_ 部分），由 slimgui_ext.cpp 拆分而来。
#include "imgui_common.h"

void register_imgui_types(nb::module_& m) {
    nb::class_<ImFont>(m, "Font")
        .def_ro("legacy_size", &ImFont::LegacySize);

    nb::class_<ImFontConfig>(m, "FontConfig") // exposes only safe fields, e.g., no FontData, FontDataOwnedByAtlas, etc.
        .def(nb::init<>())
        .def_rw("font_no", &ImFontConfig::FontNo)
        .def_rw("size_pixels", &ImFontConfig::SizePixels)
        .def_rw("oversample_h", &ImFontConfig::OversampleH)
        .def_rw("oversample_v", &ImFontConfig::OversampleV)
        .def_rw("pixel_snap_h", &ImFontConfig::PixelSnapH)
        .def_rw("pixel_snap_v", &ImFontConfig::PixelSnapV)
        .def_rw("glyph_offset", &ImFontConfig::GlyphOffset)
        .def_rw("glyph_min_advance_x", &ImFontConfig::GlyphMinAdvanceX)
        .def_rw("glyph_max_advance_x", &ImFontConfig::GlyphMaxAdvanceX)
        .def_rw("merge_mode", &ImFontConfig::MergeMode)
        .def_rw("font_loader_flags", &ImFontConfig::FontLoaderFlags)
        .def_rw("rasterizer_multiply", &ImFontConfig::RasterizerMultiply)
        .def_rw("rasterizer_density", &ImFontConfig::RasterizerDensity)
        .def_rw("ellipsis_char", &ImFontConfig::EllipsisChar);

    nb::class_<ImFontAtlas>(m, "FontAtlas")
        .def("add_font_default", &ImFontAtlas::AddFontDefault, nb::arg("font_cfg").none() = nullptr, nb::rv_policy::reference_internal)
        .def("add_font_from_memory_ttf", [](ImFontAtlas* fonts, nb::bytes font_data, float size_pixels, std::optional<ImFontConfig> font_cfg) {
            ImFontConfig cfg;
            if (font_cfg) {
                cfg = font_cfg.value();
            }
            // Copy font data, let imgui delete it after building.  Without the copy, Python
            // might deallocate the bytes buffer before the font atlas gets built.
            cfg.FontDataOwnedByAtlas = true;
            void* data = IM_ALLOC(font_data.size());
            memcpy(data, font_data.c_str(), font_data.size());
            return fonts->AddFontFromMemoryTTF(data, font_data.size(), size_pixels, &cfg, nullptr);
        }, nb::rv_policy::reference_internal, "font_data"_a, "size_pixels"_a = 0.f, nb::arg("font_cfg").none() = std::nullopt)
        .def("clear_tex_data", &ImFontAtlas::ClearTexData)
        .def("get_tex_data_as_rgba32", [](ImFontAtlas* fonts) {
            int tex_w, tex_h;
            unsigned char* tex_pixels = nullptr;
            fonts->GetTexDataAsRGBA32(&tex_pixels, &tex_w, &tex_h);
            return std::tuple(tex_w, tex_h, nb::bytes(tex_pixels, tex_w*tex_h*4));
        })
        .def_prop_rw("texture_id",
            [](ImFontAtlas& a) { return a.TexRef.GetTexID(); },
            [](ImFontAtlas& a, ImU64 texID) { a.TexRef = ImTextureRef((ImTextureID)texID); }
        );

    nb::class_<ImTextureRef>(m, "TextureRef")
        .def("get_tex_id", &ImTextureRef::GetTexID);

    // TODO incomplete
    nb::class_<ImGuiViewport>(m, "Viewport")
        .def_rw("pos", &ImGuiViewport::Pos)
        .def_rw("size", &ImGuiViewport::Size)
        .def_rw("work_pos", &ImGuiViewport::WorkPos)
        .def_rw("work_size", &ImGuiViewport::WorkSize)
        .def("get_center", &ImGuiViewport::GetCenter)
        .def("get_work_center", &ImGuiViewport::GetWorkCenter);

    // ColorsArray is just a way of providing mutable list access to
    // the Colors array in ImGuiStyle.
    struct ColorsArray {
        ImVec4* data;
        ColorsArray(ImVec4* colors) : data(colors) {}
    };
    nb::class_<ColorsArray>(m, "ColorsArray")
        .def("__getitem__", [](const ColorsArray& self, ImGuiCol_ index) {
            return self.data[index];
        })
        .def("__setitem__", [](ColorsArray& self, ImGuiCol_ index, ImVec4 value) {
            self.data[index] = value;
        })
        .def("__iter__", [](const ColorsArray& self) {
            // TODO weird why 'slimgui_ext.' is required here.  Some missing setup in this class binding?
            return nb::make_iterator(nb::type<ImVec4>(), "slimgui_ext.imgui.ColorsArrayIterator", self.data, self.data + (size_t)ImGuiCol_COUNT);
        }, nb::keep_alive<0, 1>())
        .def("__len__", [](const ColorsArray& self) {
            return (size_t)ImGuiCol_COUNT;
        });

    nb::class_<ImGuiStyle>(m, "Style")
        .def_ro("font_size_base", &ImGuiStyle::FontSizeBase, "Current base font size before external global factors are applied. Use `imgui.push_font(None, size)` to modify. Use `imgui.get_font_size()` to obtain scaled value.")
        .def_rw("font_scale_main", &ImGuiStyle::FontScaleMain, "Main global scale factor. May be set by application once, or exposed to end-user.")
        .def_ro("font_scale_dpi", &ImGuiStyle::FontScaleDpi, "Additional global scale factor from viewport/monitor contents scale. When `io.config_dpi_scale_fonts` is enabled, this is automatically overwritten when changing monitor DPI.")
        .def_rw("alpha", &ImGuiStyle::Alpha)
        .def_rw("disabled_alpha", &ImGuiStyle::DisabledAlpha)
        .def_rw("window_padding", &ImGuiStyle::WindowPadding)
        .def_rw("window_rounding", &ImGuiStyle::WindowRounding)
        .def_rw("window_border_size", &ImGuiStyle::WindowBorderSize)
        .def_rw("window_min_size", &ImGuiStyle::WindowMinSize)
        .def_rw("window_title_align", &ImGuiStyle::WindowTitleAlign)
        .def_rw("window_menu_button_position", &ImGuiStyle::WindowMenuButtonPosition)
        .def_rw("child_rounding", &ImGuiStyle::ChildRounding)
        .def_rw("child_border_size", &ImGuiStyle::ChildBorderSize)
        .def_rw("popup_rounding", &ImGuiStyle::PopupRounding)
        .def_rw("popup_border_size", &ImGuiStyle::PopupBorderSize)
        .def_rw("frame_padding", &ImGuiStyle::FramePadding)
        .def_rw("frame_rounding", &ImGuiStyle::FrameRounding)
        .def_rw("frame_border_size", &ImGuiStyle::FrameBorderSize)
        .def_rw("item_spacing", &ImGuiStyle::ItemSpacing)
        .def_rw("item_inner_spacing", &ImGuiStyle::ItemInnerSpacing)
        .def_rw("cell_padding", &ImGuiStyle::CellPadding)
        .def_rw("touch_extra_padding", &ImGuiStyle::TouchExtraPadding)
        .def_rw("indent_spacing", &ImGuiStyle::IndentSpacing)
        .def_rw("columns_min_spacing", &ImGuiStyle::ColumnsMinSpacing)
        .def_rw("scrollbar_size", &ImGuiStyle::ScrollbarSize)
        .def_rw("scrollbar_rounding", &ImGuiStyle::ScrollbarRounding)
        .def_rw("grab_min_size", &ImGuiStyle::GrabMinSize)
        .def_rw("grab_rounding", &ImGuiStyle::GrabRounding)
        .def_rw("log_slider_deadzone", &ImGuiStyle::LogSliderDeadzone)
        .def_rw("tab_rounding", &ImGuiStyle::TabRounding)
        .def_rw("tab_border_size", &ImGuiStyle::TabBorderSize)
        .def_rw("tab_close_button_min_width_selected", &ImGuiStyle::TabCloseButtonMinWidthSelected)
        .def_rw("tab_close_button_min_width_unselected", &ImGuiStyle::TabCloseButtonMinWidthUnselected)
        .def_rw("tab_bar_border_size", &ImGuiStyle::TabBarBorderSize)
        .def_rw("table_angled_headers_angle", &ImGuiStyle::TableAngledHeadersAngle)
        .def_rw("color_button_position", &ImGuiStyle::ColorButtonPosition)
        .def_rw("button_text_align", &ImGuiStyle::ButtonTextAlign)
        .def_rw("selectable_text_align", &ImGuiStyle::SelectableTextAlign)
        .def_rw("separator_text_border_size", &ImGuiStyle::SeparatorTextBorderSize)
        .def_rw("separator_text_align", &ImGuiStyle::SeparatorTextAlign)
        .def_rw("separator_text_padding", &ImGuiStyle::SeparatorTextPadding)
        .def_rw("display_window_padding", &ImGuiStyle::DisplayWindowPadding)
        .def_rw("display_safe_area_padding", &ImGuiStyle::DisplaySafeAreaPadding)
        .def_rw("mouse_cursor_scale", &ImGuiStyle::MouseCursorScale)
        .def_rw("anti_aliased_lines", &ImGuiStyle::AntiAliasedLines)
        .def_rw("anti_aliased_lines_use_tex", &ImGuiStyle::AntiAliasedLinesUseTex)
        .def_rw("anti_aliased_fill", &ImGuiStyle::AntiAliasedFill)
        .def_rw("curve_tessellation_tol", &ImGuiStyle::CurveTessellationTol)
        .def_rw("circle_tessellation_max_error", &ImGuiStyle::CircleTessellationMaxError)
        .def_prop_ro("colors", [](ImGuiStyle* style) -> ColorsArray { return ColorsArray(style->Colors); }, nb::rv_policy::reference_internal)
        .def_rw("hover_stationary_delay", &ImGuiStyle::HoverStationaryDelay)
        .def_rw("hover_delay_short", &ImGuiStyle::HoverDelayShort)
        .def_rw("hover_delay_normal", &ImGuiStyle::HoverDelayNormal)
        .def_rw("hover_flags_for_tooltip_mouse", &ImGuiStyle::HoverFlagsForTooltipMouse)
        .def_rw("hover_flags_for_tooltip_nav", &ImGuiStyle::HoverFlagsForTooltipNav)
        .def("scale_all_sizes", &ImGuiStyle::ScaleAllSizes, "scale_factor"_a);

    nb::class_<ImGuiIO>(m, "IO")
        .def("add_mouse_pos_event", &ImGuiIO::AddMousePosEvent, "x"_a, "y"_a)
        .def("add_mouse_button_event", &ImGuiIO::AddMouseButtonEvent, "button"_a, "down"_a)
        .def("add_mouse_wheel_event", &ImGuiIO::AddMouseWheelEvent, "wheel_x"_a, "wheel_y"_a)
        .def("add_input_character", &ImGuiIO::AddInputCharacter, "c"_a)
        .def("add_key_event", &ImGuiIO::AddKeyEvent, "key"_a, "down"_a)
        .def("add_focus_event", &ImGuiIO::AddFocusEvent, "focused"_a, "Queue a gain/loss of focus for the application (generally based on OS/platform focus of your window).")
        .def("add_input_characters_utf8", &ImGuiIO::AddInputCharactersUTF8, "str"_a, "Queue a new characters input from a UTF-8 string.")
        .def("add_key_analog_event", &ImGuiIO::AddKeyAnalogEvent, "key"_a, "down"_a, "v"_a, "Queue a new key down/up event for analog values (e.g. `Key.KEY_GAMEPAD_*` values). Dead-zones should be handled by the backend.")
        .def("add_mouse_source_event", &ImGuiIO::AddMouseSourceEvent, "source"_a, "Queue a mouse source change (Mouse/TouchScreen/Pen).")
        .def("set_app_accepting_events", &ImGuiIO::SetAppAcceptingEvents, "accepting_events"_a, "Set master flag for accepting key/mouse/text events (default to true).  Useful if you have native dialog boxes that are interrupting your application loop/refresh, and you want to disable events being queued while your app is frozen.")
        .def("clear_events_queue", &ImGuiIO::ClearEventsQueue, "Clear all incoming events.")
        .def("clear_input_keys", &ImGuiIO::ClearInputKeys, "Clear current keyboard/gamepad state + current frame text input buffer.  Equivalent to releasing all keys/buttons.")
        .def("clear_input_mouse", &ImGuiIO::ClearInputMouse, "Clear current mouse state.")
        .def_prop_rw("config_flags",
            [](ImGuiIO& io) { return (ImGuiConfigFlags_)io.ConfigFlags; },
            [](ImGuiIO& io, ImGuiConfigFlags_ flags) { io.ConfigFlags = flags; }
        )
        .def_prop_rw("backend_flags",
            [](ImGuiIO& io) { return (ImGuiBackendFlags_)io.BackendFlags; },
            [](ImGuiIO& io, ImGuiBackendFlags_ flags) { io.BackendFlags = flags; }
        )
        .def_rw("display_size", &ImGuiIO::DisplaySize)
        .def_rw("display_framebuffer_scale", &ImGuiIO::DisplayFramebufferScale)
        .def_rw("delta_time", &ImGuiIO::DeltaTime)
        .def_rw("ini_saving_rate", &ImGuiIO::IniSavingRate)
        .def_prop_rw("ini_filename",
            [](ImGuiIO& io) { return io.IniFilename; },
            [](ImGuiIO& io, nb::handle filename) {
                // TODO what about the lifetime of io.IniFilename?
                // Note: maybe it works with the wrapper business in https://github.com/nurpax/slimgui/issues/1?
                const char* fname = !filename.is_none() ? nb::cast<const char *>(filename) : nullptr;
                io.IniFilename = fname;
            },
            "ini_filename"_a.none(),
            nb::for_getter(nb::sig("def ini_filename(self, /) -> str | None")),
            nb::for_setter(nb::sig("def ini_filename(self, filename: str | None, /) -> None"))
        )
        .def_prop_rw("log_filename",
            [](ImGuiIO& io) { return io.LogFilename; },
            [](ImGuiIO& io, nb::handle filename) {
                const char* fname = !filename.is_none() ? nb::cast<const char *>(filename) : nullptr;
                io.LogFilename = fname;
            },
            "log_filename"_a.none(),
            nb::for_getter(nb::sig("def log_filename(self, /) -> str | None")),
            nb::for_setter(nb::sig("def log_filename(self, filename: str | None, /) -> None"))
        )
        .def_rw("fonts", &ImGuiIO::Fonts, nb::rv_policy::reference_internal)

        .def_rw("config_nav_swap_gamepad_buttons", &ImGuiIO::ConfigNavSwapGamepadButtons)
        .def_rw("config_nav_move_set_mouse_pos", &ImGuiIO::ConfigNavMoveSetMousePos)
        .def_rw("config_nav_capture_keyboard", &ImGuiIO::ConfigNavCaptureKeyboard)
        .def_rw("config_nav_escape_clear_focus_item", &ImGuiIO::ConfigNavEscapeClearFocusItem)
        .def_rw("config_nav_escape_clear_focus_window", &ImGuiIO::ConfigNavEscapeClearFocusWindow)
        .def_rw("config_nav_cursor_visible_auto", &ImGuiIO::ConfigNavCursorVisibleAuto)
        .def_rw("config_nav_cursor_visible_always", &ImGuiIO::ConfigNavCursorVisibleAlways)

        .def_rw("mouse_draw_cursor", &ImGuiIO::MouseDrawCursor)
        .def_rw("config_mac_osx_behaviors", &ImGuiIO::ConfigMacOSXBehaviors)
        .def_rw("config_input_trickle_event_queue", &ImGuiIO::ConfigInputTrickleEventQueue)
        .def_rw("config_input_text_cursor_blink", &ImGuiIO::ConfigInputTextCursorBlink)
        .def_rw("config_input_text_enter_keep_active", &ImGuiIO::ConfigInputTextEnterKeepActive)
        .def_rw("config_drag_click_to_input_text", &ImGuiIO::ConfigDragClickToInputText)
        .def_rw("config_windows_resize_from_edges", &ImGuiIO::ConfigWindowsResizeFromEdges)
        .def_rw("config_windows_move_from_title_bar_only", &ImGuiIO::ConfigWindowsMoveFromTitleBarOnly)
        .def_rw("config_windows_copy_contents_with_ctrl_c", &ImGuiIO::ConfigWindowsCopyContentsWithCtrlC)
        .def_rw("config_scrollbar_scroll_by_page", &ImGuiIO::ConfigScrollbarScrollByPage)
        .def_rw("config_memory_compact_timer", &ImGuiIO::ConfigMemoryCompactTimer)
        .def_rw("mouse_double_click_time", &ImGuiIO::MouseDoubleClickTime)
        .def_rw("mouse_double_click_max_dist", &ImGuiIO::MouseDoubleClickMaxDist)
        .def_rw("mouse_drag_threshold", &ImGuiIO::MouseDragThreshold)
        .def_rw("key_repeat_delay", &ImGuiIO::KeyRepeatDelay)
        .def_rw("key_repeat_rate", &ImGuiIO::KeyRepeatRate)

        .def_rw("config_error_recovery", &ImGuiIO::ConfigErrorRecovery)
        .def_rw("config_error_recovery_enable_assert", &ImGuiIO::ConfigErrorRecoveryEnableAssert)
        .def_rw("config_error_recovery_enable_debug_log", &ImGuiIO::ConfigErrorRecoveryEnableDebugLog)
        .def_rw("config_error_recovery_enable_tooltip", &ImGuiIO::ConfigErrorRecoveryEnableTooltip)

        .def_rw("config_debug_is_debugger_present", &ImGuiIO::ConfigDebugIsDebuggerPresent)
        .def_rw("config_debug_highlight_id_conflicts", &ImGuiIO::ConfigDebugHighlightIdConflicts)
        .def_rw("config_debug_highlight_id_conflicts_show_item_picker", &ImGuiIO::ConfigDebugHighlightIdConflictsShowItemPicker)
        .def_rw("config_debug_begin_return_value_once", &ImGuiIO::ConfigDebugBeginReturnValueOnce)
        .def_rw("config_debug_begin_return_value_loop", &ImGuiIO::ConfigDebugBeginReturnValueLoop)
        .def_rw("config_debug_ignore_focus_loss", &ImGuiIO::ConfigDebugIgnoreFocusLoss)
        .def_rw("config_debug_ini_settings", &ImGuiIO::ConfigDebugIniSettings)

        .def_ro("want_capture_mouse", &ImGuiIO::WantCaptureMouse)
        .def_ro("want_capture_keyboard", &ImGuiIO::WantCaptureKeyboard)
        .def_ro("want_text_input", &ImGuiIO::WantTextInput)
        .def_ro("want_set_mouse_pos", &ImGuiIO::WantSetMousePos)
        .def_ro("want_save_ini_settings", &ImGuiIO::WantSaveIniSettings)
        .def_ro("nav_active", &ImGuiIO::NavActive)
        .def_ro("nav_visible", &ImGuiIO::NavVisible)
        .def_ro("framerate", &ImGuiIO::Framerate)
        .def_ro("metrics_render_vertices", &ImGuiIO::MetricsRenderVertices)
        .def_ro("metrics_render_indices", &ImGuiIO::MetricsRenderIndices)
        .def_ro("metrics_render_windows", &ImGuiIO::MetricsRenderWindows)
        .def_ro("metrics_active_windows", &ImGuiIO::MetricsActiveWindows)
        .def_ro("mouse_delta", &ImGuiIO::MouseDelta)
        .def_ro("mouse_pos", &ImGuiIO::MousePos)
        .def_ro("mouse_down", &ImGuiIO::MouseDown)
        .def_prop_ro("mouse_down", [](const ImGuiIO* io) {
            std::array<bool, (int)ImGuiMouseSource_COUNT> mouse_down;
            for (int i = 0; i < (int)ImGuiMouseSource_COUNT; ++i) {
                mouse_down[i] = io->MouseDown[i];
            }
            return mouse_down;
        })
        .def_ro("mouse_wheel", &ImGuiIO::MouseWheel)
        .def_ro("mouse_wheel_h", &ImGuiIO::MouseWheelH)
        .def_prop_ro("mouse_source", [](const ImGuiIO* io) {
            return (ImGuiMouseSource)io->MouseSource;
        })
        .def_ro("key_ctrl", &ImGuiIO::KeyCtrl)
        .def_ro("key_shift", &ImGuiIO::KeyShift)
        .def_ro("key_alt", &ImGuiIO::KeyAlt)
        .def_ro("key_super", &ImGuiIO::KeySuper);

    nb::class_<ImGuiPlatformImeData>(m, "PlatformImeData", "Platform IME data for io.platform_set_ime_data_fn() function.")
        .def_ro("want_visible", &ImGuiPlatformImeData::WantVisible, "A widget wants the IME to be visible.")
        .def_ro("input_pos", &ImGuiPlatformImeData::InputPos, "Position of the input cursor.")
        .def_ro("input_line_height", &ImGuiPlatformImeData::InputLineHeight, "Line height.");

    nb::class_<ImGuiSelectionRequest>(m, "SelectionRequest", "A selection request from BeginMultiSelect()/EndMultiSelect().")
        .def_ro("type", &ImGuiSelectionRequest::Type, "Request type.")
        .def_ro("selected", &ImGuiSelectionRequest::Selected, "Parameter for SetAll/SetRange (true=select, false=unselect).")
        .def_ro("range_direction", &ImGuiSelectionRequest::RangeDirection, "+1 forward, -1 backward.")
        .def_ro("range_first_item", &ImGuiSelectionRequest::RangeFirstItem, "First item for SetRange request.")
        .def_ro("range_last_item", &ImGuiSelectionRequest::RangeLastItem, "Last item for SetRange request (inclusive).");

    nb::class_<ImGuiMultiSelectIO>(m, "MultiSelectIO", "Main IO structure returned by BeginMultiSelect()/EndMultiSelect().")
        .def_prop_ro("requests", [](ImGuiMultiSelectIO* ms_io) {
            return nb::make_iterator(nb::type<ImGuiMultiSelectIO>(), "iterator", ms_io->Requests.begin(), ms_io->Requests.end());
        }, nb::keep_alive<0, 1>(), "Selection requests to process.")
        .def_rw("range_src_item", &ImGuiMultiSelectIO::RangeSrcItem, "Source item that must not be clipped.")
        .def_rw("nav_id_item", &ImGuiMultiSelectIO::NavIdItem, "Last known SetNextItemSelectionUserData() value for NavId.")
        .def_rw("nav_id_selected", &ImGuiMultiSelectIO::NavIdSelected, "Whether NavId item is currently selected.")
        .def_rw("range_src_reset", &ImGuiMultiSelectIO::RangeSrcReset, "Set before EndMultiSelect() to reset RangeSrcItem.")
        .def_ro("items_count", &ImGuiMultiSelectIO::ItemsCount, "items_count passed to BeginMultiSelect().");

    nb::class_<ImGuiSelectionBasicStorage>(m, "SelectionBasicStorage", "Optional helper to store multi-selection state.")
        .def(nb::init<>())
        .def_rw("preserve_order", &ImGuiSelectionBasicStorage::PreserveOrder)
        .def("get_adapter_index_to_storage_id", [](ImGuiSelectionBasicStorage* self) -> nb::object {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                auto* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                auto it = bd->selection_adapter_refs.find(self);
                if (it == bd->selection_adapter_refs.end()) return nb::none();
                return it->second;
            })
        .def("set_adapter_index_to_storage_id", [](ImGuiSelectionBasicStorage* self, nb::object fn) {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                auto* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (fn.is_none()) {
                    bd->selection_adapter_refs.erase(self);
                    self->AdapterIndexToStorageId = nullptr;
                    self->UserData = nullptr;
                } else {
                    bd->selection_adapter_refs[self] = fn;
                    self->UserData = fn.ptr();
                    self->AdapterIndexToStorageId = [](ImGuiSelectionBasicStorage* self, int idx) -> ImGuiID {
                        auto py_fn = nb::borrow<nb::callable>(static_cast<PyObject*>(self->UserData));
                        try {
                            return nb::cast<ImGuiID>(py_fn(idx));
                        } catch (nb::python_error& e) {
                            e.discard_as_unraisable("SelectionBasicStorage.adapter_index_to_storage_id");
                            return (ImGuiID)idx;
                        }
                    };
                }
            }, "fn"_a=nb::none())
        .def("apply_requests", &ImGuiSelectionBasicStorage::ApplyRequests, "ms_io"_a)
        .def("contains", &ImGuiSelectionBasicStorage::Contains, "id"_a)
        .def("clear", &ImGuiSelectionBasicStorage::Clear)
        .def("swap", &ImGuiSelectionBasicStorage::Swap, "other"_a)
        .def("set_item_selected", &ImGuiSelectionBasicStorage::SetItemSelected, "id"_a, "selected"_a)
        .def("get_storage_id_from_index", &ImGuiSelectionBasicStorage::GetStorageIdFromIndex, "idx"_a)
        .def_prop_ro("size", [](const ImGuiSelectionBasicStorage* self) { return self->_Storage.Data.Size; }, "Number of selected items.");

    nb::class_<ImGuiSelectionExternalStorage>(m, "SelectionExternalStorage", "Optional helper to apply multi-selection requests to existing storage.")
        .def(nb::init<>())
        .def("get_adapter_set_item_selected", [](ImGuiSelectionExternalStorage* self) -> nb::object {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                auto* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                auto it = bd->selection_adapter_refs.find(self);
                if (it == bd->selection_adapter_refs.end()) return nb::none();
                return it->second;
            })
        .def("set_adapter_set_item_selected", [](ImGuiSelectionExternalStorage* self, nb::object fn) {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                auto* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (fn.is_none()) {
                    bd->selection_adapter_refs.erase(self);
                    self->AdapterSetItemSelected = nullptr;
                    self->UserData = nullptr;
                } else {
                    bd->selection_adapter_refs[self] = fn;
                    self->UserData = fn.ptr();
                    self->AdapterSetItemSelected = [](ImGuiSelectionExternalStorage* self, int idx, bool selected) {
                        auto py_fn = nb::borrow<nb::callable>(static_cast<PyObject*>(self->UserData));
                        try {
                            py_fn(idx, selected);
                        } catch (nb::python_error& e) {
                            e.discard_as_unraisable("SelectionExternalStorage.adapter_set_item_selected");
                        }
                    };
                }
            }, "fn"_a=nb::none())
        .def("apply_requests", &ImGuiSelectionExternalStorage::ApplyRequests, "ms_io"_a);

    nb::class_<ImGuiPlatformIO>(m, "PlatformIO")
        .def_rw("renderer_texture_max_width", &ImGuiPlatformIO::Renderer_TextureMaxWidth)
        .def_rw("renderer_texture_max_height", &ImGuiPlatformIO::Renderer_TextureMaxHeight)
        .def_prop_ro("textures", [](ImGuiPlatformIO* plat_io) {
            return nb::make_iterator(nb::type<ImGuiPlatformIO>(), "iterator", plat_io->Textures.begin(), plat_io->Textures.end());
        }, nb::keep_alive<0, 1>())
        .def("_get_platform_get_clipboard_text_fn", [](ImGuiPlatformIO* plat_io) -> nb::object {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (bd->platform_get_clipboard_text_fn.is_none()) return nb::none();
                return bd->platform_get_clipboard_text_fn;
            })
        .def("_set_platform_get_clipboard_text_fn", [](ImGuiPlatformIO* plat_io, nb::object fn) {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (fn.is_none()) {
                    bd->platform_get_clipboard_text_fn = nb::none();
                    plat_io->Platform_GetClipboardTextFn = nullptr;
                } else {
                    bd->platform_get_clipboard_text_fn = fn;
                    plat_io->Platform_GetClipboardTextFn = &platform_get_clipboard_text_py_wrapper;
                }
            }, "fn"_a=nb::none())
        .def("_get_platform_set_clipboard_text_fn", [](ImGuiPlatformIO* plat_io) -> nb::object {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (bd->platform_set_clipboard_text_fn.is_none()) return nb::none();
                return bd->platform_set_clipboard_text_fn;
            })
        .def("_set_platform_set_clipboard_text_fn", [](ImGuiPlatformIO* plat_io, nb::object fn) {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (fn.is_none()) {
                    bd->platform_set_clipboard_text_fn = nb::none();
                    plat_io->Platform_SetClipboardTextFn = nullptr;
                } else {
                    bd->platform_set_clipboard_text_fn = fn;
                    plat_io->Platform_SetClipboardTextFn = &platform_set_clipboard_text_py_wrapper;
                }
            }, "fn"_a=nb::none())
        .def("_get_platform_open_in_shell_fn", [](ImGuiPlatformIO* plat_io) -> nb::object {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (bd->platform_open_in_shell_fn.is_none()) return nb::none();
                return bd->platform_open_in_shell_fn;
            })
        .def("_set_platform_open_in_shell_fn", [](ImGuiPlatformIO* plat_io, nb::object fn) {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (fn.is_none()) {
                    bd->platform_open_in_shell_fn = nb::none();
                    plat_io->Platform_OpenInShellFn = nullptr;
                } else {
                    bd->platform_open_in_shell_fn = fn;
                    plat_io->Platform_OpenInShellFn = &platform_open_in_shell_py_wrapper;
                }
            }, "fn"_a=nb::none())
        .def("_get_platform_set_ime_data_fn", [](ImGuiPlatformIO* plat_io) -> nb::object {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (bd->platform_set_ime_data_fn.is_none()) return nb::none();
                return bd->platform_set_ime_data_fn;
            })
        .def("_set_platform_set_ime_data_fn", [](ImGuiPlatformIO* plat_io, nb::object fn) {
                ImGuiIO& io = ImGui::GetIO(ImGui::GetCurrentContext());
                ContextBackendData* bd = static_cast<ContextBackendData*>(io.BackendLanguageUserData);
                if (fn.is_none()) {
                    bd->platform_set_ime_data_fn = nb::none();
                    plat_io->Platform_SetImeDataFn = nullptr;
                } else {
                    bd->platform_set_ime_data_fn = fn;
                    plat_io->Platform_SetImeDataFn = &platform_set_ime_data_py_wrapper;
                }
            }, "fn"_a=nb::none());

    nb::class_<ImTextureRect>(m, "TextureRect")
        .def_ro("x", &ImTextureRect::x, "Upper-left x-coordinate of rectangle to update")
        .def_ro("y", &ImTextureRect::y, "Upper-left y-coordinate of rectangle to update")
        .def_ro("w", &ImTextureRect::w, "Width of rectangle to update (in pixels)")
        .def_ro("h", &ImTextureRect::h, "Height of rectangle to update (in pixels)");

    nb::class_<ImTextureData>(m, "TextureData")
        .def_ro("status", &ImTextureData::Status, "`TextureStatus.OK/WANT_CREATE/WANT_UPDATES/WANT_DESTROY`. Always use `TextureData.set_status()` to modify!")
        .def_ro("format", &ImTextureData::Format, "`TextureFormat.RGBA32` (default) or `TextureFormat.ALPHA8`.")
        .def_ro("width", &ImTextureData::Width, "Texture width.")
        .def_ro("height", &ImTextureData::Height, "Texture height.")
        .def_ro("bytes_per_pixel", &ImTextureData::BytesPerPixel, "4 or 1.")
        .def_ro("unused_frames", &ImTextureData::UnusedFrames, "In order to facilitate handling `TextureData.status == TextureStatus.WANT_DESTROY` in some backends: this is a count successive frames where the texture was not used. Always `>0` when `status == WANT_DESTROY`.")
        .def_ro("ref_count", &ImTextureData::RefCount, "Number of contexts using this texture. Used during backend shutdown.")
        .def_prop_ro("updates", [](ImTextureData* texData) {
            return nb::make_iterator(nb::type<const ImDrawList*>(), "iterator", texData->Updates.begin(), texData->Updates.end());
        }, "Array of individual updates.")
        .def("get_size_in_bytes", &ImTextureData::GetSizeInBytes, "`width * height * `bytes_per_pixel`.")
        .def("get_pixels", [](ImTextureData* texData) {
            return nb::ndarray<nb::numpy, uint8_t, nb::ndim<1>>(texData->GetPixels(), { (size_t)texData->GetSizeInBytes() });
        }, nb::rv_policy::reference_internal, "Get texture data as an `ndarray`.")
        .def("get_pixels_at", [](ImTextureData* texData, int x, int y) {
            size_t total_bytes = texData->GetSizeInBytes();
            const uint8_t* pixels_start = (const uint8_t*)texData->GetPixelsAt(x, y);
            uintptr_t pixels_end = (uintptr_t)texData->GetPixels() + total_bytes;
            return nb::ndarray<nb::numpy, uint8_t, nb::ndim<1>>(texData->GetPixelsAt(x, y), { pixels_end - (uintptr_t)pixels_start });
        }, nb::rv_policy::reference_internal, "Get texture data as an `ndarray` starting at `x, y` corner.  Note that the pixel stride is the same as in the original texture.")
        .def("get_tex_id", &ImTextureData::GetTexID, "Backend-specific texture identifier.")
        .def("set_tex_id", &ImTextureData::SetTexID, "Call after creating or destroying the texture.")
        .def("set_status", &ImTextureData::SetStatus, "Call after honoring a request. Never modify `TextureData.status` directly!");

    nb::class_<ImGuiSizeCallbackData>(m, "SizeCallbackData", "Callback data for SetNextWindowSizeConstraints().")
        .def_prop_ro("pos", [](const ImGuiSizeCallbackData* d) { return d->Pos; }, "Window position, for reference.")
        .def_prop_ro("current_size", [](const ImGuiSizeCallbackData* d) { return d->CurrentSize; }, "Current window size.")
        .def_prop_rw("desired_size",
            [](const ImGuiSizeCallbackData* d) { return d->DesiredSize; },
            [](ImGuiSizeCallbackData* d, ImVec2 v) { d->DesiredSize = v; },
            "Desired size, based on mouse position. Write to this field to restrain resizing.");

    nb::class_<ImGuiInputTextCallbackData>(m, "InputTextCallbackData", "Shared state of InputText() when using custom callback.")
        .def_prop_ro("event_flag", [](const ImGuiInputTextCallbackData* d) { return (ImGuiInputTextFlags_)d->EventFlag; }, "One of ImGuiInputTextFlags_Callback* indicating which event triggered the callback.")
        .def_prop_ro("flags", [](const ImGuiInputTextCallbackData* d) { return (ImGuiInputTextFlags_)d->Flags; }, "What user passed to InputText().")
        .def_prop_rw("event_char",
            [](const ImGuiInputTextCallbackData* d) -> int { return (int)d->EventChar; },
            [](ImGuiInputTextCallbackData* d, int c) { d->EventChar = (ImWchar)c; },
            "Character input. Read-write. Replace character with another one, or set to zero to drop. (For CallbackCharFilter)")
        .def_prop_ro("event_key", [](const ImGuiInputTextCallbackData* d) { return d->EventKey; }, "Key pressed (Up/Down/TAB). Read-only. (For CallbackCompletion/CallbackHistory)")
        .def_prop_ro("buf", [](const ImGuiInputTextCallbackData* d) { return std::string(d->Buf, d->BufTextLen); }, "Current text buffer contents.")
        .def_prop_ro("buf_text_len", [](const ImGuiInputTextCallbackData* d) { return d->BufTextLen; }, "Current text length in bytes.")
        .def_prop_rw("cursor_pos",
            [](const ImGuiInputTextCallbackData* d) { return d->CursorPos; },
            [](ImGuiInputTextCallbackData* d, int v) { d->CursorPos = v; },
            "Read-write. Cursor position in bytes.")
        .def_prop_rw("selection_start",
            [](const ImGuiInputTextCallbackData* d) { return d->SelectionStart; },
            [](ImGuiInputTextCallbackData* d, int v) { d->SelectionStart = v; },
            "Read-write. Selection start in bytes.")
        .def_prop_rw("selection_end",
            [](const ImGuiInputTextCallbackData* d) { return d->SelectionEnd; },
            [](ImGuiInputTextCallbackData* d, int v) { d->SelectionEnd = v; },
            "Read-write. Selection end in bytes.")
        .def("delete_chars", &ImGuiInputTextCallbackData::DeleteChars, "pos"_a, "bytes_count"_a,
            "Delete bytes_count bytes at position pos. Resets selection.")
        .def("insert_chars", [](ImGuiInputTextCallbackData* d, int pos, const char* text) {
            d->InsertChars(pos, text);
        }, "pos"_a, "text"_a, "Insert text at position pos. Resets selection.")
        .def("select_all", &ImGuiInputTextCallbackData::SelectAll, "Select all text.")
        .def("clear_selection", &ImGuiInputTextCallbackData::ClearSelection, "Clear selection.")
        .def("has_selection", &ImGuiInputTextCallbackData::HasSelection, "Returns true if there is a selection.");

    nb::enum_<DrawListCallbackResult>(m, "DrawListCallbackResult", "Return value for `DrawCmd.run_callback()` that's used in backend renderers.")
        .value("DRAW", DrawListCallbackResult::DRAW, "No callback, backend should draw elements.")
        .value("CALLBACK", DrawListCallbackResult::CALLBACK, "Callback executed, no further processing of this command necessary.")
        .value("RESET_RENDER_STATE", DrawListCallbackResult::RESET_RENDER_STATE, "Reset render state token, backend should perform render state reset.");

    nb::class_<ImDrawCmd>(m, "DrawCmd")
        .def_ro("tex_ref", &ImDrawCmd::TexRef)
        .def_ro("clip_rect", &ImDrawCmd::ClipRect)
        .def_ro("vtx_offset", &ImDrawCmd::VtxOffset)
        .def_ro("idx_offset", &ImDrawCmd::IdxOffset)
        .def_ro("elem_count", &ImDrawCmd::ElemCount)
        .def_prop_ro("has_callback", [](const ImDrawCmd* cmd) {
            return cmd->UserCallback != nullptr;
        })
        .def_prop_ro("is_reset_render_state_callback", [](const ImDrawCmd* cmd) {
            return cmd->UserCallback == ImDrawCallback_ResetRenderState;
        })
        .def_prop_ro("callback_userdata", [](const ImDrawCmd* cmd) -> nb::object {
            nb::object userdata = nb::none();
            decode_drawlist_py_callback(cmd, nullptr, &userdata);
            return userdata;
        }, "Userdata passed to `DrawList.add_callback` (int, bytes or an arbitrary object), or None if this command has no Python callback.")
        .def_prop_ro("callback", [](const ImDrawCmd* cmd) -> nb::object {
            nb::object callable = nb::none();
            decode_drawlist_py_callback(cmd, &callable, nullptr);
            return callable;
        }, "The Python callable passed to `DrawList.add_callback`, or None if this command has no Python callback.\n"
           "Together with `callback_userdata` this lets a renderer inspect callback commands without running them.")
        .def("run_callback", [](const ImDrawCmd* cmd, ImDrawList* dl) {
            if (cmd->UserCallback) {
                if (cmd->UserCallback == ImDrawCallback_ResetRenderState) {
                    return DrawListCallbackResult::RESET_RENDER_STATE;
                }
                cmd->UserCallback(dl, cmd);
                return DrawListCallbackResult::CALLBACK;
            }
            return DrawListCallbackResult::DRAW;
        },
        "Run the callback added with `DrawList.add_callback` or do nothing if this draw command doesn't have a callback.\n"
        "Slimgui renderer backends should call this for every draw command.\n"
        "\n"
        "Returns: `DrawListCallbackResult` which the backend should always handle.  See docs for `DrawListCallbackResult`.");

    nb::class_<ImDrawList>(m, "DrawList")
        .def_prop_ro("vtx_buffer_size", [](const ImDrawList* drawList) {
            return drawList->VtxBuffer.Size;
        })
        .def_prop_ro("vtx_buffer_data", [](const ImDrawList* drawList) {
            return (uintptr_t)drawList->VtxBuffer.Data;
        })
        .def_prop_ro("idx_buffer_size", [](const ImDrawList* drawList) {
            return drawList->IdxBuffer.Size;
        })
        .def_prop_ro("idx_buffer_data", [](const ImDrawList* drawList) {
            return (uintptr_t)drawList->IdxBuffer.Data;
        })
        .def("get_render_data", [](const ImDrawList* drawList) -> nb::tuple {
            const int vtx_count = drawList->VtxBuffer.Size;
            const int idx_count = drawList->IdxBuffer.Size;
            const int cmd_count = drawList->CmdBuffer.Size;
            const ImDrawVert* vtx_src = drawList->VtxBuffer.Data;
            const ImDrawIdx*  idx_src = drawList->IdxBuffer.Data;
            const ImDrawCmd*  cmd_src = drawList->CmdBuffer.Data;

            // --- 顶点数据: 拆分 AoS → SoA ---
            float*    pos_data = new float[vtx_count * 2];
            float*    uv_data  = new float[vtx_count * 2];
            uint8_t*  col_data = new uint8_t[vtx_count * 4];
            for (int i = 0; i < vtx_count; i++) {
                pos_data[i * 2]     = vtx_src[i].pos.x;
                pos_data[i * 2 + 1] = vtx_src[i].pos.y;
                uv_data[i * 2]      = vtx_src[i].uv.x;
                uv_data[i * 2 + 1]  = vtx_src[i].uv.y;
                uint32_t c = vtx_src[i].col;
                col_data[i * 4]     = (uint8_t)(c);
                col_data[i * 4 + 1] = (uint8_t)(c >> 8);
                col_data[i * 4 + 2] = (uint8_t)(c >> 16);
                col_data[i * 4 + 3] = (uint8_t)(c >> 24);
            }

            // --- 用 capsule 管理顶点内存生命周期 ---
            size_t vn2 = (size_t)vtx_count;
            nb::capsule pos_owner(pos_data, [](void* p) noexcept { delete[] (float*)p; });
            nb::capsule uv_owner(uv_data,  [](void* p) noexcept { delete[] (float*)p; });
            nb::capsule col_owner(col_data, [](void* p) noexcept { delete[] (uint8_t*)p; });

            auto positions = nb::ndarray<nb::numpy, float,   nb::ndim<2>>(pos_data, {vn2, 2}, pos_owner);
            auto uvs       = nb::ndarray<nb::numpy, float,   nb::ndim<2>>(uv_data,  {vn2, 2}, uv_owner);
            auto colors    = nb::ndarray<nb::numpy, uint8_t, nb::ndim<2>>(col_data, {vn2, 4}, col_owner);

            // --- 命令数据: 返回 Python list of (tex_id, clip_tuple, indices_ndarray, callback, userdata) ---
            nb::list cmd_list;
            for (int i = 0; i < cmd_count; i++) {
                int64_t tex_id = (int64_t)cmd_src[i].TexRef.GetTexID();
                auto clip = nb::make_tuple(
                    cmd_src[i].ClipRect.x, cmd_src[i].ClipRect.y,
                    cmd_src[i].ClipRect.z, cmd_src[i].ClipRect.w
                );
                // 预切索引: uint16 → int32, 每个 cmd 独立数组。VtxOffset 直接
                // 折进索引: 启用 RendererHasVtxOffset 后, 大 draw list (>64k
                // 顶点) 的命令携带相对基址的 16 位索引; 消费方 (如 Blender
                // gpu) 没有 BaseVertex 绘制, 必须在此还原为全局索引。
                int elem = (int)cmd_src[i].ElemCount;
                int off  = (int)cmd_src[i].IdxOffset;
                int32_t vtx_off = (int32_t)cmd_src[i].VtxOffset;
                int32_t* sub_idx = new int32_t[elem];
                for (int j = 0; j < elem; j++) {
                    sub_idx[j] = (int32_t)idx_src[off + j] + vtx_off;
                }
                nb::capsule sub_owner(sub_idx, [](void* p) noexcept { delete[] (int32_t*)p; });
                auto idx_arr = nb::ndarray<nb::numpy, int32_t, nb::ndim<1>>(sub_idx, {(size_t)elem}, sub_owner);

                // callback 命令不丢弃: 附带 callable + userdata（强引用, 可在帧后使用）
                nb::object cb_obj = nb::none();
                nb::object ud_obj = nb::none();
                if (cmd_src[i].UserCallback == ImDrawCallback_ResetRenderState) {
                    cb_obj = nb::cast(DrawListCallbackResult::RESET_RENDER_STATE);
                } else {
                    decode_drawlist_py_callback(&cmd_src[i], &cb_obj, &ud_obj);
                }
                cmd_list.append(nb::make_tuple(tex_id, clip, idx_arr, cb_obj, ud_obj));
            }

            return nb::make_tuple(positions, uvs, colors, cmd_list);
        }, "Pack vertex/index/command data into numpy arrays in one C++ call.\n"
           "Returns: (positions[N,2], uvs[N,2], colors[N,4](u8),\n"
           "          [(tex_id, (x1,y1,x2,y2), indices[M](i32), callback, userdata), ...])\n"
           "\n"
           "For regular draw commands `callback` and `userdata` are None. For commands\n"
           "added with `DrawList.add_callback` they carry the Python callable and its\n"
           "userdata (the consumer decides whether to invoke the callable or dispatch on\n"
           "the userdata). A reset-render-state token has\n"
           "`callback == DrawListCallbackResult.RESET_RENDER_STATE`.")
        .def("get_render_data_merged", [](const ImDrawList* drawList) -> nb::tuple {
            const int vtx_count = drawList->VtxBuffer.Size;
            const int idx_count = drawList->IdxBuffer.Size;
            const int cmd_count = drawList->CmdBuffer.Size;
            const ImDrawVert* vtx_src = drawList->VtxBuffer.Data;
            const ImDrawIdx*  idx_src = drawList->IdxBuffer.Data;
            const ImDrawCmd*  cmd_src = drawList->CmdBuffer.Data;

            // --- 顶点数据: 拆分 AoS → SoA (与 get_render_data 相同) ---
            float*    pos_data = new float[vtx_count * 2];
            float*    uv_data  = new float[vtx_count * 2];
            uint8_t*  col_data = new uint8_t[vtx_count * 4];
            for (int i = 0; i < vtx_count; i++) {
                pos_data[i * 2 + 0]     = vtx_src[i].pos.x;
                pos_data[i * 2 + 1] = vtx_src[i].pos.y;
                uv_data[i * 2 + 0]      = vtx_src[i].uv.x;
                uv_data[i * 2 + 1]  = vtx_src[i].uv.y;
                uint32_t c = vtx_src[i].col;
                col_data[i * 4 + 0]     = (uint8_t)(c);
                col_data[i * 4 + 1] = (uint8_t)(c >> 8);
                col_data[i * 4 + 2] = (uint8_t)(c >> 16);
                col_data[i * 4 + 3] = (uint8_t)(c >> 24);
            }

            size_t vn2 = (size_t)vtx_count;
            nb::capsule pos_owner(pos_data, [](void* p) noexcept { delete[] (float*)p; });
            nb::capsule uv_owner(uv_data,  [](void* p) noexcept { delete[] (float*)p; });
            nb::capsule col_owner(col_data, [](void* p) noexcept { delete[] (uint8_t*)p; });

            auto positions = nb::ndarray<nb::numpy, float,   nb::ndim<2>>(pos_data, {vn2, 2}, pos_owner);
            auto uvs       = nb::ndarray<nb::numpy, float,   nb::ndim<2>>(uv_data,  {vn2, 2}, uv_owner);
            auto colors    = nb::ndarray<nb::numpy, uint8_t, nb::ndim<2>>(col_data, {vn2, 4}, col_owner);

            // --- 索引数据: 整张缓冲一次性转全局 int32, vtx_offset 逐命令折叠 ---
            // 与 get_render_data 的区别: 不再逐命令切出独立数组, 而是返回整表 + 每命令
            // (idx_offset, elem_count)。消费方建一个 GPUIndexBuf + 一个 batch, 用
            // draw_range(idx_offset, elem_count) 分段绘制, 省掉 Python 侧的拼接。
            int32_t* idx_data = new int32_t[idx_count > 0 ? idx_count : 1];
            nb::list cmd_list;
            for (int i = 0; i < cmd_count; i++) {
                const ImDrawCmd& cmd = cmd_src[i];
                int elem = (int)cmd.ElemCount;
                int off  = (int)cmd.IdxOffset;
                int32_t vtx_off = (int32_t)cmd.VtxOffset;
                // 折叠当前命令的索引区间到全局表 (callback 命令 elem==0, 不写)
                for (int j = 0; j < elem; j++) {
                    idx_data[off + j] = (int32_t)idx_src[off + j] + vtx_off;
                }

                int64_t tex_id = (int64_t)cmd.TexRef.GetTexID();
                auto clip = nb::make_tuple(cmd.ClipRect.x, cmd.ClipRect.y, cmd.ClipRect.z, cmd.ClipRect.w);

                nb::object cb_obj = nb::none();
                nb::object ud_obj = nb::none();
                if (cmd.UserCallback == ImDrawCallback_ResetRenderState) {
                    cb_obj = nb::cast(DrawListCallbackResult::RESET_RENDER_STATE);
                } else {
                    decode_drawlist_py_callback(&cmd, &cb_obj, &ud_obj);
                }
                // 命令元数据: 偏移 + 数量 (普通 int), 而非切好的数组
                cmd_list.append(nb::make_tuple(tex_id, clip, off, elem, cb_obj, ud_obj));
            }

            nb::capsule idx_owner(idx_data, [](void* p) noexcept { delete[] (int32_t*)p; });
            auto indices = nb::ndarray<nb::numpy, int32_t, nb::ndim<1>>(idx_data, {(size_t)idx_count}, idx_owner);

            return nb::make_tuple(positions, uvs, colors, indices, cmd_list);
        }, "Like `get_render_data` but returns ONE merged index array for the whole draw\n"
           "list plus per-command (idx_offset, elem_count) ranges, instead of pre-sliced\n"
           "per-command index arrays. Lets a renderer build a single index buffer + batch\n"
           "and draw each command with a ranged draw call.\n"
           "Returns: (positions[N,2], uvs[N,2], colors[N,4](u8), indices[I](i32),\n"
           "          [(tex_id, (x1,y1,x2,y2), idx_offset, elem_count, callback, userdata), ...])\n"
           "\n"
           "Indices already have per-command vtx_offset folded in (global into the vertex\n"
           "arrays). `callback`/`userdata` semantics match `get_render_data`.")
        .def_prop_ro("commands", [](const ImDrawList* drawList) {
            return nb::make_iterator(nb::type<const ImDrawList*>(), "iterator", drawList->CmdBuffer.begin(), drawList->CmdBuffer.end());
        }, nb::keep_alive<0, 1>())
        .def("ptr", [](const ImDrawList* drawList) {
            return reinterpret_cast<uintptr_t>(drawList);
        }, "Internal function for reference book keeping.")
        .def("push_clip_rect", &ImDrawList::PushClipRect, "clip_rect_min"_a, "clip_rect_max"_a, "intersect_with_current_clip_rect"_a = false,
             "Render-level scissoring. This is passed down to your render function but not used for CPU-side coarse clipping. "
             "Prefer using higher-level `imgui.push_clip_rect() to affect logic (hit-testing and widget culling)")
        .def("push_clip_rect_full_screen", &ImDrawList::PushClipRectFullScreen)
        .def("pop_clip_rect", &ImDrawList::PopClipRect)
        .def("push_texture", [](ImDrawList* drawList, TextureRefOrID tex_ref) {
            drawList->PushTexture(to_texture_ref(tex_ref));
        }, "tex_ref"_a)
        .def("pop_texture", &ImDrawList::PopTexture)
        .def("get_clip_rect_min", &ImDrawList::GetClipRectMin)
        .def("get_clip_rect_max", &ImDrawList::GetClipRectMax)
        .def("add_line", &ImDrawList::AddLine, "p1"_a, "p2"_a, "col"_a, "thickness"_a = 1.0f)
        .def("add_rect", [](ImDrawList* drawList, ImVec2 p_min, ImVec2 p_max, ImU32 col, float rounding, ImDrawFlags_ flags, float thickness) {
            drawList->AddRect(p_min, p_max, col, rounding, flags, thickness);
        }, "p_min"_a, "p_max"_a, "col"_a, "rounding"_a = 0.0f, "flags"_a.sig("DrawFlags.NONE") = 0, "thickness"_a = 1.0f)
        .def("add_rect_filled", [](ImDrawList* drawList, ImVec2 p_min, ImVec2 p_max, ImU32 col, float rounding, ImDrawFlags_ flags) {
            drawList->AddRectFilled(p_min, p_max, col, rounding, flags);
        }, "p_min"_a, "p_max"_a, "col"_a, "rounding"_a = 0.0f, "flags"_a.sig("DrawFlags.NONE") = 0)
        .def("add_rect_filled_multi_color", [](ImDrawList* drawList, ImVec2 p_min, ImVec2 p_max, ImU32 col_upr_left, ImU32 col_upr_right, ImU32 col_bot_right, ImU32 col_bot_left) {
            drawList->AddRectFilledMultiColor(p_min, p_max, col_upr_left, col_upr_right, col_bot_right, col_bot_left);
        }, "p_min"_a, "p_max"_a, "col_upr_left"_a, "col_upr_right"_a, "col_bot_right"_a, "col_bot_left"_a)
        .def("add_rect_filled_multi_color_rounded", [](ImDrawList* drawList, ImVec2 p_min, ImVec2 p_max, ImU32 col_upr_left, ImU32 col_upr_right, ImU32 col_bot_right, ImU32 col_bot_left, float rounding, ImDrawFlags_ flags) {
            AddRectFilledMultiColorRounded(drawList, p_min, p_max, col_upr_left, col_upr_right, col_bot_right, col_bot_left, rounding, flags);
        }, "p_min"_a, "p_max"_a, "col_upr_left"_a, "col_upr_right"_a, "col_bot_right"_a, "col_bot_left"_a, "rounding"_a = 0.0f, "flags"_a.sig("DrawFlags.NONE") = 0)
        .def("add_quad", [](ImDrawList* drawList, ImVec2 p1, ImVec2 p2, ImVec2 p3, ImVec2 p4, ImU32 col, float thickness) {
            drawList->AddQuad(p1, p2, p3, p4, col, thickness);
        }, "p1"_a, "p2"_a, "p3"_a, "p4"_a, "col"_a, "thickness"_a = 1.0f)
        .def("add_quad_filled", &ImDrawList::AddQuadFilled, "p1"_a, "p2"_a, "p3"_a, "p4"_a, "col"_a)
        .def("add_triangle", &ImDrawList::AddTriangle, "p1"_a, "p2"_a, "p3"_a, "col"_a, "thickness"_a = 1.0f)
        .def("add_triangle_filled", &ImDrawList::AddTriangleFilled, "p1"_a, "p2"_a, "p3"_a, "col"_a)
        .def("add_circle", &ImDrawList::AddCircle, "center"_a, "radius"_a, "col"_a, "num_segments"_a = 0, "thickness"_a = 1.0f)
        .def("add_circle_filled", &ImDrawList::AddCircleFilled, "center"_a, "radius"_a, "col"_a, "num_segments"_a = 0)
        .def("add_ngon", &ImDrawList::AddNgon, "center"_a, "radius"_a, "col"_a, "num_segments"_a, "thickness"_a = 1.0f)
        .def("add_ngon_filled", &ImDrawList::AddNgonFilled, "center"_a, "radius"_a, "col"_a, "num_segments"_a)
        .def("add_ellipse", &ImDrawList::AddEllipse, "center"_a, "radius"_a, "col"_a, "rot"_a = 0.0f, "num_segments"_a = 0, "thickness"_a = 1.0f)
        .def("add_ellipse_filled", &ImDrawList::AddEllipseFilled, "center"_a, "radius"_a, "col"_a, "rot"_a = 0.0f, "num_segments"_a = 0)
        .def("add_text", [](ImDrawList* drawList, ImVec2 pos, ImU32 col, const char* text) {
            drawList->AddText(pos, col, text, nullptr);
        }, "pos"_a, "col"_a, "text"_a)
        .def("add_text", [](ImDrawList* drawList, ImFont* font, float font_size, ImVec2 pos, ImU32 col, const char* text, float wrap_width, std::optional<ImVec4> cpu_fine_clip_rect) {
            ImVec4 clip_rect(0, 0, 0, 0);
            if (cpu_fine_clip_rect) {
                clip_rect = cpu_fine_clip_rect.value();
            }
            drawList->AddText(font, font_size, pos, col, text, nullptr, wrap_width, cpu_fine_clip_rect ? &clip_rect : nullptr);
        }, "font"_a, "font_size"_a, "pos"_a, "col"_a, "text"_a, "wrap_width"_a = 0.0f, "cpu_fine_clip_rect"_a = nb::none())
        .def("add_bezier_cubic", &ImDrawList::AddBezierCubic, "p1"_a, "p2"_a, "p3"_a, "p4"_a, "col"_a, "thickness"_a, "num_segments"_a = 0)
        .def("add_bezier_quadratic", &ImDrawList::AddBezierQuadratic, "p1"_a, "p2"_a, "p3"_a, "col"_a, "thickness"_a, "num_segments"_a = 0)
        .def("add_polyline", [](ImDrawList* drawList, const std::vector<ImVec2>& points, ImU32 col, ImDrawFlags_ flags, float thickness) {
            drawList->AddPolyline(points.data(), (int)points.size(), col, flags, thickness);
        }, "points"_a, "col"_a, "flags"_a, "thickness"_a = 1.0f)
        .def("add_polyline", [](ImDrawList* drawList, const nb::ndarray<const float, nb::shape<-1, 2>, nb::device::cpu>& points, ImU32 col, ImDrawFlags_ flags, float thickness) {
            drawList->AddPolyline((const ImVec2*)points.data(), (int)points.shape(0), col, flags, thickness);
        }, "points"_a, "col"_a, "flags"_a, "thickness"_a)
        .def("add_convex_poly_filled", [](ImDrawList* drawList, const std::vector<ImVec2>& points, ImU32 col) {
            drawList->AddConvexPolyFilled(points.data(), (int)points.size(), col);
        }, "points"_a, "col"_a)
        .def("add_convex_poly_filled", [](ImDrawList* drawList, const nb::ndarray<const float, nb::shape<-1, 2>, nb::device::cpu>& points, ImU32 col) {
            drawList->AddConvexPolyFilled((const ImVec2*)points.data(), (int)points.shape(0), col);
        }, "points"_a, "col"_a)
        .def("add_concave_poly_filled", [](ImDrawList* drawList, const std::vector<ImVec2>& points, ImU32 col) {
            drawList->AddConcavePolyFilled(points.data(), (int)points.size(), col);
        }, "points"_a, "col"_a)
        .def("add_concave_poly_filled", [](ImDrawList* drawList, const nb::ndarray<const float, nb::shape<-1, 2>, nb::device::cpu>& points, ImU32 col) {
            drawList->AddConcavePolyFilled((const ImVec2*)points.data(), (int)points.shape(0), col);
        }, "points"_a, "col"_a)
        .def("add_image", [](ImDrawList* drawList, TextureRefOrID tex_ref, ImVec2 p_min, ImVec2 p_max, ImVec2 uv_min, ImVec2 uv_max, ImU32 col) {
            drawList->AddImage(to_texture_ref(tex_ref), p_min, p_max, uv_min, uv_max, col);
        }, "tex_ref"_a, "p_min"_a, "p_max"_a, "uv_min"_a = ImVec2(0, 0), "uv_max"_a = ImVec2(1, 1), "col"_a.sig("COL32_WHITE") = IM_COL32_WHITE)
        .def("add_image_quad", [](ImDrawList* drawList, TextureRefOrID tex_ref, ImVec2 p1, ImVec2 p2, ImVec2 p3, ImVec2 p4, ImVec2 uv1, ImVec2 uv2, ImVec2 uv3, ImVec2 uv4, ImU32 col) {
            drawList->AddImageQuad(to_texture_ref(tex_ref), p1, p2, p3, p4, uv1, uv2, uv3, uv4, col);
        }, "tex_ref"_a, "p1"_a, "p2"_a, "p3"_a, "p4"_a, "uv1"_a = ImVec2(0.0f, 0.0f), "uv2"_a = ImVec2(1.0f, 0.0f), "uv3"_a = ImVec2(1.0f, 1.0f), "uv4"_a = ImVec2(0.0f, 1.0f), "col"_a.sig("COL32_WHITE") = IM_COL32_WHITE)
        .def("add_image_rounded", [](ImDrawList* drawList, TextureRefOrID tex_ref, ImVec2 p_min, ImVec2 p_max, ImVec2 uv_min, ImVec2 uv_max, ImU32 col, float rounding, ImDrawFlags_ flags) {
            drawList->AddImageRounded(to_texture_ref(tex_ref), p_min, p_max, uv_min, uv_max, col, rounding, flags);
        }, "tex_ref"_a, "p_min"_a, "p_max"_a, "uv_min"_a, "uv_max"_a, "col"_a, "rounding"_a, "flags"_a.sig("DrawFlags.NONE") = 0)
        .def("path_clear", &ImDrawList::PathClear)
        .def("path_line_to", &ImDrawList::PathLineTo, "pos"_a)
        .def("path_line_to_merge_duplicate", &ImDrawList::PathLineToMergeDuplicate, "pos"_a)
        .def("path_fill_convex", &ImDrawList::PathFillConvex, "col"_a)
        .def("path_fill_concave", &ImDrawList::PathFillConcave, "col"_a)
        .def("path_stroke", [](ImDrawList* drawList, ImU32 col, ImDrawFlags_ flags, float thickness) {
            drawList->PathStroke(col, flags, thickness);
        }, "col"_a, "flags"_a.sig("DrawFlags.NONE") = 0, "thickness"_a = 1.0f)
        .def("path_arc_to", &ImDrawList::PathArcTo, "center"_a, "radius"_a, "a_min"_a, "a_max"_a, "num_segments"_a = 0)
        .def("path_arc_to_fast", &ImDrawList::PathArcToFast, "center"_a, "radius"_a, "a_min_of_12"_a, "a_max_of_12"_a)
        .def("path_elliptical_arc_to", &ImDrawList::PathEllipticalArcTo, "center"_a, "radius"_a, "rot"_a, "a_min"_a, "a_max"_a, "num_segments"_a = 0)
        .def("path_bezier_cubic_curve_to", &ImDrawList::PathBezierCubicCurveTo, "p2"_a, "p3"_a, "p4"_a, "num_segments"_a = 0)
        .def("path_bezier_quadratic_curve_to", &ImDrawList::PathBezierQuadraticCurveTo, "p2"_a, "p3"_a, "num_segments"_a = 0)
        .def("path_rect", [](ImDrawList* drawList, ImVec2 rect_min, ImVec2 rect_max, float rounding, ImDrawFlags_ flags) {
            drawList->PathRect(rect_min, rect_max, rounding, flags);
        }, "rect_min"_a, "rect_max"_a, "rounding"_a = 0.0f, "flags"_a.sig("DrawFlags.NONE") = 0)
        .def("add_draw_cmd", &ImDrawList::AddDrawCmd, "This is useful if you need to forcefully create a new draw call (to allow for dependent rendering / blending). Otherwise primitives are merged into the same draw-call as much as possible.")
        .def("channels_split", &ImDrawList::ChannelsSplit, "count"_a)
        .def("channels_merge", &ImDrawList::ChannelsMerge)
        .def("channels_set_current", &ImDrawList::ChannelsSetCurrent, "n"_a)
        .def("add_callback", [](ImDrawList* drawList, DrawListCallbackCallable cb, nb::object userdata) {
            // Both the callable and the userdata are stored as borrowed
            // PyObject* references; the Python-side DrawList wrapper keeps
            // them alive until the next new_frame().
            intptr_t data[2] = { (intptr_t)cb.ptr(), (intptr_t)userdata.ptr() };
            drawList->AddCallback(&drawlist_callback_py_wrapper, data, sizeof(data));
        }, "callback"_a, "userdata"_a.none() = nb::none())
        .def("add_reset_render_state_callback", [](ImDrawList* drawList) {
            drawList->AddCallback(ImDrawCallback_ResetRenderState, nullptr, 0);
        }, "Add a callback to reset the renderer backend's render state to default.\n"
           "Equivalent to the C++ ImDrawCallback_ResetRenderState sentinel.");

    nb::class_<ImDrawData>(m, "DrawData")
        .def("scale_clip_rects", &ImDrawData::ScaleClipRects, "fb_scale"_a)
        .def_ro("framebuffer_scale", &ImDrawData::FramebufferScale, "Amount of pixels for each unit of `display_size`. Copied from `Viewport.framebuffer_scale` (`== IO.display_framebuffer_scale` for main viewport). Generally (1,1) on normal display, (2,2) on OSX with Retina display.")
        .def_prop_ro("commands_lists", [](ImDrawData& drawData) {
            return nb::make_iterator(nb::type<ImDrawData>(), "iterator", drawData.CmdLists.begin(), drawData.CmdLists.end());
        }, nb::keep_alive<0, 1>())
        .def_prop_ro("textures", [](ImDrawData& drawData) -> std::optional<nb::typed<nb::iterator, ImTextureData *&>> {
            if (!drawData.Textures) {
                return std::nullopt;
            }
            return nb::make_iterator(nb::type<ImDrawData>(), "iterator", drawData.Textures->begin(), drawData.Textures->end());
        }, nb::keep_alive<0, 1>());
     nb::class_<ImGuiPayload>(m, "Payload", "Data payload for Drag and Drop operations: `accept_drag_drop_payload()`, `get_drag_drop_payload()`")
        .def("is_data_type", &ImGuiPayload::IsDataType)
        .def("is_preview", &ImGuiPayload::IsPreview)
        .def("is_delivery", &ImGuiPayload::IsDelivery)
        .def("data", [](ImGuiPayload& self) {
            return nb::bytes(self.Data, self.DataSize);
        });

    // ── ListClipper ──────────────────────────────────────────────────
    nb::class_<ImGuiListClipper>(m, "ListClipper",
        "Helper to clip large lists of uniformly-sized items.\n\n"
        "Manually call Begin()/End() or use as a context manager.\n"
        "Call Step() in a while-loop; use display_start/display_end to know which items to draw.")
        .def(nb::init<>())
        .def("begin", &ImGuiListClipper::Begin,
            "items_count"_a, "items_height"_a = -1.0f,
            "Begin the clipper. items_height=-1 means auto-detect from first item.")
        .def("end", &ImGuiListClipper::End,
            "End the clipper. Automatically called by the last Step() returning false.")
        .def("step", &ImGuiListClipper::Step,
            "Call in a while-loop. Returns false when done. "
            "Use display_start/display_end to determine which items to draw.")
        .def("include_item_by_index", &ImGuiListClipper::IncludeItemByIndex,
            "item_index"_a,
            "Ensure a specific item is never clipped (call before first Step()).")
        .def("include_items_by_index", &ImGuiListClipper::IncludeItemsByIndex,
            "item_begin"_a, "item_end"_a,
            "Ensure a range of items is never clipped. item_end is exclusive.")
        .def("seek_cursor_for_item", &ImGuiListClipper::SeekCursorForItem,
            "item_index"_a,
            "Seek cursor toward given item. Useful with Begin(INT_MAX) when count is unknown.")
        .def_ro("display_start", &ImGuiListClipper::DisplayStart,
            "First item to display (inclusive), updated by Step().")
        .def_ro("display_end", &ImGuiListClipper::DisplayEnd,
            "End of items to display (exclusive), updated by Step().")
        .def("__enter__", [](ImGuiListClipper* self) { return self; }, nb::rv_policy::reference)
        .def("__exit__", [](ImGuiListClipper* self, nb::handle, nb::handle, nb::handle) {
            self->End();
        });

}
