#!/usr/bin/env python3
"""Generate slimgui bindings using litgen.

Reads imgui.h and generates:
  - src/imgui_enums.inl   (C++ nanobind enum binding code)
  - src/imgui_funcs.inl   (C++ nanobind function binding code)

Simple functions are auto-generated via a litgen allowlist (LITGEN_FUNC_ALLOWLIST).
Complex bindings (callbacks, out-params, custom types) remain hand-written in
slimgui_ext.cpp.

Usage:
    python tools/gen_bindings.py [--imgui-h src/c/imgui/imgui.h]
"""

import re
import subprocess
import sys
from pathlib import Path

import litgen

ROOT = Path(__file__).resolve().parent.parent
IMGUI_H = ROOT / "src" / "c" / "imgui" / "imgui.h"
OUT_ENUMS_INL = ROOT / "src" / "imgui_enums.inl"
OUT_FUNCS_INL = ROOT / "src" / "imgui_funcs.inl"


def preprocess_imgui_code(code: str) -> str:
    """Clean up imgui.h macros that confuse srcML."""
    code = re.sub(r"IM_FMTARGS\(\d\)", "", code)
    code = re.sub(r"IM_FMTLIST\(\d\)", "", code)
    code = re.sub(
        r"\nIM_MSVC_RUNTIME_CHECKS_OFF\n",
        "\nIM_MSVC_RUNTIME_CHECKS_OFF;\n",
        code,
    )
    code = re.sub(
        r"\nIM_MSVC_RUNTIME_CHECKS_RESTORE\n",
        "\nIM_MSVC_RUNTIME_CHECKS_RESTORE;\n",
        code,
    )
    return code


# Enums we want to expose (C++ name -> Python name)
IMGUI_ENUMS = [
    "ImDrawFlags_",
    "ImGuiInputTextFlags_",
    "ImGuiButtonFlags_",
    "ImGuiChildFlags_",
    "ImGuiDragDropFlags_",
    "ImGuiFocusedFlags_",
    "ImGuiInputFlags_",
    "ImGuiWindowFlags_",
    "ImGuiTreeNodeFlags_",
    "ImGuiTabBarFlags_",
    "ImGuiTabItemFlags_",
    "ImGuiTableFlags_",
    "ImGuiTableRowFlags_",
    "ImGuiTableColumnFlags_",
    "ImGuiColorEditFlags_",
    "ImGuiComboFlags_",
    "ImGuiSelectableFlags_",
    "ImGuiConfigFlags_",
    "ImGuiBackendFlags_",
    "ImGuiCond_",
    "ImGuiHoveredFlags_",
    "ImGuiItemFlags_",
    "ImGuiSliderFlags_",
    "ImGuiPopupFlags_",
    "ImGuiMouseButton_",
    "ImGuiMouseCursor_",
    "ImGuiCol_",
    "ImGuiDir",
    "ImGuiStyleVar_",
    "ImGuiTableBgTarget_",
    "ImGuiMouseSource",
    "ImTextureStatus",
    "ImTextureFormat",
    "ImGuiKey",
    "ImGuiMultiSelectFlags_",
    "ImGuiSelectionRequestType",
]

# Python names for enums (strip ImGui/Im prefix and trailing _)
ENUM_PY_NAMES = {
    "ImDrawFlags_": "DrawFlags",
    "ImGuiInputTextFlags_": "InputTextFlags",
    "ImGuiButtonFlags_": "ButtonFlags",
    "ImGuiChildFlags_": "ChildFlags",
    "ImGuiDragDropFlags_": "DragDropFlags",
    "ImGuiFocusedFlags_": "FocusedFlags",
    "ImGuiInputFlags_": "InputFlags",
    "ImGuiWindowFlags_": "WindowFlags",
    "ImGuiTreeNodeFlags_": "TreeNodeFlags",
    "ImGuiTabBarFlags_": "TabBarFlags",
    "ImGuiTabItemFlags_": "TabItemFlags",
    "ImGuiTableFlags_": "TableFlags",
    "ImGuiTableRowFlags_": "TableRowFlags",
    "ImGuiTableColumnFlags_": "TableColumnFlags",
    "ImGuiColorEditFlags_": "ColorEditFlags",
    "ImGuiComboFlags_": "ComboFlags",
    "ImGuiSelectableFlags_": "SelectableFlags",
    "ImGuiConfigFlags_": "ConfigFlags",
    "ImGuiBackendFlags_": "BackendFlags",
    "ImGuiCond_": "Cond",
    "ImGuiHoveredFlags_": "HoveredFlags",
    "ImGuiItemFlags_": "ItemFlags",
    "ImGuiSliderFlags_": "SliderFlags",
    "ImGuiPopupFlags_": "PopupFlags",
    "ImGuiMouseButton_": "MouseButton",
    "ImGuiMouseCursor_": "MouseCursor",
    "ImGuiCol_": "Col",
    "ImGuiDir": "Dir",
    "ImGuiStyleVar_": "StyleVar",
    "ImGuiTableBgTarget_": "TableBgTarget",
    "ImGuiMouseSource": "MouseSource",
    "ImTextureStatus": "TextureStatus",
    "ImTextureFormat": "TextureFormat",
    "ImGuiKey": "Key",
    "ImGuiMultiSelectFlags_": "MultiSelectFlags",
    "ImGuiSelectionRequestType": "SelectionRequestType",
}


