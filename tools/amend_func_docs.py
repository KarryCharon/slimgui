# Note: this script runs in CI and should run on the lowest Python version
# that the library is being built for.

# This script reads the comments from the ImGui header file and adds them to the
# corresponding functions in the pyi file.
import argparse
from collections import defaultdict
import re
from typing import Dict, Optional, Set, Union


# ---------------------------------------------------------------------------
# Utilities (previously in gen_utils.py)
# ---------------------------------------------------------------------------

_KNOWN_ENUMS = {
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
}


def camel_to_snake(name: str) -> str:
    if 'HSVtoRGB' in name:
        name = name.replace('HSVtoRGB', 'HsvToRgb')
    elif 'RGBtoHSV' in name:
        name = name.replace('RGBtoHSV', 'RgbToHsv')
    elif 'VSlider' in name:
        name = name.replace('VSlider', 'Vslider')
    elif name == 'PlotHistogram2D':
        return 'plot_histogram2d'

    def _camel_chunk(tok: str) -> str:
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', tok)
        s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()

    leading = len(name) - len(name.lstrip('_'))
    trailing = len(name) - len(name.rstrip('_'))
    core = name.strip('_')
    parts = core.split('_')
    core_out = '_'.join(_camel_chunk(p) for p in parts if p)
    return '_' * leading + core_out + '_' * trailing


