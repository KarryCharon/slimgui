# fragfx

渲染器无关的 fragment 特效组合框架：用 Python 表达式 DAG 描述逐像素效果,
运行时生成 shader(内置 GLSL 方言),按树**形状**缓存编译产物——动画零重编译。

```python
import fragfx as fx

rect = fx.fields.RoundedRect(p_min, p_max, rounding)
band = fx.profiles.tent((rect.sdf + 1.5) / 3.0)
sweep = fx.profiles.gauss(fx.profiles.wrap_delta(rect.path_t, progress) / 0.1)
color = fx.color.hsv2rgb(fx.math.fract(rect.path_t), 0.85, 1.0)
effect = fx.Effect(fx.color.rgba(color, band * sweep), p_min, p_max)
# effect 是纯数据;交给实现了 contract.md 的 renderer 绘制
```

## 核心机制

- **数值即 uniform**:表达式里的 Python 数字/元组自动提升为 uniform 槽位。
  每帧用新值重建同形状的树 → 命中同一个已编译程序。真常量用 `fx.const()`。
- **树形状即缓存 key**:`structure_key` 只哈希节点种类与 DAG 连接;
  同一对象复用两次只发射一次(CSE)。
- **热路径用 Template**:结构建一次,逐帧只按命名参数绑值(无树遍历):

```python
p = fx.TemplateParams()
r = fx.fields.RoundedRect(p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"))
glow = fx.Template(fx.color.rgba(p.vec3("rgb"), r.clip() * p.f("alpha")), p)
effect = glow.effect(q_min, q_max, p_min=a, p_max=b, rounding=8.0,
                     rgb=(1, 1, 1), alpha=0.5)   # ~微秒级
```

- **纪律红线**:禁止用运行时数值做 Python 分支改变树形状(每帧重编译);
  形状分支只允许配置型条件(stops 数量、corner mask 等)。

## 三个接触面

1. **构建特效**:词汇命名空间 `fx.math` / `fx.fields` / `fx.profiles` /
   `fx.color` / `fx.noise` / `fx.blocks`,以及 22 个预设 `fx.effects.*`
   (返回 `Effect`)。
2. **扩展词汇**:`fx.lib.register(name, src, deps)` 注册库函数
   (循环/分支写在库函数里,表达式层保持无分支),`fx.lib.call()` 调用。
   源码按 dialect 注册,GLSL 为默认。
3. **后端注入**:子类化 `fx.Dialect`(类型拼写 / 节点发射 / 库函数源 /
   外壳拼接),按 [contract.md](contract.md) 实现绘制。GLSL 家族后端通常
   只需覆写 `assemble`。

## 模块地图

```text
core/      类型 + AST 节点 + linearize/structure_key + Template/Effect
dialect.py Dialect 协议(后端注入接缝)
glsl/      内置 GLSL 方言 + 库函数源码(GL330 外壳)
lib.py     库函数注册表(按 dialect 维度)
math/fields/profiles/color/noise/blocks   词汇
effects.py 预设特效 + TemplateStore(warmup 用 preset_templates())
```

调试:`fx.dump_glsl(effect | template | expr)` 输出生成的着色器源码
(Template 会标注命名 uniform 槽位)。