def _postprocess_pydef(code: str) -> str:
    """Fix C++ enum binding code to match slimgui conventions.

    - Strip trailing _ from Python enum class names: "WindowFlags_" -> "WindowFlags"
    - Convert enum value names to UPPER_SNAKE_CASE: "no_title_bar" -> "NO_TITLE_BAR"
    - Key enum: add KEY_ prefix, handle ImGuiMod_ -> MOD_ prefix
    """
    # Fix class names: (m, "WindowFlags_", ...) -> (m, "WindowFlags", ...)
    for cpp_name, py_name in ENUM_PY_NAMES.items():
        litgen_name = py_name + "_" if cpp_name.endswith("_") else py_name
        if litgen_name != py_name:
            code = code.replace(f'"{litgen_name}"', f'"{py_name}"')

    # Convert .value("snake_case", ...) to .value("UPPER_SNAKE_CASE", ...)
    def upper_value(m: re.Match) -> str:
        return f'.value("{m.group(1).upper()}"'

    code = re.sub(r'\.value\("([a-z_0-9]+)"', upper_value, code)

    # Fix docstrings that end with escaped quotes (causes """...\"""" syntax errors in stubs)
    # Match: .value("NAME", CppName, "some doc ending with \"")
    # Replace trailing \" before closing ") with just "
    code = re.sub(r'\\""\)', '")', code)

    # Key enum special handling: add KEY_ prefix and fix MOD_ values
    # Find the Key enum block and fix value names
    lines = code.split("\n")
    in_key_enum = False
    result_lines = []
    for line in lines:
        if 'nb::enum_<ImGuiKey>' in line:
            in_key_enum = True
        elif in_key_enum and ('nb::enum_<' in line):
            # Next enum started, Key enum is done
            in_key_enum = False

        if in_key_enum and '.value("' in line:
            # Fix ImGuiMod_ values: "IM_GUI_MOD_CTRL" -> "MOD_CTRL"
            line = re.sub(r'\.value\("IM_GUI_MOD_', '.value("MOD_', line)
            # Add KEY_ prefix to non-MOD values
            m = re.search(r'\.value\("([A-Z_0-9]+)"', line)
            if m and not m.group(1).startswith("MOD_"):
                old_name = m.group(1)
                new_name = f"KEY_{old_name}"
                # Fix double underscore: KEY__0 -> KEY_0
                new_name = re.sub(r"KEY__(\d)", r"KEY_\1", new_name)
                line = line.replace(f'.value("{old_name}"', f'.value("{new_name}"')

        result_lines.append(line)

    return "\n".join(result_lines)