def _get_imgui_funcnames_from_header(header_path: str) -> Set[str]:
    """Extract IMGUI_API function names directly from imgui.h."""
    funcnames: Set[str] = set()
    with open(header_path, "rt", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*IMGUI_API\s+\S+\s+(\w+)\(", line)
            if m:
                funcnames.add(m.group(1))
    return funcnames


def translate_enum_name(sym: str) -> Optional[str]:
    """Translate a C++ enum name to Python enum name."""
    if any(sym.startswith(enum_name) for enum_name in _KNOWN_ENUMS.keys()):
        if sym.startswith('ImGui'):
            enum_name, enum_field = sym.removeprefix('ImGui').split('_')
        elif sym.startswith('ImDraw') or sym.startswith('ImText'):
            enum_name, enum_field = sym.removeprefix('Im').split('_')
        else:
            return None
        if enum_field == '':
            return f'{enum_name}'
        else:
            return f'{enum_name}.{camel_to_snake(enum_field).upper()}'
    return None


def _tokenize(s: str) -> list[str]:
    return re.findall(r'\w+|[^\w\s]|\s+', s)


def _is_special_case_string(tokens: list[str]) -> Optional[list[str]]:
    exceptions = [
        ['Window', ' ', 'Menu', ' ', 'Button'],
        ['Shortcut', ' ', 'for'],
    ]
    for e in exceptions:
        if ''.join(tokens[:len(e)]) == ''.join(e):
            return e
    return None


def _match_funcname_parens(tokens: list[str]) -> tuple:
    """Parse funcname(...) pattern. Returns (shift, name, contents) or None."""
    funcname = tokens[0]
    tok_idx = 1
    while tok_idx < len(tokens) and tokens[tok_idx].strip() == '':
        tok_idx += 1
    if tok_idx >= len(tokens) or tokens[tok_idx] != '(':
        return None
    tok_idx += 1
    depth = 1
    while tok_idx < len(tokens) and depth > 0:
        if tokens[tok_idx] == '(':
            depth += 1
        elif tokens[tok_idx] == ')':
            depth -= 1
            if depth == 0:
                tok_idx += 1
                break
        tok_idx += 1
        if tok_idx >= len(tokens):
            return None
    return tok_idx, funcname, ''.join(tokens[2:tok_idx-1])


def _best_effort_fix_funcall_args(s: str) -> str:
    """Fix C++ style args in function calls to Python style."""
    tokens = _tokenize(s)
    out = []
    tok_idx = 0
    while tok_idx < len(tokens):
        match tokens[tok_idx:]:
            case ['ImVec2', *_]:
                tok_idx += 1
            case _:
                sym = tokens[tok_idx]
                if (m := translate_enum_name(sym)) is not None:
                    out += [m]
                else:
                    out += [sym]
                tok_idx += 1
    return ''.join(out)


def docstring_fixer(docstring: str, imgui_funcnames: Set[str]) -> str:
    """Replace imgui function names in a docstring with Python naming convention."""
    tokens = _tokenize(docstring)
    out = []
    tok_idx = 0
    while tok_idx < len(tokens):
        if (s := _is_special_case_string(tokens[tok_idx:])) is not None:
            out += s
            tok_idx += len(s)
            continue

        ignore_rename = {'Value'}
        rest = tokens[tok_idx:]
        sym = rest[0]
        if (sym not in ignore_rename) and (sym in imgui_funcnames):
            if (m := _match_funcname_parens(rest)) is not None:
                shift, name, contents = m
                contents = _best_effort_fix_funcall_args(contents)
                out.append(f'`{camel_to_snake(name)}({contents})`')
                tok_idx += shift
            else:
                out.append(f'`{camel_to_snake(sym)}`')
                tok_idx += 1
        else:
            if (translated := translate_enum_name(sym)) is not None:
                out.append(f'`{translated}`')
                tok_idx += 1
            else:
                out.append(sym)
                tok_idx += 1

    ret = ''.join(out)
    if ret == '':
        return ret
    return ret[0].upper() + ret[1:]


# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------

def parse_func_line_comments(header_path: str) -> Dict[str, Union[str, None]]:
    with open(header_path, "rt", encoding="utf-8") as f:
        lines = f.readlines()

    func_line_comments: Dict[str, Union[str, None]] = {}
    func_overload_count = defaultdict[str, int](int)
    for line in lines:
        line = line.rstrip()
        if (m := re.match(r"^\s*IMGUI_API .*? (\w+)\(.*;(.*)", line)) is not None:
            comment = None
            func_name = camel_to_snake(m.group(1))
            func_overload_count[func_name] += 1
            if func_overload_count[func_name] <= 1:
                trail = m.group(2)
                if (pos := trail.find('//')) != -1:
                    comment = trail[pos+2:].lstrip(' \t')
                func_line_comments[func_name] = comment
    return func_line_comments


def main():
    parser = argparse.ArgumentParser(description="Extract doc comments from imgui.h")
    parser.add_argument('--imgui-h', type=str, default='src/c/imgui/imgui.h')
    parser.add_argument('--pyi-file', type=str, default='src/slimgui/slimgui_ext.pyi')
    parser.add_argument('-o', dest='output', type=str,
                        help="If not specified, output to stdout.")
    args = parser.parse_args()

    imgui_funcnames = _get_imgui_funcnames_from_header(args.imgui_h)
    syms = parse_func_line_comments(args.imgui_h)

    out_lines = []
    func_overload_count = defaultdict[str, int](int)

    with open(args.pyi_file, "rt", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.rstrip()

            if (m := re.match(r"^def (\w+)\(", line)) is not None:
                has_doc_string = not line.endswith(': ...')
                line = re.sub(r': ...$', ':', line)
                out_lines.append(line)
                if has_doc_string:
                    continue
                func_name = m.group(1)
                func_overload_count[func_name] += 1
                if func_overload_count[func_name] <= 1 and (comment := syms.get(func_name)) is not None:
                    comment = comment.strip()
                    if comment == '"':
                        comment = ''
                    comment = comment.rstrip('"')  # strip trailing quotes that break docstrings
                    comment = comment.replace('"', '\\"')
                    if comment != '':
                        out_lines.append(f'    """{docstring_fixer(comment, imgui_funcnames)}"""')
                out_lines.append('    ...\n')
            else:
                out_lines.append(line)

    if args.output is not None:
        with open(args.output, "wt", encoding="utf-8") as f:
            f.write('\n'.join(out_lines))
    else:
        print('\n'.join(out_lines))

if __name__ == "__main__":
    main()
