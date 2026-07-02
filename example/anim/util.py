import tempfile
import fragfx
import urllib.request

from pathlib import Path
from slimgui import imgui


CHINESE_FONT_URL = "https://github.com/lxgw/LxgwWenKai/releases/download/v1.522/LXGWWenKai-Regular.ttf"
CHINESE_FONT_CACHE = Path(tempfile.gettempdir()) / "slimgui-chinese-font" / "LXGWWenKai-Regular.ttf"
CHINESE_FONT_SIZE = 14.0


def download_chinese_font() -> Path | None:
    if CHINESE_FONT_CACHE.exists() and CHINESE_FONT_CACHE.stat().st_size > 1024 * 1024:
        return CHINESE_FONT_CACHE

    try:
        CHINESE_FONT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(CHINESE_FONT_URL, timeout=20.0) as response:
            font_data = response.read()
        tmp_path = CHINESE_FONT_CACHE.with_suffix(".tmp")
        tmp_path.write_bytes(font_data)
        tmp_path.replace(CHINESE_FONT_CACHE)
        return CHINESE_FONT_CACHE
    except OSError as exc:
        print(f"Chinese font download skipped: {exc}")
        return None


def load_chinese_font(size: float = CHINESE_FONT_SIZE) -> None:
    font_path = download_chinese_font()
    if font_path is None:
        return

    try:
        imgui.get_io().fonts.add_font_from_memory_ttf(font_path.read_bytes(), size)
    except RuntimeError as exc:
        print(f"Chinese font load skipped: {exc}")


def _unsupported_renderer(_dl: object, _cmd: object, _effect: object) -> None:
    """Shared callback behind every emitted effect: a shader-capable renderer
    dispatches `cmd.callback_userdata` and never runs this; a renderer that
    blindly runs callbacks lands here (fail-fast for unsupported backends)."""
    raise RuntimeError(
        "this renderer does not draw fragfx effects"
        + " (it ran the effect callback instead of dispatching cmd.callback_userdata)"
    )


def emit(draw_list: "imgui.DrawList", effect: "fragfx.Effect | None") -> None:
    """Queue an effect as draw-list callback userdata (module-level callback:
    no per-call closure allocation). `None` effects are ignored."""
    if effect is None:
        return
    draw_list.add_callback(_unsupported_renderer, effect)