def make_litgen_options() -> litgen.LitgenOptions:
    """Configure litgen options for imgui enum generation."""
    options = litgen.LitgenOptions()
    options.bind_library = litgen.BindLibraryType.nanobind
    options.python_convert_to_snake_case = True

    # API prefix
    options.srcmlcpp_options.functions_api_prefixes = "IMGUI_API"

    # Preprocess
    options.srcmlcpp_options.code_preprocess_function = preprocess_imgui_code

    # Namespace handling
    options.namespace_names_replacements.add_last_replacement(r"^ImGui$", "imgui")

    # We ONLY want enums - exclude everything else
    options.fn_exclude_by_name__regex = ".*"
    options.class_exclude_by_name__regex = ".*"
    options.member_exclude_by_name__regex = ".*"
    options.globals_vars_include_by_name__regex = "^$"  # exclude all globals

    # Enum naming: strip ImGui/Im prefix
    enum_name_replacements = [
        (r"^ImGui", ""),
        (r"^ImDraw", "Draw"),
        (r"^ImTexture", "Texture"),
        (r"^Im", ""),
    ]
    for pattern, replacement in enum_name_replacements:
        options.type_replacements.add_last_replacement(pattern, replacement)

    # Flag enums: types ending with Flags_ should be is_flag
    options.enum_make_flag__regex = r".*Flags_$"
    options.enum_make_arithmetic__regex = ".*"

    # Remove common prefix from enum values
    options.enum_flag_remove_values_prefix = True

    # Post-processing to match slimgui naming conventions
    options.postprocess_pydef_function = _postprocess_pydef

    return options


def extract_enum_blocks(imgui_h_code: str) -> str:
    """Extract only enum declarations from imgui.h for litgen processing.

    This avoids litgen trying to parse the entire header (which has many
    constructs it can't handle), and focuses on what we need: enums.
    """
    lines = imgui_h_code.split("\n")
    output_lines = []
    in_enum = False
    brace_depth = 0

    # Add necessary typedefs so srcML can parse
    output_lines.append("#define IMGUI_API")
    output_lines.append("typedef int ImGuiID;")
    output_lines.append("typedef unsigned int ImU32;")
    output_lines.append("typedef unsigned short ImU16;")
    output_lines.append("typedef unsigned char ImU8;")
    output_lines.append("typedef int ImGuiKeyChord;")
    output_lines.append("")

    for line in lines:
        # Detect enum start
        if not in_enum:
            for enum_name in IMGUI_ENUMS:
                # Match "enum EnumName_" or "enum EnumName"
                if re.match(rf"^\s*enum\s+{re.escape(enum_name)}\b", line):
                    in_enum = True
                    brace_depth = 0
                    output_lines.append(line)
                    if "{" in line:
                        brace_depth += line.count("{") - line.count("}")
                    break
        else:
            output_lines.append(line)
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0 and "}" in line:
                in_enum = False
                output_lines.append("")

    return "\n".join(output_lines)


def _join_regexes(patterns: list[str]) -> str:
    """Join regex patterns with | for litgen exclude options."""
    return "|".join(patterns)


