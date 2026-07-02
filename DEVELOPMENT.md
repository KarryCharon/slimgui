# Development

## Setup

```
uv sync --no-editable
```

依赖全部在 pyproject 的 dev 组里（含 pip / nanobind / scikit-build-core，
供 gen_bindings.py 的非隔离构建使用）。

> **必须 `--no-editable`**：editable(redirect) 模式下 stubs 目录
> `slimgui/slimgui_ext/*.pyi` 会在 scikit-build-core 的模块映射中覆盖
> 同名的 `slimgui_ext.abi3.so`，导致 native 扩展 import 失败。

## 仓库布局

- `src/slimgui/` — slimgui Python 包（含 stubs）
- `bindings/` — 手写 C++ 绑定：`module.cpp`（入口）、`imgui_types.cpp`
  （类绑定）、`imgui_functions.cpp`（函数绑定）、`anim.cpp`（ImAnim）；
  `bindings/generated/` 是 gen_bindings.py 的输出，勿手改
- `vendor/` — 第三方源码：`imgui`（imgui_vendor.py 管理）、
  `imanim`（git 子模块）
- `packages/fragfx/` — 独立的 fragfx 特效库（uv workspace 子包，
  纯 Python 零依赖，slimgui 本体不依赖它，仅 examples/tests 使用）

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

## VFX 性能测试

特效全部走 `fragfx`（表达式组合 → 运行时 GLSL，无 native mesh 路径）。两个
**不参与 wheel 打包**的基准脚本：

- `temp/bench_vfx_python.py`：逐特效的 Python 侧开销（模板绑值 / 临时建树 /
  draw 侧 key+uniform 收集），无 GPU。
- `temp/profile_gallery.py`：gallery 全帧分段计时（UI 构建 / GL 派发 /
  glFinish GPU / swap），隐藏窗口实跑。

```bash
.venv/bin/python temp/bench_vfx_python.py
.venv/bin/python temp/profile_gallery.py
```

4. 在真实窗口里看整体体感时，再跑 gallery（窗口标题旁有 FPS / ms）：

```bash
.venv/bin/python example/anim/gallery.py
```

### 调试时注意：Python 与 native 可能不同步

editable 模式下：

- Python wrapper / stub 在 `src/slimgui/`（随 git 更新）。
- 实际执行的 native 模块是 `.venv/lib/python3.12/site-packages/slimgui/slimgui_ext.abi3.so`（或 `pip install` 装进去的 wheel）。

若刚改完 C++ 绑定（如 `bindings/imgui_functions.cpp`）但没重装，运行时行为与源码
不一致。**处理：** 再跑一次 `uv run python tools/gen_bindings.py --stubs`，或：

```bash
.venv/bin/python -m pip install -e . --no-build-isolation
```

### 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| headless 基准 assert 顶点数超 64K | 未声明 `VtxOffset` | 设置 `BackendFlags.RENDERER_HAS_VTX_OFFSET` |
| benchmark 与 gallery FPS 不一致 | 前者无 GPU/窗口，后者含渲染与 UI 框架 | 两者结合看：benchmark 定位热点，gallery 验证体感 |

### 给后续维护者

- 新增 gallery 卡片时，在 `tools/bench_vfx_gallery.py` 的 `_card_cases()` 里补一项（与 `gallery.py` 的 draw 函数保持一致），这样基准会自动覆盖。
- 改 VFX 实现后：先 `--stubs` 编译，再跑一遍 benchmark，对比优化前后的 `gallery_cards_*` 与对应单卡行。
- 性能相关构建约定见 `temp/构建最佳实践.md`。

## Updating imgui

Edit `tools/imgui_vendor.py` to set the new version, then:

```
python tools/imgui_vendor.py
python tools/gen_bindings.py --full
```
