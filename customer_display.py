# customer_display.py
"""Second-monitor customer-facing display: mirrors the current cart and
running total so the customer can watch what's being rung up, separate
from the cashier's own screen. Setting persists in .env like PRINTER_NAME.
"""
import os

import tkinter as tk
import win32api
from dotenv import load_dotenv, set_key

from theme import Theme
from receipt import STORE_NAME, STORE_ADDRESS, STORE_PHONE

load_dotenv()
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def is_enabled():
    load_dotenv(override=True)
    value = (os.getenv("CUSTOMER_DISPLAY_ENABLED") or "").strip().strip('"').strip("'").lower()
    return value == "true"


def set_enabled(value):
    set_key(_ENV_PATH, "CUSTOMER_DISPLAY_ENABLED", "true" if value else "false")


_DEFAULT_LINES = (STORE_NAME, STORE_ADDRESS, STORE_PHONE)


def get_header_lines():
    """Returns the 3 customizable display lines as a tuple. These drive
    both the idle screen (all 3 lines) and the cart-view header (line 1)
    — previously the idle screen showed the hardcoded STORE_NAME/ADDRESS/
    PHONE from receipt.py regardless of what was set in Settings >
    Customize, so the two screens could show different text; pulling both
    from the same saved lines keeps them always in sync."""
    load_dotenv(override=True)
    lines = []
    for i in range(1, 4):
        value = (os.getenv(f"CUSTOMER_DISPLAY_LINE{i}") or "").strip().strip('"').strip("'")
        lines.append(value or _DEFAULT_LINES[i - 1])
    return tuple(lines)


def set_header_lines(line1, line2, line3):
    for i, value in enumerate((line1, line2, line3), start=1):
        value = (value or "").strip()
        set_key(_ENV_PATH, f"CUSTOMER_DISPLAY_LINE{i}", value or _DEFAULT_LINES[i - 1])


def get_secondary_monitor_rect():
    """Returns (x, y, width, height) of the first non-primary monitor, or
    None if only one monitor is connected. The primary monitor's origin is
    always (0, 0) in Windows' virtual screen coordinates, so anything else
    is a secondary monitor."""
    try:
        monitors = win32api.EnumDisplayMonitors()
    except Exception:
        return None
    for _hmon, _hdc, rect in monitors:
        left, top, right, bottom = rect
        if (left, top) != (0, 0):
            return (left, top, right - left, bottom - top)
    return None


def list_monitors():
    """Returns every connected monitor as
    {'left', 'top', 'right', 'bottom', 'is_primary'} dicts, for populating
    the Target Monitor picker in Settings > Customize."""
    try:
        monitors = win32api.EnumDisplayMonitors()
    except Exception:
        return []
    result = []
    for _hmon, _hdc, rect in monitors:
        left, top, right, bottom = rect
        result.append({
            'left': left, 'top': top, 'right': right, 'bottom': bottom,
            'is_primary': (left, top) == (0, 0),
        })
    return result


def monitor_key(m):
    return f"{m['left']},{m['top']},{m['right']},{m['bottom']}"


def get_monitor_choice():
    """Returns "auto" or a saved "left,top,right,bottom" monitor key."""
    load_dotenv(override=True)
    value = (os.getenv("CUSTOMER_DISPLAY_MONITOR") or "").strip().strip('"').strip("'")
    return value or "auto"


def set_monitor_choice(value):
    set_key(_ENV_PATH, "CUSTOMER_DISPLAY_MONITOR", value or "auto")


def get_resolution_override():
    """Returns "auto" or a saved "WIDTHxHEIGHT" string."""
    load_dotenv(override=True)
    value = (os.getenv("CUSTOMER_DISPLAY_RESOLUTION") or "").strip().strip('"').strip("'")
    return value or "auto"


def set_resolution_override(value):
    set_key(_ENV_PATH, "CUSTOMER_DISPLAY_RESOLUTION", value or "auto")


def get_customer_display_rect():
    """Resolves the (x, y, width, height) rect to actually open the
    customer display at, honoring the saved Target Monitor + Resolution
    choices from Settings > Customize. Falls back to the first non-primary
    monitor if the saved monitor is "auto" or no longer matches a connected
    monitor (e.g. it was unplugged or moved)."""
    monitors = list_monitors()
    if not monitors:
        return None

    choice = get_monitor_choice()
    chosen = None
    if choice != "auto":
        chosen = next((m for m in monitors if monitor_key(m) == choice), None)

    if chosen is None:
        chosen = next((m for m in monitors if not m['is_primary']), None)

    if chosen is None:
        return None

    x, y = chosen['left'], chosen['top']
    width, height = chosen['right'] - chosen['left'], chosen['bottom'] - chosen['top']

    resolution = get_resolution_override()
    if resolution != "auto":
        try:
            w_str, h_str = resolution.lower().split("x")
            width, height = int(w_str), int(h_str)
        except ValueError:
            pass

    return (x, y, width, height)