# ---------------------------------------------------------------------------
# Functions that MUST remain hand-written in slimgui_ext.cpp
# (complex logic, custom types, out-param adaptation, callbacks, etc.)
# ---------------------------------------------------------------------------
MANUAL_FUNC_PATTERNS = [
    # Context management (custom Context wrapper)
    r"^CreateContext$", r"^DestroyContext$", r"^SetCurrentContext$", r"^GetCurrentContext$",
    # Main (bound via Context or custom wrappers)
    r"^GetIO$", r"^GetPlatformIO$", r"^GetStyle$", r"^NewFrame$",
    r"^GetDrawData$", r"^GetMainViewport$",
    r"^GetBackgroundDrawList$", r"^GetForegroundDrawList$", r"^GetWindowDrawList$",
    # Demo/Debug windows (bool* p_open -> tuple)
    r"^ShowDemoWindow$", r"^ShowMetricsWindow$", r"^ShowDebugLogWindow$",
    r"^ShowIDStackToolWindow$", r"^ShowAboutWindow$",
    r"^ShowStyleEditor$",  # takes ImGuiStyle* ref
    r"^ShowStyleSelector$", r"^ShowFontSelector$", r"^ShowUserGuide$",  # in imgui_demo.cpp
    # Style functions (take ImGuiStyle* dst)
    r"^StyleColorsDark$", r"^StyleColorsLight$", r"^StyleColorsClassic$",
    # Windows (bool* p_open -> tuple)
    r"^Begin$",
    # Child windows (custom flags handling)
    r"^BeginChild$",
    # Font stack (custom logic)
    r"^PushFont$", r"^GetFont$", r"^GetFontBaked$",
    # Style color with Vec3 overload
    r"^PushStyleColor$",
    # Style var overloads
    r"^PushStyleVar$", r"^PushStyleVarX$", r"^PushStyleVarY$",
    # Item flags (enum cast)
    r"^PushItemFlag$",
    # GetColorU32 overloads (complex)
    r"^GetColorU32$",
    # Window manipulation with Cond (custom .sig())
    r"^SetNextWindowPos$", r"^SetNextWindowSize$",
    r"^SetNextWindowSizeConstraints$",
    r"^SetNextWindowCollapsed$",
    r"^SetWindowPos$", r"^SetWindowSize$", r"^SetWindowCollapsed$",
    r"^SetWindowFocus$",  # has overloads (void vs name)
    # Scrolling (lambda wrappers for overloads)
    r"^SetScrollX$", r"^SetScrollY$",
    r"^SetScrollFromPosX$", r"^SetScrollFromPosY$",
    # ID stack (overloads: str/int/ptr)
    r"^PushID$", r"^GetID$",
    # Text functions (printf format / special handling)
    r"^Text$", r"^TextV$", r"^TextColored$", r"^TextColoredV$",
    r"^TextDisabled$", r"^TextDisabledV$", r"^TextWrapped$", r"^TextWrappedV$",
    r"^LabelText$", r"^LabelTextV$", r"^BulletText$", r"^BulletTextV$",
    # Image (TextureRefOrID variant)
    r"^Image$", r"^ImageButton$",
    # Combo (custom out-param / callback)
    r"^Combo$", r"^BeginCombo$",
    # Selectable (bool* out-param)
    r"^Selectable$",
    # Drag/Slider (mutable values, custom types)
    r"^DragFloat", r"^DragInt", r"^DragScalar",
    r"^SliderFloat", r"^SliderInt", r"^SliderAngle$", r"^SliderScalar",
    r"^VSliderFloat$", r"^VSliderInt$", r"^VSliderScalar$",
    # Input (custom callback, mutable values)
    r"^InputText", r"^InputFloat", r"^InputInt", r"^InputDouble$", r"^InputScalar",
    # Color edit/picker (mutable float arrays, Vec3)
    r"^ColorEdit3$", r"^ColorEdit4$", r"^ColorPicker3$", r"^ColorPicker4$",
    r"^ColorButton$",
    r"^SetColorEditOptions$",
    # Trees (overloads with format strings)
    r"^TreeNode$", r"^TreeNodeV$", r"^TreeNodeEx$", r"^TreeNodeExV$",
    # Collapsing header (bool* visible out-param)
    r"^CollapsingHeader$",
    # ListBox (custom callback)
    r"^ListBox$", r"^BeginListBox$",
    # Plot (function pointer callbacks)
    r"^PlotLines$", r"^PlotHistogram$",
    # Value helpers (overloads)
    r"^Value$",
    # Menu item (bool* selected out-param)
    r"^MenuItem$",
    # Tooltips (printf format)
    r"^SetTooltip$", r"^SetTooltipV$", r"^SetItemTooltip$", r"^SetItemTooltipV$",
    # Popups (custom optional str_id, .sig() defaults)
    r"^BeginPopup$", r"^BeginPopupModal$",
    r"^OpenPopup$",
    r"^OpenPopupOnItemClick$",
    r"^BeginPopupContextItem$", r"^BeginPopupContextWindow$", r"^BeginPopupContextVoid$",
    r"^IsPopupOpen$",
    # Tab bar/item (custom flags .sig())
    r"^BeginTabBar$", r"^BeginTabItem$", r"^TabItemButton$",
    # Tables (custom flags .sig())
    r"^BeginTable$", r"^TableSetupColumn$", r"^TableSetBgColor$",
    # Checkbox (bool* out-param)
    r"^Checkbox$",
    # RadioButton (overloads)
    r"^RadioButton$",
    # Progress bar (custom)
    r"^ProgressBar$",
    # Drag and drop (bytes handling)
    r"^BeginDragDropSource$", r"^SetDragDropPayload$",
    r"^AcceptDragDropPayload$", r"^GetDragDropPayload$",
    # IsWindowFocused/Hovered (enum flags .sig())
    r"^IsWindowFocused$", r"^IsWindowHovered$",
    # IsItemClicked (enum .sig())
    r"^IsItemClicked$",
    # IsItemHovered (flags .sig())
    r"^IsItemHovered$",
    # Mouse functions (enum casts, optional params)
    r"^IsMouseDown$", r"^IsMouseClicked$", r"^IsMouseReleased$",
    r"^IsMouseDoubleClicked$", r"^GetMouseClickedCount$",
    r"^IsMouseDragging$", r"^GetMouseDragDelta$", r"^ResetMouseDragDelta$",
    r"^GetMouseCursor$", r"^SetMouseCursor$",
    r"^IsMousePosValid$",
    # Key functions (enum casts)
    r"^IsKeyDown$", r"^IsKeyPressed$", r"^IsKeyReleased$",
    r"^GetKeyName$",
    r"^SetNextFrameWantCaptureKeyboard$",
    # Shortcut
    r"^Shortcut$",
    # Misc internal / not exposed
    r"^DebugCheckVersionAndDataLayout$", r"^DebugLog$", r"^DebugLogV$",
    r"^SetAllocatorFunctions$", r"^GetAllocatorFunctions$",
    r"^MemAlloc$", r"^MemFree$",
    r"^LoadIniSettings", r"^SaveIniSettings",
    # CalcTextSize (custom)
    r"^CalcTextSize$",
    # ColorConvert (custom)
    r"^ColorConvertU32ToFloat4$", r"^ColorConvertFloat4ToU32$",
    r"^ColorConvertRGBtoHSV$", r"^ColorConvertHSVtoRGB$",
    # SetNextItemOpen (Cond .sig())
    r"^SetNextItemOpen$",
    # BeginDisabled/EndDisabled
    r"^BeginDisabled$",
    # MultiSelect (custom bindings with adapter callbacks)
    r"^BeginMultiSelect$", r"^EndMultiSelect$",
    r"^SetNextItemSelectionUserData$", r"^IsItemToggledSelection$",
]

