#!/usr/bin/env python3
"""
Interactive callback test harness for slimgui.

Run with:  python tests/test_callbacks_interactive.py

Uses GLFW + OpenGL backend. Each callback type has a dedicated section in the UI.
A status panel at the bottom shows which callbacks have actually fired.
Press ESC to quit.
"""

import glfw
import OpenGL.GL as gl
import math
from slimgui import imgui
from slimgui.integrations.glfw import GlfwRenderer

# ---------------------------------------------------------------------------
# Callback fire tracker
# ---------------------------------------------------------------------------
class CallbackTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.fired = {
            "DrawList.add_callback": 0,
            "DrawList.reset_render_state": 0,
            "SizeConstraint": 0,
            "InputText.Always": 0,
            "InputText.CharFilter": 0,
            "InputText.Completion": 0,
            "InputText.History": 0,
            "InputText.Edit": 0,
            "Combo.getter": 0,
            "ListBox.getter": 0,
            "PlotLines.getter": 0,
            "PlotHistogram.getter": 0,
            "PlatformIO.GetClipboard": 0,
            "PlatformIO.SetClipboard": 0,
            "MultiSelect.AdapterIdx": 0,
        }
        self.last_events: list[str] = []

    def fire(self, name: str, detail: str = ""):
        self.fired[name] = self.fired.get(name, 0) + 1
        msg = f"{name}: {detail}" if detail else name
        self.last_events.append(msg)
        if len(self.last_events) > 20:
            self.last_events.pop(0)

tracker = CallbackTracker()

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_esc_pressed = False
input_text_val = "Type here"
input_text_filter_val = "no digits"
input_text_completion_val = ""
input_text_history_val = ""
input_text_edit_val = "edit me"
combo_current = 0
listbox_current = 0
constraint_window_open = True
multiselect_selected: set[int] = set()

HISTORY_ITEMS = ["alpha", "beta", "gamma", "delta", "epsilon"]
history_pos = -1

# ---------------------------------------------------------------------------
# Callback implementations
# ---------------------------------------------------------------------------

def drawlist_callback(dl, cmd, userdata):
    tracker.fire("DrawList.add_callback", f"userdata={userdata}")

def size_constraint_callback(data):
    tracker.fire("SizeConstraint", f"desired={data.desired_size}")
    # Force square
    mx = max(data.desired_size[0], data.desired_size[1])
    data.desired_size = (mx, mx)

def input_text_always_cb(data):
    tracker.fire("InputText.Always", f"buf_len={data.buf_text_len}")
    return 0

def input_text_char_filter_cb(data):
    ch = chr(data.event_char) if data.event_char < 0x10000 else '?'
    if ch.isdigit():
        tracker.fire("InputText.CharFilter", f"blocked digit '{ch}'")
        return 1  # discard
    tracker.fire("InputText.CharFilter", f"allowed '{ch}'")
    return 0

def input_text_completion_cb(data):
    tracker.fire("InputText.Completion", "TAB pressed")
    data.insert_chars(data.cursor_pos, "completed!")
    return 0

def input_text_history_cb(data):
    global history_pos
    if data.event_key == imgui.Key.KEY_UP_ARROW:
        history_pos = min(history_pos + 1, len(HISTORY_ITEMS) - 1)
    elif data.event_key == imgui.Key.KEY_DOWN_ARROW:
        history_pos = max(history_pos - 1, -1)
    if history_pos >= 0:
        text = HISTORY_ITEMS[history_pos]
        tracker.fire("InputText.History", f"pos={history_pos} -> '{text}'")
        data.delete_chars(0, data.buf_text_len)
        data.insert_chars(0, text)
    else:
        tracker.fire("InputText.History", "pos=-1 (empty)")
        data.delete_chars(0, data.buf_text_len)
    return 0

def input_text_edit_cb(data):
    tracker.fire("InputText.Edit", f"buf='{data.buf}'")
    return 0

def combo_getter(idx):
    items = ["Apple", "Banana", "Cherry", "Date", "Elderberry"]
    tracker.fire("Combo.getter", f"idx={idx}")
    return items[idx]

def listbox_getter(idx):
    items = ["Red", "Green", "Blue", "Yellow", "Cyan", "Magenta"]
    tracker.fire("ListBox.getter", f"idx={idx}")
    return items[idx]

def plot_lines_getter(idx):
    tracker.fire("PlotLines.getter", f"idx={idx}")
    return math.sin(idx * 0.1) * 50

def plot_histogram_getter(idx):
    tracker.fire("PlotHistogram.getter", f"idx={idx}")
    return abs(math.sin(idx * 0.5)) * 100

# ---------------------------------------------------------------------------
# UI drawing
# ---------------------------------------------------------------------------