def open_customer_display(parent_win):
    """Opens a borderless window filling the secondary monitor. Returns a
    dict of hooks {'update': fn, 'show_idle': fn} for the caller to push
    cart changes into, or None if no secondary monitor is available. The
    window is parented to parent_win, so it closes automatically when the
    Sales window does — no separate cleanup needed."""
    rect = get_customer_display_rect()
    if rect is None:
        return None

    x, y, width, height = rect

    win = tk.Toplevel(parent_win)
    win.overrideredirect(True)
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.config(bg=Theme.BG_DARK)

    # A borderless window's very first .geometry() call can land slightly
    # off on a secondary monitor — Windows hasn't finished associating the
    # new window with that monitor's DPI context yet when it's applied.
    # Forcing the window to realize (update_idletasks) and then reapplying
    # the same geometry snaps it to the correct spot.
    win.update_idletasks()
    win.geometry(f"{width}x{height}+{x}+{y}")

    idle_frame = tk.Frame(win, bg=Theme.BG_DARK)
    # place(relx/rely=0.5, anchor="center") pins this block to the exact
    # middle of idle_frame regardless of its actual pixel size — unlike
    # pack(expand=True) stacked with other widgets, whose "centered" slice
    # can end up skewed to a corner if font rendering size ever changes.
    line1, line2, line3 = get_header_lines()

    idle_content = tk.Frame(idle_frame, bg=Theme.BG_DARK)
    idle_content.place(relx=0.5, rely=0.5, anchor="center")
    tk.Label(
        idle_content, text=line1, bg=Theme.BG_DARK, fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 48, "bold"), justify="center"
    ).pack()
    tk.Label(
        idle_content, text=line2, bg=Theme.BG_DARK, fg=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, 18), justify="center"
    ).pack(pady=(20, 0))
    tk.Label(
        idle_content, text=line3, bg=Theme.BG_DARK, fg=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, 18), justify="center"
    ).pack()

    cart_frame = tk.Frame(win, bg=Theme.BG_DARK)
    header_label = tk.Label(
        cart_frame, text=line1, bg=Theme.BG_DARK, fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 28, "bold"), justify="center", anchor="center"
    )
    header_label.pack(fill="x", pady=(20, 10))

    items_container = tk.Frame(cart_frame, bg=Theme.BG_DARK)
    items_container.pack(fill="both", expand=True, padx=40, pady=10)

    breakdown_frame = tk.Frame(cart_frame, bg=Theme.BG_DARK)
    breakdown_frame.pack(fill="x", padx=40, pady=(0, 20))

    total_label = tk.Label(
        cart_frame, text="Total: $0.00", bg=Theme.BG_DARK, fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 40, "bold")
    )
    total_label.pack(pady=(0, 30))

    def show_idle():
        cart_frame.pack_forget()
        idle_frame.pack(fill="both", expand=True)

    def _breakdown_row(label, value):
        row = tk.Frame(breakdown_frame, bg=Theme.BG_DARK)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=Theme.BG_DARK, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 14)).pack(side="left")
        tk.Label(row, text=value, bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                 font=(Theme.FONT_FAMILY, 14, "bold")).pack(side="right")

    def update(cart_items, totals):
        if not cart_items:
            show_idle()
            return

        idle_frame.pack_forget()
        cart_frame.pack(fill="both", expand=True)

        for w in items_container.winfo_children():
            w.destroy()
        for item in cart_items:
            name = item['brand']
            if item.get('is_custom'):
                name += " (Custom)"
            line_total = item['quantity'] * item['price']
            row = tk.Frame(items_container, bg=Theme.BG_DARK)
            row.pack(fill="x", pady=2)
            tk.Label(
                row, text=f"{item['quantity']} x {name}", bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                font=(Theme.FONT_FAMILY, 16), anchor="w"
            ).pack(side="left")
            tk.Label(
                row, text=f"${line_total:.2f}", bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
                font=(Theme.FONT_FAMILY, 16, "bold"), anchor="e"
            ).pack(side="right")

        for w in breakdown_frame.winfo_children():
            w.destroy()
        _breakdown_row("Subtotal", f"${totals['subtotal']:.2f}")
        if totals['discount_amount'] > 0:
            _breakdown_row("Discount", f"-${totals['discount_amount']:.2f}")
        _breakdown_row("Tax", f"${totals['tax_amount']:.2f}")
        if totals['deposit_amount'] > 0:
            _breakdown_row("Deposit", f"${totals['deposit_amount']:.2f}")

        total_label.config(text=f"Total: ${totals['total']:.2f}")

    show_idle()
    return {'update': update, 'show_idle': show_idle}