# Functions we want litgen to generate (allowlist approach is safer).
# These are simple forwarding functions with no complex logic.
LITGEN_FUNC_ALLOWLIST = [
    # Demo/Debug simple
    "GetVersion",
    # Main simple
    "Render", "EndFrame",
    # Windows
    "End",
    # Child windows
    "EndChild",
    # Window utilities (simple getters)
    "IsWindowAppearing", "IsWindowCollapsed",
    "GetWindowPos", "GetWindowSize", "GetWindowWidth", "GetWindowHeight",
    # Content region
    "GetContentRegionAvail",
    # Scrolling (simple getters)
    "GetScrollX", "GetScrollY", "GetScrollMaxX", "GetScrollMaxY",
    "SetScrollHereX", "SetScrollHereY",
    # Font stack
    "PopFont",
    # Style stacks
    "PopStyleColor", "PopStyleVar",
    "PopItemFlag",
    # Parameters stacks (current window)
    "PushItemWidth", "PopItemWidth", "SetNextItemWidth", "CalcItemWidth",
    "PushTextWrapPos", "PopTextWrapPos",
    # Style read access
    "GetFontSize", "GetFontTexUvWhitePixel",
    # Cursor / Layout
    "Separator", "SameLine", "NewLine", "Spacing", "Dummy",
    "Indent", "Unindent", "BeginGroup", "EndGroup",
    "GetCursorPos", "GetCursorPosX", "GetCursorPosY",
    "SetCursorPos", "SetCursorPosX", "SetCursorPosY",
    "GetCursorStartPos", "GetCursorScreenPos", "SetCursorScreenPos",
    "AlignTextToFramePadding",
    "GetTextLineHeight", "GetTextLineHeightWithSpacing",
    "GetFrameHeight", "GetFrameHeightWithSpacing",
    # Widgets: simple
    "Button", "SmallButton", "ArrowButton",
    "Bullet",
    # Widgets: Checkbox/Radio - simple ones
    # Trees: simple
    "TreePush", "TreePop", "GetTreeNodeToLabelSpacing",
    # Menus
    "BeginMenuBar", "EndMenuBar", "BeginMainMenuBar", "EndMainMenuBar",
    "BeginMenu", "EndMenu",
    # Tooltips
    "BeginTooltip", "EndTooltip", "BeginItemTooltip",
    # Popups: simple
    "EndPopup", "CloseCurrentPopup",
    # Tab bars: simple
    "EndTabBar", "EndTabItem",
    # Tables: simple
    "EndTable", "TableNextColumn", "TableSetColumnIndex",
    "TableHeadersRow", "TableHeader",
    "TableGetColumnCount", "TableGetColumnIndex", "TableGetRowIndex",
    "TableSetColumnEnabled",
    # Drag and drop: simple
    "EndDragDropSource", "BeginDragDropTarget", "EndDragDropTarget",
    # Item utils: simple getters
    "IsItemActive", "IsItemFocused",
    "IsItemVisible", "IsItemEdited", "IsItemActivated", "IsItemDeactivated",
    "IsItemDeactivatedAfterEdit", "IsItemToggledOpen",
    "IsAnyItemHovered", "IsAnyItemActive", "IsAnyItemFocused",
    "GetItemRectMin", "GetItemRectMax", "GetItemRectSize", "GetItemID",
    # Focus
    "SetItemDefaultFocus", "SetKeyboardFocusHere",
    "SetNextItemAllowOverlap",
    # Window manipulation: simple
    "SetNextWindowContentSize", "SetNextWindowFocus",
    "SetNextWindowScroll", "SetNextWindowBgAlpha",
    "SetWindowFontScale",
    # Misc
    "GetTime", "GetFrameCount",
    # Clipboard
    "GetClipboardText", "SetClipboardText",
    # Mouse: simple
    "IsMouseHoveringRect", "GetMousePos", "GetMousePosOnOpeningCurrentPopup",
    # Debug
    "DebugTextEncoding", "DebugFlashStyleColor", "DebugStartItemPicker",
    # Disabled
    "EndDisabled",
    # Table sort specs
    "TableGetSortSpecs",
    # Table scroll freeze
    "TableSetupScrollFreeze",
    # Misc (new)
    "IsAnyMouseDown",
    "SetNextItemStorageID",
    # Ini settings
    "LoadIniSettingsFromDisk", "SaveIniSettingsToDisk",
]


