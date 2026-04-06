# Development

## Setup

```
python3 -m venv .venv
. .venv/bin/activate
pip install nanobind==2.9.2 scikit-build-core litgen glfw pyopengl numpy toml
pip install -e --no-build-isolation .
```

## Build

```
python tools/gen_bindings.py --full
```

This single command runs the full pipeline: generate bindings, compile, generate stubs, and build docs.

Use `--stubs` instead of `--full` to skip docs generation.
Use no flags to only regenerate the `.inl` files.

## Test

```
pytest
```

## Updating imgui

Edit `tools/imgui_vendor.py` to set the new version, then:

```
python tools/imgui_vendor.py
python tools/gen_bindings.py --full
```