def draw_ui():
    global input_text_val, input_text_filter_val, input_text_completion_val
    global input_text_history_val, input_text_edit_val
    global combo_current, listbox_current, constraint_window_open

    imgui.set_next_window_size((700, 600), imgui.Cond.FIRST_USE_EVER)
    imgui.begin("Callback Test Harness")

    if imgui.button("Reset Tracker"):
        tracker.reset()
    imgui.same_line()
    imgui.text(f"Total events: {sum(tracker.fired.values())}")

    imgui.separator()

    # --- DrawList callbacks ---
    if imgui.collapsing_header("DrawList Callbacks")[0]:
        imgui.text("DrawList callbacks fire during render. Check status panel below.")
        dl = imgui.get_window_draw_list()
        dl.add_callback(drawlist_callback, 42)
        dl.add_callback(drawlist_callback, b"hello")
        dl.add_reset_render_state_callback()

    # --- SizeConstraint callback ---
    if imgui.collapsing_header("SizeConstraint Callback")[0]:
        imgui.text("Resize the 'Constrained Window' below — it's forced to be square.")
        imgui.set_next_window_size_constraints((100, 100), (500, 500), size_constraint_callback)
        imgui.set_next_window_size((200, 200), imgui.Cond.FIRST_USE_EVER)
        _, constraint_window_open = imgui.begin("Constrained Window (square)")
        imgui.text("Resize me!")
        imgui.end()

    # --- InputText callbacks ---
    if imgui.collapsing_header("InputText Callbacks")[0]:
        imgui.text("CallbackAlways — fires every frame while focused:")
        _, input_text_val = imgui.input_text("##always", input_text_val,
            imgui.InputTextFlags.CALLBACK_ALWAYS, callback=input_text_always_cb)

        imgui.text("CallbackCharFilter — blocks digits:")
        _, input_text_filter_val = imgui.input_text("##charfilter", input_text_filter_val,
            imgui.InputTextFlags.CALLBACK_CHAR_FILTER, callback=input_text_char_filter_cb)

        imgui.text("CallbackCompletion — press TAB to insert 'completed!':")
        _, input_text_completion_val = imgui.input_text("##completion", input_text_completion_val,
            imgui.InputTextFlags.CALLBACK_COMPLETION, callback=input_text_completion_cb)

        imgui.text("CallbackHistory — press Up/Down to cycle history:")
        _, input_text_history_val = imgui.input_text("##history", input_text_history_val,
            imgui.InputTextFlags.CALLBACK_HISTORY, callback=input_text_history_cb)

        imgui.text("CallbackEdit — fires on each edit:")
        _, input_text_edit_val = imgui.input_text("##edit", input_text_edit_val,
            imgui.InputTextFlags.CALLBACK_EDIT, callback=input_text_edit_cb)

    # --- Combo/ListBox getter ---
    if imgui.collapsing_header("Combo/ListBox Getter Callbacks")[0]:
        _, combo_current = imgui.combo("##combo_getter", combo_current, combo_getter, 5)
        _, listbox_current = imgui.list_box("##listbox_getter", listbox_current, listbox_getter, 6)

    # --- Plot getter ---
    if imgui.collapsing_header("Plot Getter Callbacks")[0]:
        imgui.plot_lines("##plotlines_getter", plot_lines_getter, 200)
        imgui.plot_histogram("##plothist_getter", plot_histogram_getter, 50)

    # --- MultiSelect ---
    if imgui.collapsing_header("MultiSelect Adapter")[0]:
        storage = imgui.SelectionBasicStorage()
        ids = list(range(1000, 1010))
        call_count = [0]
        def ms_adapter(idx):
            call_count[0] += 1
            tracker.fire("MultiSelect.AdapterIdx", f"idx={idx}")
            return ids[idx]
        storage.adapter_index_to_storage_id = ms_adapter

        ms_io = imgui.begin_multi_select(imgui.MultiSelectFlags.CLEAR_ON_ESCAPE | imgui.MultiSelectFlags.BOX_SELECT1D, storage.size, len(ids))
        storage.apply_requests(ms_io)
        for i, item_id in enumerate(ids):
            imgui.set_next_item_selection_user_data(i)
            selected = storage.contains(item_id)
            _, selected = imgui.selectable(f"MS Item {i} (id={item_id})", selected)
        ms_io = imgui.end_multi_select()
        storage.apply_requests(ms_io)
        imgui.text(f"Adapter called {call_count[0]} times this frame")

    imgui.separator()

    # --- Status panel ---
    imgui.text("=== Callback Fire Status ===")
    for name, count in tracker.fired.items():
        color = (0.0, 1.0, 0.0, 1.0) if count > 0 else (0.5, 0.5, 0.5, 1.0)
        imgui.text_colored(color, f"  {name}: {count}")

    imgui.separator()
    imgui.text("=== Recent Events (last 20) ===")
    for evt in tracker.last_events:
        imgui.text(f"  {evt}")

    imgui.end()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def _key_callback(_window, key, _scan, action, _mods):
    global _esc_pressed
    if action == glfw.PRESS and key == glfw.KEY_ESCAPE:
        _esc_pressed = True

def main():
    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(900, 700, "slimgui Callback Test Harness", None, None)
    glfw.make_context_current(window)

    imgui.create_context()
    io = imgui.get_io()
    io.config_flags |= imgui.ConfigFlags.NAV_ENABLE_KEYBOARD
    io.ini_filename = None
    renderer = GlfwRenderer(window, prev_key_callback=_key_callback)

    # Wire up PlatformIO clipboard hooks for testing
    clipboard_buf = [""]
    def get_clipboard():
        tracker.fire("PlatformIO.GetClipboard", f"len={len(clipboard_buf[0])}")
        return clipboard_buf[0]
    def set_clipboard(text):
        tracker.fire("PlatformIO.SetClipboard", f"len={len(text)}")
        clipboard_buf[0] = text

    plat_io = imgui.get_platform_io()
    plat_io.platform_get_clipboard_text_fn = get_clipboard
    plat_io.platform_set_clipboard_text_fn = set_clipboard

    while not (glfw.window_should_close(window) or _esc_pressed):
        glfw.poll_events()
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT))
        renderer.new_frame()
        imgui.new_frame()

        draw_ui()

        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    renderer.shutdown()
    imgui.destroy_context(None)
    glfw.terminate()

if __name__ == "__main__":
    main()