def make_litgen_options_funcs() -> litgen.LitgenOptions:
    """Configure litgen options for imgui function generation."""
    options = litgen.LitgenOptions()
    options.bind_library = litgen.BindLibraryType.nanobind
    options.python_convert_to_snake_case = True
    options.original_location_flag_show = False

    # API prefix
    options.srcmlcpp_options.functions_api_prefixes = "IMGUI_API"

    # Preprocess
    options.srcmlcpp_options.code_preprocess_function = preprocess_imgui_code

    # Namespace handling
    options.namespace_names_replacements.add_last_replacement(r"^ImGui$", "imgui")

    # Exclude ALL classes (keep manual)
    options.class_exclude_by_name__regex = ".*"

    # Exclude ALL enums (already handled by imgui_enums.inl)
    options.enum_exclude_by_name__regex = ".*"

    # Exclude all global variables
    options.globals_vars_include_by_name__regex = "^$"

    # Only include functions from our allowlist (exclude everything else)
    allowlist_inner = "|".join(LITGEN_FUNC_ALLOWLIST)
    options.fn_exclude_by_name__regex = f"^(?!({allowlist_inner})$).*$"

    # Exclude functions with varargs or problematic param types
    options.fn_exclude_by_param_type__regex = r"\.\.\.|va_list|void\s*\*|ImGuiInputTextCallback|ImGuiSizeCallbackData"

    # Type replacements (strip ImGui prefix for types used in signatures)
    type_replacements = [
        (r"^ImGui", ""),
        (r"^ImDraw", "Draw"),
        (r"^ImTexture", "Texture"),
        (r"^Im", ""),
    ]
    for pattern, replacement in type_replacements:
        options.type_replacements.add_last_replacement(pattern, replacement)

    # Function name replacements
    options.function_names_replacements.add_last_replacement(r"^ImGui_", "")

    # Post-processing
    options.postprocess_pydef_function = _postprocess_pydef_funcs

    return options


def _postprocess_pydef_funcs(code: str) -> str:
    """Fix generated function binding code to match slimgui conventions."""
    # litgen may generate "auto pyClassXxx = ..." variable declarations, remove them
    code = re.sub(r"auto py\w+ =\s*\n\s*", "", code)
    # litgen wraps in namespace block with its own submodule variable.
    # We need to use the existing `m` variable from slimgui_ext.cpp.
    # Remove the namespace wrapper and replace pyNsImGui with m.
    code = re.sub(r'\{ // <namespace ImGui>\n', '', code)
    code = re.sub(r'    nb::module_ pyNsImGui = m\.def_submodule\("imgui", "namespace ImGui"\);\n', '', code)
    code = re.sub(r'\} // </namespace ImGui>\n?', '', code)
    code = code.replace("pyNsImGui.", "m.")
    # Fix docstrings that end with escaped quotes (causes """...\"""" syntax errors in stubs)
    code = re.sub(r'\\""\)', '")', code)
    return code


