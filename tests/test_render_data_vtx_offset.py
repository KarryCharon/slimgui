"""get_render_data 必须把 VtxOffset 折进预切索引:启用 RendererHasVtxOffset
后,>64k 顶点的 draw list 会产生基址相对的 16 位索引;没有 BaseVertex 绘制
能力的消费方(如 Blender gpu)依赖这里还原为全局索引。"""

from slimgui import imgui


def test_render_data_folds_vtx_offset():
    ctx = imgui.create_context()
    try:
        io = imgui.get_io()
        io.display_size = (4096, 4096)
        io.backend_flags |= imgui.BackendFlags.RENDERER_HAS_TEXTURES
        io.backend_flags |= imgui.BackendFlags.RENDERER_HAS_VTX_OFFSET

        imgui.new_frame()
        dl = imgui.get_foreground_draw_list()
        n_rects = 20000  # 4 vtx each -> 80k 顶点, 必然跨越 64k 边界
        for i in range(n_rects):
            x = float(i % 200) * 4.0
            y = float(i // 200) * 4.0
            dl.add_rect_filled((x, y), (x + 3.0, y + 3.0), 0xFF00FF00)
        imgui.render()

        checked_cmds = 0
        max_index_seen = -1
        for cmds in imgui.get_draw_data().commands_lists:
            positions, _uvs, _colors, cmd_list = cmds.get_render_data()
            vtx_count = positions.shape[0]
            for _tex, _clip, indices, callback, _ud in cmd_list:
                if callback is not None or len(indices) == 0:
                    continue
                checked_cmds += 1
                assert int(indices.max()) < vtx_count, "index out of vertex range"
                max_index_seen = max(max_index_seen, int(indices.max()))

        assert checked_cmds >= 2, "expected the big draw list to split into multiple commands"
        # 关键断言: 折叠后必须出现超过 16 位寻址范围的全局索引
        assert max_index_seen > 0xFFFF, (
            f"vtx_offset not folded into indices (max index {max_index_seen})"
        )
    finally:
        imgui.destroy_context(ctx)
