# ui_settings.py
"""App-wide UI settings not tied to any specific feature (unlike
customer_display.py's settings). Currently just the main-window UI scale,
which compensates for Tk's font scaling being pinned to a fixed 96 DPI
ratio (see login_gui.py) so multi-monitor DPI-awareness doesn't break the
customer display — that pin also flattens scaling for every other window,
so this lets a user on a high-DPI primary monitor size the app back up.
"""
import os

from dotenv import load_dotenv, set_key

from customer_display import list_monitors, monitor_key

load_dotenv()
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

_DEFAULT_UI_SCALE = 1.5


def get_ui_scale():
    load_dotenv(override=True)
    value = (os.getenv("UI_SCALE") or "").strip().strip('"').strip("'")
    try:
        scale = float(value)
        return scale if scale > 0 else _DEFAULT_UI_SCALE
    except ValueError:
        return _DEFAULT_UI_SCALE


def set_ui_scale(value):
    try:
        scale = float(value)
        if scale <= 0:
            scale = _DEFAULT_UI_SCALE
    except (TypeError, ValueError):
        scale = _DEFAULT_UI_SCALE
    set_key(_ENV_PATH, "UI_SCALE", str(scale))


def scale_dim(value):
    """Scales a single pixel dimension by the saved UI scale. 'tk scaling'
    only affects font point sizes, not literal pixel values passed to
    .geometry()/.place(width=,height=) — so those need scaling separately
    for the whole window (not just its text) to actually grow."""
    return round(value * get_ui_scale())


def scale_geometry(width, height):
    """Scales a window's width/height for use in .geometry(), e.g.
    scale_geometry(900, 600) -> "1350x900" at 150% UI scale."""
    return f"{scale_dim(width)}x{scale_dim(height)}"


def get_main_monitor_choice():
    """Returns "auto" or a saved monitor_key() string — mirrors
    customer_display's Target Monitor picker, but for the main app's own
    windows (login, dashboard, sales, inventory, reports)."""
    load_dotenv(override=True)
    value = (os.getenv("MAIN_MONITOR") or "").strip().strip('"').strip("'")
    return value or "auto"


def set_main_monitor_choice(value):
    set_key(_ENV_PATH, "MAIN_MONITOR", value or "auto")


def _resolve_main_monitor():
    monitors = list_monitors()
    if not monitors:
        return None

    choice = get_main_monitor_choice()
    if choice != "auto":
        chosen = next((m for m in monitors if monitor_key(m) == choice), None)
        if chosen is not None:
            return chosen

    # Auto: the main app defaults to the primary monitor (unlike the
    # customer display, which defaults to the first *non*-primary one).
    return next((m for m in monitors if m['is_primary']), monitors[0])


def position_main_window(win):
    """Maximizes a main-app window onto the target monitor from Settings >
    Customize > Main Monitor (default: the primary monitor). Call this
    after the window's initial .geometry() call, which still sets its
    restored/un-maximized size (used if the window is later un-maximized).
    A per-window fixed-size override used to exist here too, but it kept
    getting mistaken for "tell the app my screen resolution" and left
    people stuck with a small windowed app instead of full screen — removed
    in favor of always maximizing, which is what every real deployment of
    this app actually wants."""
    monitor = _resolve_main_monitor()

    if monitor is not None:
        # Move the window onto the target monitor before maximizing —
        # Windows maximizes a window onto whichever monitor it currently
        # occupies, so this has to happen first.
        win.geometry(f"+{monitor['left'] + 20}+{monitor['top'] + 20}")
        win.update_idletasks()

    win.state('zoomed')