def extract_imgui_namespace(imgui_h_code: str) -> str:
    """Extract the ImGui namespace block from imgui.h for litgen processing."""
    lines = imgui_h_code.split("\n")
    output_lines = []
    in_namespace = False
    brace_depth = 0

    # Add necessary forward declarations / typedefs so srcML can parse
    output_lines.append("#define IMGUI_API")
    output_lines.append("typedef int ImGuiID;")
    output_lines.append("typedef unsigned int ImU32;")
    output_lines.append("typedef unsigned short ImU16;")
    output_lines.append("typedef unsigned char ImU8;")
    output_lines.append("typedef int ImGuiKeyChord;")
    output_lines.append("typedef int ImGuiCol;")
    output_lines.append("typedef int ImGuiCond;")
    output_lines.append("typedef int ImGuiDataType;")
    output_lines.append("typedef int ImGuiDir;")
    output_lines.append("typedef int ImGuiMouseButton;")
    output_lines.append("typedef int ImGuiMouseCursor;")
    output_lines.append("typedef int ImGuiSortDirection;")
    output_lines.append("typedef int ImGuiStyleVar;")
    output_lines.append("typedef int ImGuiTableBgTarget;")
    output_lines.append("typedef int ImGuiChildFlags;")
    output_lines.append("typedef int ImGuiColorEditFlags;")
    output_lines.append("typedef int ImGuiComboFlags;")
    output_lines.append("typedef int ImGuiDragDropFlags;")
    output_lines.append("typedef int ImGuiFocusedFlags;")
    output_lines.append("typedef int ImGuiHoveredFlags;")
    output_lines.append("typedef int ImGuiInputFlags;")
    output_lines.append("typedef int ImGuiInputTextFlags;")
    output_lines.append("typedef int ImGuiItemFlags;")
    output_lines.append("typedef int ImGuiPopupFlags;")
    output_lines.append("typedef int ImGuiSelectableFlags;")
    output_lines.append("typedef int ImGuiSliderFlags;")
    output_lines.append("typedef int ImGuiTabBarFlags;")
    output_lines.append("typedef int ImGuiTabItemFlags;")
    output_lines.append("typedef int ImGuiTableFlags;")
    output_lines.append("typedef int ImGuiTableColumnFlags;")
    output_lines.append("typedef int ImGuiTableRowFlags;")
    output_lines.append("typedef int ImGuiTreeNodeFlags;")
    output_lines.append("typedef int ImGuiWindowFlags;")
    output_lines.append("typedef int ImGuiButtonFlags;")
    output_lines.append("typedef int ImGuiMultiSelectFlags;")
    output_lines.append("typedef int ImDrawFlags;")
    output_lines.append("typedef void* ImTextureID;")
    output_lines.append("struct ImVec2 { float x, y; };")
    output_lines.append("struct ImVec4 { float x, y, z, w; };")
    output_lines.append("struct ImFont;")
    output_lines.append("struct ImFontAtlas;")
    output_lines.append("struct ImFontBaked;")
    output_lines.append("struct ImDrawList;")
    output_lines.append("struct ImDrawData;")
    output_lines.append("struct ImGuiContext;")
    output_lines.append("struct ImGuiIO;")
    output_lines.append("struct ImGuiPlatformIO;")
    output_lines.append("struct ImGuiStyle;")
    output_lines.append("struct ImGuiViewport;")
    output_lines.append("struct ImGuiPayload;")
    output_lines.append("struct ImGuiTableSortSpecs;")
    output_lines.append("struct ImGuiTextFilter;")
    output_lines.append("struct ImGuiTextBuffer;")
    output_lines.append("struct ImGuiStorage;")
    output_lines.append("struct ImGuiListClipper;")
    output_lines.append("struct ImColor;")
    output_lines.append("struct ImTextureRef;")
    output_lines.append("")

    found_first_namespace = False
    for i, line in enumerate(lines):
        if not in_namespace:
            if re.match(r"^namespace\s+ImGui\s*$", line.strip()):
                # Only take the first ImGui namespace (public API)
                if not found_first_namespace:
                    found_first_namespace = True
                    in_namespace = True
                    brace_depth = 0
                    output_lines.append(line)
        else:
            output_lines.append(line)
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0 and "}" in line:
                in_namespace = False
                break

    return "\n".join(output_lines)


