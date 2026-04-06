#!/usr/bin/env python3
"""API compatibility verification script.

Parses .pyi stub files and compares the current API against a baseline snapshot.
Reports missing symbols, signature changes, and new additions.

Usage:
    python api_snapshot/verify_api.py [--baseline api_snapshot/imgui_baseline.pyi] [--current src/slimgui/slimgui_ext/imgui.pyi]
"""

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ApiSymbol:
    name: str
    kind: str  # 'constant', 'function', 'class', 'method', 'property', 'enum_value'
    signature: str = ""
    parent: str = ""

    @property
    def qualified_name(self) -> str:
        return f"{self.parent}.{self.name}" if self.parent else self.name


@dataclass
class ApiSurface:
    symbols: dict[str, ApiSymbol] = field(default_factory=dict)

    def add(self, sym: ApiSymbol):
        self.symbols[sym.qualified_name] = sym


def extract_api(pyi_path: str) -> ApiSurface:
    """Parse a .pyi file and extract all public symbols."""
    source = Path(pyi_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    api = ApiSurface()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name.startswith("_"):
                continue
            ann = ast.dump(node.annotation) if node.annotation else ""
            api.add(ApiSymbol(name=name, kind="constant", signature=ann))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            sig = _func_signature(node)
            api.add(ApiSymbol(name=node.name, kind="function", signature=sig))

        elif isinstance(node, ast.ClassDef):
            cls_name = node.name
            if cls_name.startswith("_"):
                continue
            api.add(ApiSymbol(name=cls_name, kind="class"))
            _extract_class_members(node, cls_name, api)

    return api


def _func_signature(node: ast.FunctionDef) -> str:
    """Extract a normalized function signature string."""
    params = []
    for arg in node.args.args:
        name = arg.arg
        ann = ast.unparse(arg.annotation) if arg.annotation else ""
        params.append(f"{name}: {ann}" if ann else name)
    for arg in node.args.posonlyargs:
        name = arg.arg
        ann = ast.unparse(arg.annotation) if arg.annotation else ""
        params.append(f"{name}: {ann}" if ann else name)
    if node.args.vararg:
        params.append(f"*{node.args.vararg.arg}")
    for arg in node.args.kwonlyargs:
        name = arg.arg
        ann = ast.unparse(arg.annotation) if arg.annotation else ""
        params.append(f"{name}: {ann}" if ann else name)
    if node.args.kwarg:
        params.append(f"**{node.args.kwarg.arg}")

    ret = ast.unparse(node.returns) if node.returns else ""
    return f"({', '.join(params)}) -> {ret}"


def _extract_class_members(cls_node: ast.ClassDef, cls_name: str, api: ApiSurface):
    """Extract methods, properties, and enum values from a class."""
    for item in ast.iter_child_nodes(cls_node):
        if isinstance(item, ast.FunctionDef):
            if item.name.startswith("_") and item.name not in ("__init__", "__getitem__", "__setitem__", "__iter__", "__len__"):
                continue
            sig = _func_signature(item)
            # Check if it's a property
            is_prop = any(
                isinstance(d, ast.Name) and d.id == "property"
                for d in item.decorator_list
            )
            kind = "property" if is_prop else "method"
            api.add(ApiSymbol(name=item.name, kind=kind, signature=sig, parent=cls_name))

        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            name = item.target.id
            if name.startswith("_"):
                continue
            ann = ast.unparse(item.annotation) if item.annotation else ""
            api.add(ApiSymbol(name=name, kind="enum_value", signature=ann, parent=cls_name))

        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    api.add(ApiSymbol(name=target.id, kind="enum_value", parent=cls_name))


def compare_apis(baseline: ApiSurface, current: ApiSurface) -> tuple[list[str], list[str], list[str]]:
    """Compare two API surfaces. Returns (missing, changed, added)."""
    missing = []
    changed = []
    added = []

    for qname, sym in baseline.symbols.items():
        if qname not in current.symbols:
            missing.append(f"MISSING: {sym.kind} {qname}")
        else:
            cur = current.symbols[qname]
            if sym.kind in ("function", "method") and sym.signature != cur.signature:
                changed.append(f"CHANGED: {qname}\n  baseline: {sym.signature}\n  current:  {cur.signature}")

    for qname, sym in current.symbols.items():
        if qname not in baseline.symbols:
            added.append(f"ADDED: {sym.kind} {qname}")

    return missing, changed, added


def main():
    parser = argparse.ArgumentParser(description="Verify API compatibility")
    parser.add_argument("--baseline", default="api_snapshot/imgui_baseline.pyi",
                        help="Path to baseline .pyi file")
    parser.add_argument("--current", default="src/slimgui/slimgui_ext/imgui.pyi",
                        help="Path to current .pyi file")
    args = parser.parse_args()

    print(f"Baseline: {args.baseline}")
    print(f"Current:  {args.current}")
    print()

    baseline = extract_api(args.baseline)
    current = extract_api(args.current)

    print(f"Baseline symbols: {len(baseline.symbols)}")
    print(f"Current symbols:  {len(current.symbols)}")
    print()

    missing, changed, added = compare_apis(baseline, current)

    ok = True
    if missing:
        ok = False
        print(f"=== MISSING ({len(missing)}) ===")
        for m in sorted(missing):
            print(f"  {m}")
        print()

    if changed:
        ok = False
        print(f"=== SIGNATURE CHANGES ({len(changed)}) ===")
        for c in sorted(changed):
            print(f"  {c}")
        print()

    if added:
        print(f"=== NEW ADDITIONS ({len(added)}) ===")
        for a in sorted(added):
            print(f"  {a}")
        print()

    if ok:
        print("API compatibility check PASSED.")
        return 0
    else:
        print("API compatibility check FAILED — see MISSING/CHANGED above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
