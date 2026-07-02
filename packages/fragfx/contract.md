# fragfx 执行契约（renderer 实现规范）

`Effect` 的可移植性由本契约保证，而不是由着色语言保证。任何后端
（OpenGL / Blender `gpu` / Vulkan / ...）只要按此实现，同一 `Effect`
语义一致（承诺语义一致，不承诺逐像素一致）。

## 数据

`Effect` 是冻结的纯数据：

| 字段 | 含义 |
|---|---|
| `color` | vec4 颜色表达式（DAG 根） |
| `p_min` / `p_max` | 覆盖 quad 边界，display 坐标，已含效果所需 padding |
| `texture_id` | 可选纹理句柄（宿主定义的不透明 int） |
| `key` / `values` | 可选快路径（`Template.effect` 预计算）；为 None 时现场 `linearize` + `structure_key` / `collect_params` |

## 渲染步骤

1. **程序缓存**：以 `effect.key`（即 `structure_key`）查缓存；未命中则
   `generate(order, index, dialect=...)` 生成 body，经 dialect `assemble`
   编译并缓存。key 与 dialect 无关——缓存按 renderer 自己的语言维护。
2. **uniform 上传**：`effect.values` 是单 float 数组，按 linearize 后序中
   `Param` 的出现序排列（GLSL 外壳中即 `uniform float UParams[N]`），
   一次性整包上传。
3. **纹理**：单槽位。表达式含 `tex()` 节点时（`GeneratedSource.uses_texture`），
   绑定 `effect.texture_id` 到 unit 0（GLSL 中 sampler 名为 `Texture`）。
4. **覆盖 quad**：按 `p_min`/`p_max` 画两个三角形；顶点坐标与表达式内
   坐标同为 display 坐标。
5. **逐像素求值**：`FRAG` = 当前像素的 display 坐标位置，**y 向下**。
   GLSL 外壳中由顶点着色器以 `Frag_Pos` varying 传入。
6. **混合**：src-over（`SRC_ALPHA, ONE_MINUS_SRC_ALPHA`），输出非预乘 alpha。
7. **裁剪**：宿主负责（如 imgui 的 `cmd.clip_rect` → scissor，注意是
   framebuffer 坐标）。
8. **状态恢复**：绘制自包含——renderer 必须在返回前恢复宿主默认
   program/VAO 等状态。

## 编译期常量

- `MAX_PARTICLES`（fragfx.lib）是粒子库函数的循环上限，进 GLSL 常量头。
- `Const` 节点、fbm octaves、gradient stops 数、corner mask 均进结构 key：
  改它们 = 新程序。`Param`（一切 Python 数字/元组）只改 uniform，零编译。

## 预热

启动时对 `fragfx.preset_templates()`（+ 应用自己的模板）逐个
`_ensure_program`，消除首帧编译卡顿。

## 参考实现

`slimgui` 仓库 `example/anim/fragfx_renderer.py`
（`VfxShaderOpenGLRenderer`）：约 80 行覆盖全部步骤，含 imgui 命令流
派发（识别 `cmd.callback_userdata` 中的 `Effect`，不运行回调）。