def generate():
    """Main generation entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate slimgui bindings via litgen")
    parser.add_argument("--imgui-h", default=str(IMGUI_H), help="Path to imgui.h")
    parser.add_argument("--full", action="store_true",
                        help="Full build: generate .inl + pip install + stubs + docs")
    parser.add_argument("--stubs", action="store_true",
                        help="Generate .inl + pip install + stubs (no docs)")
    args = parser.parse_args()

    imgui_h_path = Path(args.imgui_h)
    if not imgui_h_path.exists():
        print(f"Error: {imgui_h_path} not found", file=sys.stderr)
        sys.exit(1)

    imgui_h_code = imgui_h_path.read_text(encoding="utf-8")

    # --- Generate enum bindings ---
    enum_code = extract_enum_blocks(imgui_h_code)
    options = make_litgen_options()
    generated = litgen.generate_code(options, enum_code)

    pydef = generated.pydef_code
    if pydef.strip():
        pydef = re.sub(r"auto pyEnum\w+ =\s*\n\s*", "", pydef)
        OUT_ENUMS_INL.write_text(
            f"// Auto-generated by gen_bindings.py - DO NOT EDIT\n{pydef}",
            encoding="utf-8",
        )
        print(f"Wrote {OUT_ENUMS_INL}")

    # --- Generate function bindings ---
    ns_code = extract_imgui_namespace(imgui_h_code)
    func_options = make_litgen_options_funcs()
    func_generated = litgen.generate_code(func_options, ns_code)

    func_pydef = func_generated.pydef_code
    if func_pydef.strip():
        func_pydef = re.sub(r"auto py\w+ =\s*\n\s*", "", func_pydef)
        OUT_FUNCS_INL.write_text(
            f"// Auto-generated by gen_bindings.py - DO NOT EDIT\n{func_pydef}",
            encoding="utf-8",
        )
        print(f"Wrote {OUT_FUNCS_INL}")

    print("Done generating .inl files.")

    if not (args.full or args.stubs):
        return

    # --- pip install ---
    print("\n=== Installing package ===")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-build-isolation", "."],
                   cwd=ROOT, check=True)

    # --- Version check ---
    import toml
    imgui_version = toml.load(ROOT / "pyproject.toml")["tool"]["slimgui"]["imgui_version"]
    subprocess.run([sys.executable, "-c",
                    f"from slimgui import imgui; assert imgui.get_version() == '{imgui_version}'"],
                   check=True)

    # --- Generate stubs ---
    print("\n=== Generating stubs ===")
    import glob
    build_dirs = glob.glob(str(ROOT / "build" / "*/"))
    if not build_dirs:
        print("Error: no build directory found under build/", file=sys.stderr)
        sys.exit(1)
    build_dir = build_dirs[0].rstrip("/")
    subprocess.run([sys.executable, "-m", "nanobind.stubgen",
                    "-i", build_dir, "-q", "-m", "slimgui_ext", "-r",
                    "-O", str(ROOT / "src" / "slimgui")], check=True)

    # --- Fix stubs ---
    pyi_file = str(ROOT / "src" / "slimgui" / "slimgui_ext" / "imgui.pyi")
    subprocess.run([sys.executable, str(ROOT / "tools" / "stubfixer.py"),
                    pyi_file, "-o", pyi_file], check=True)

    # --- Amend docs into stubs ---
    print("\n=== Amending docstrings ===")
    subprocess.run([sys.executable, str(ROOT / "tools" / "amend_func_docs.py"),
                    "--imgui-h", str(imgui_h_path),
                    "--pyi-file", pyi_file, "-o", pyi_file], check=True)

    if not args.full:
        print("\nDone (stubs generated).")
        return

    # --- Build docs ---
    print("\n=== Building docs ===")
    dist_dir = ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_docs.py"),
                    f"--imgui-version={imgui_version}",
                    "--module", "slimgui.imgui",
                    "--pyi-file", pyi_file,
                    "--output", str(dist_dir / "index.html"),
                    str(ROOT / "docs" / "apiref.md")], check=True)

    print("\nFull build complete.")


if __name__ == "__main__":
    generate()
