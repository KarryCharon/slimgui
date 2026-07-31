// PrimList: 保留式图元列表(retained display list)。
//
// 面向 "布局一次、逐帧回放" 的富文本/markdown 类控件: Python 侧在布局期把
// 文本与矩形图元灌进来并 finalize(按 y 稳定排序), 之后每帧一次 render()
// 调用完成可视区间二分裁剪 + 全部 ImDrawList 提交, 消除逐图元的跨语言开销。
#include "imgui_common.h"

#include <nanobind/stl/string_view.h>

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace {

struct Prim {
    uint8_t  kind;       // 0=text 1=rect_filled 2=rect(描边)
    int32_t  link_gid;   // 文本: 链接组 id (-1 无); hover 时整组换色
    float    x, y, w, h; // h 同时用于裁剪判定
    float    size;       // 文本: 字号; 矩形: 圆角
    float    extra;      // 文本: wrap 宽度(0 不换行); 描边矩形: 线宽
    ImU32    col;
    ImFont*  font;       // 仅文本; 字体由 atlas 持有, 生命周期长于本对象
    uint32_t text_ofs;
    uint32_t text_len;
};

} // namespace

class SlimguiPrimList {
public:
    void add_text(float x, float y, float h, ImFont* font, float size, uint32_t col,
                  std::string_view text, float wrap_w, int link_gid) {
        Prim p{};
        p.kind = 0;
        p.link_gid = link_gid;
        p.x = x; p.y = y; p.w = 0.0f; p.h = h;
        p.size = size;
        p.extra = wrap_w;
        p.col = col;
        p.font = font;
        p.text_ofs = (uint32_t)pool_.size();
        p.text_len = (uint32_t)text.size();
        pool_.append(text.data(), text.size());
        prims_.push_back(p);
    }

    void add_rect_filled(float x, float y, float w, float h, uint32_t col, float rounding) {
        Prim p{};
        p.kind = 1;
        p.link_gid = -1;
        p.x = x; p.y = y; p.w = w; p.h = h;
        p.size = rounding;
        p.col = col;
        prims_.push_back(p);
    }

    void add_rect(float x, float y, float w, float h, uint32_t col, float rounding, float thickness) {
        Prim p{};
        p.kind = 2;
        p.link_gid = -1;
        p.x = x; p.y = y; p.w = w; p.h = h;
        p.size = rounding;
        p.extra = thickness;
        p.col = col;
        prims_.push_back(p);
    }

    // 按 y 稳定排序(同 y 处保持插入次序: 底色先于文字), 建二分索引
    void finalize() {
        std::stable_sort(prims_.begin(), prims_.end(),
                         [](const Prim& a, const Prim& b) { return a.y < b.y; });
        ys_.resize(prims_.size());
        max_h_ = 0.0f;
        for (size_t i = 0; i < prims_.size(); i++) {
            ys_[i] = prims_[i].y;
            if (prims_[i].h > max_h_) max_h_ = prims_[i].h;
        }
        pool_.shrink_to_fit();
        prims_.shrink_to_fit();
    }

    void render(ImDrawList* dl, float ox, float oy, float clip_y0, float clip_y1,
                int hovered_gid, uint32_t hover_col) const {
        const size_t lo = std::lower_bound(ys_.begin(), ys_.end(), clip_y0 - oy - max_h_) - ys_.begin();
        const size_t hi = std::upper_bound(ys_.begin(), ys_.end(), clip_y1 - oy) - ys_.begin();
        const char* pool = pool_.data();
        for (size_t i = lo; i < hi; i++) {
            const Prim& p = prims_[i];
            const float py = oy + p.y;
            if (py + p.h < clip_y0)
                continue;
            const float px = ox + p.x;
            switch (p.kind) {
            case 0: {
                const ImU32 col = (p.link_gid >= 0 && p.link_gid == hovered_gid) ? hover_col : p.col;
                dl->AddText(p.font, p.size, ImVec2(px, py), col,
                            pool + p.text_ofs, pool + p.text_ofs + p.text_len, p.extra);
                break;
            }
            case 1:
                dl->AddRectFilled(ImVec2(px, py), ImVec2(px + p.w, py + p.h), p.col, p.size);
                break;
            default:
                dl->AddRect(ImVec2(px, py), ImVec2(px + p.w, py + p.h), p.col, p.size, 0, p.extra);
                break;
            }
        }
    }

    size_t size() const { return prims_.size(); }

private:
    std::vector<Prim> prims_;
    std::string pool_;         // 所有文本共用的 UTF-8 池(offset+len 引用)
    std::vector<float> ys_;
    float max_h_ = 0.0f;
};

void register_primlist(nb::module_& m) {
    nb::class_<SlimguiPrimList>(m, "PrimList",
        "Retained primitive list for layout-once / replay-per-frame widgets\n"
        "(e.g. markdown renderers). Fill with `add_*` at layout time, call\n"
        "`finalize()` once, then call `render()` each frame: it bisects the\n"
        "y-sorted primitives against the clip range and submits everything to\n"
        "the draw list in native code.")
        .def(nb::init<>())
        .def("add_text", &SlimguiPrimList::add_text,
             "x"_a, "y"_a, "h"_a, "font"_a, "size"_a, "col"_a, "text"_a,
             "wrap_w"_a = 0.0f, "link_gid"_a = -1,
             "Add a text primitive. `h` is the line height used for culling;\n"
             "`wrap_w` > 0 enables word wrap; `link_gid` >= 0 marks a hyperlink\n"
             "group recolored to `hover_col` when `render(hovered_gid=...)` matches.")
        .def("add_rect_filled", &SlimguiPrimList::add_rect_filled,
             "x"_a, "y"_a, "w"_a, "h"_a, "col"_a, "rounding"_a = 0.0f)
        .def("add_rect", &SlimguiPrimList::add_rect,
             "x"_a, "y"_a, "w"_a, "h"_a, "col"_a, "rounding"_a = 0.0f, "thickness"_a = 1.0f)
        .def("finalize", &SlimguiPrimList::finalize,
             "Stable-sort primitives by y and build the bisect index. Call once\n"
             "after all `add_*` calls; `render()` requires it.")
        .def("render", &SlimguiPrimList::render,
             "draw_list"_a, "ox"_a, "oy"_a, "clip_y0"_a, "clip_y1"_a,
             "hovered_gid"_a = -1, "hover_col"_a = 0,
             "Replay visible primitives into `draw_list` at origin (ox, oy),\n"
             "culled to the [clip_y0, clip_y1] screen-space range.")
        .def("__len__", &SlimguiPrimList::size);
}
