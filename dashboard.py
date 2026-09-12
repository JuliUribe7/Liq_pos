# dashboard.py
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from theme import Theme
from customer_display import (
    is_enabled as customer_display_enabled,
    set_enabled as set_customer_display_enabled,
    list_monitors as list_customer_display_monitors,
    get_monitor_choice as get_customer_display_monitor_choice,
    set_monitor_choice as set_customer_display_monitor_choice,
    get_resolution_override as get_customer_display_resolution,
    set_resolution_override as set_customer_display_resolution,
    get_header_lines as get_customer_display_header_lines,
    set_header_lines as set_customer_display_header_lines,
)
from ui_settings import (
    get_ui_scale, set_ui_scale, scale_dim, scale_geometry, position_main_window,
    get_main_monitor_choice, set_main_monitor_choice,
)

_RESOLUTION_OPTIONS = [
    "Auto (match monitor)",
    "1920x1080",
    "1366x768",
    "1280x1024",
    "1280x720",
    "1024x768",
    "800x600",
]

_UI_SCALE_OPTIONS = ["75%", "100%", "125%", "150%", "175%", "200%"]


def _monitor_key(m):
    return f"{m['left']},{m['top']},{m['right']},{m['bottom']}"


def _open_scrollable_window(parent, title, width):
    """Opens a CTkToplevel with a vertically scrollable content area, sized
    to fit its content up to 85% of screen height. Settings/Customize used
    to be fixed-size and non-resizable, so a large UI Scale could push
    buttons like "Customize" itself below the visible window with no way
    to reach or scroll to them — this makes that impossible regardless of
    font/UI scale. Uses a plain tk.Canvas + tk.Scrollbar for the scrolling
    mechanics rather than CTkScrollableFrame: that widget collapses to fit
    whatever content is currently packed into it instead of holding the
    fixed viewport size it's given, which left this window's content
    looking tiny and stranded in a corner — a plain Canvas holds an
    explicit width and reports its content's natural height accurately,
    which is exactly what's needed here. The widgets placed inside are
    still CustomTkinter (CTkButton, CTkLabel, etc.), so the CTk look is
    unaffected."""
    width = scale_dim(width)
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.configure(**Theme.ctk_window_style())
    win.resizable(False, True)

    canvas = tk.Canvas(win, bg=Theme.BG_FRAME, highlightthickness=0)
    scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    content = ctk.CTkFrame(canvas, fg_color=Theme.BG_FRAME, corner_radius=0)
    content_id = canvas.create_window((0, 0), window=content, anchor="nw", width=width)

    def sync_scrollregion(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    content.bind("<Configure>", sync_scrollregion)

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Only capture the mouse wheel while the pointer is actually over this
    # window's canvas, so it doesn't hijack scrolling in other windows.
    canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_mousewheel))
    canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

    def finalize():
        win.update_idletasks()
        max_height = int(win.winfo_screenheight() * 0.85)
        height = min(content.winfo_reqheight() + 4, max_height)
        win.geometry(f"{width + scrollbar.winfo_reqwidth()}x{height}")
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (win.winfo_width() // 2)
        y = (win.winfo_screenheight() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

    return win, content, finalize


def open_customize_window(parent):
    """Settings > Customize — everything related to the second-monitor
    customer display lives here: on/off, which physical monitor to use,
    what resolution to open it at, and its header text."""
    scale = get_ui_scale()
    win, scroll_content, finalize = _open_scrollable_window(parent, "Customize", 480)

    frame = ctk.CTkFrame(scroll_content, fg_color="transparent")
    frame.pack(padx=20, pady=20, fill="both", expand=True)

    ctk.CTkLabel(
        frame, text="Customize", fg_color="transparent", text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(20), "bold")
    ).pack(pady=(0, 20))

    ctk.CTkLabel(
        frame, text="Customer Display (2nd Monitor)", fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_LARGE), "bold")
    ).pack(pady=(0, 10))

    monitors = list_customer_display_monitors()
    has_second_monitor = any(not m['is_primary'] for m in monitors)
    cd_var = tk.BooleanVar(value=customer_display_enabled())

    def on_toggle_customer_display():
        set_customer_display_enabled(cd_var.get())

    # Always interactive, even with no second monitor connected — disabling
    # it whenever none is detected trapped anyone who'd enabled it during a
    # multi-monitor session and later moved to a single-monitor machine:
    # the box still showed checked but couldn't be clicked to turn back off.
    ctk.CTkCheckBox(
        frame,
        text="Enable Customer Display",
        variable=cd_var,
        command=on_toggle_customer_display,
        **Theme.ctk_checkbox_style(scale=scale)
    ).pack()

    if not has_second_monitor:
        ctk.CTkLabel(
            frame, text="No second monitor currently detected.", fg_color="transparent",
            text_color=Theme.TEXT_WARNING, font=(Theme.FONT_FAMILY, scale_dim(9))
        ).pack(pady=(5, 0))

    # Display text — 3 lines. Line 1 doubles as the cart-view header, and
    # all 3 show together on the idle screen when the cart is empty, so
    # both screens always match whatever's saved here.
    ctk.CTkLabel(
        frame, text="Display Text", fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
    ).pack(pady=(20, 5))

    current_line1, current_line2, current_line3 = get_customer_display_header_lines()
    line_vars = [
        tk.StringVar(value=current_line1),
        tk.StringVar(value=current_line2),
        tk.StringVar(value=current_line3),
    ]

    def save_header_lines(event=None):
        set_customer_display_header_lines(*(v.get() for v in line_vars))

    for i, var in enumerate(line_vars):
        line_row = ctk.CTkFrame(frame, fg_color="transparent")
        line_row.pack(pady=(0, 6))
        line_entry = ctk.CTkEntry(line_row, textvariable=var, width=scale_dim(260), **Theme.ctk_entry_style(scale=scale))
        line_entry.pack(side="left")
        line_entry.bind("<Return>", save_header_lines)
        line_entry.bind("<FocusOut>", save_header_lines)
        if i == 0:
            ctk.CTkButton(
                line_row, text="Save", command=save_header_lines, width=scale_dim(70), **Theme.ctk_button_style(scale=scale)
            ).pack(side="left", padx=(10, 0))

    # Target monitor — lets the user pick a specific physical monitor
    # instead of relying on auto-detection, for setups with more than one
    # secondary monitor or where auto-detect picks the wrong one.
    ctk.CTkLabel(
        frame, text="Target Monitor", fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
    ).pack(pady=(20, 5))

    monitor_values = {"Auto (first secondary monitor)": "auto"}
    for m in monitors:
        w, h = m['right'] - m['left'], m['bottom'] - m['top']
        label = f"{w}x{h} at ({m['left']}, {m['top']})"
        if m['is_primary']:
            label += " [Primary]"
        monitor_values[label] = _monitor_key(m)

    current_monitor_choice = get_customer_display_monitor_choice()
    current_monitor_label = next(
        (label for label, value in monitor_values.items() if value == current_monitor_choice),
        "Auto (first secondary monitor)"
    )
    monitor_var = tk.StringVar(value=current_monitor_label)

    def on_monitor_change(selected):
        set_customer_display_monitor_choice(monitor_values[selected])

    ctk.CTkOptionMenu(
        frame, variable=monitor_var, values=list(monitor_values.keys()),
        command=on_monitor_change, **Theme.ctk_option_menu_style(scale=scale)
    ).pack(fill="x", padx=40)

    # Resolution — overrides the window size used on the target monitor,
    # for setups where the detected monitor resolution isn't what's wanted.
    ctk.CTkLabel(
        frame, text="Resolution", fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
    ).pack(pady=(20, 5))

    current_resolution = get_customer_display_resolution()
    resolution_options = _RESOLUTION_OPTIONS[:]
    if current_resolution != "auto" and current_resolution not in resolution_options:
        resolution_options.append(current_resolution)

    resolution_var = tk.StringVar(
        value="Auto (match monitor)" if current_resolution == "auto" else current_resolution
    )

    def on_resolution_change(selected):
        set_customer_display_resolution("auto" if selected.startswith("Auto") else selected)

    ctk.CTkOptionMenu(
        frame, variable=resolution_var, values=resolution_options,
        command=on_resolution_change, **Theme.ctk_option_menu_style(scale=scale)
    ).pack(fill="x", padx=40)

    ctk.CTkLabel(
        frame,
        text="Target monitor, resolution and display text take effect\nnext time Sales is opened.",
        fg_color="transparent", text_color=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, scale_dim(9)), justify="center"
    ).pack(pady=(20, 0))

    ctk.CTkFrame(frame, fg_color=Theme.TEXT_SECONDARY, height=1, corner_radius=0).pack(fill="x", padx=20, pady=(25, 15))

    # Main Monitor — the app's own windows (login, dashboard, sales, etc.)
    # all render at a fixed 96-DPI font scale so the customer display's
    # text doesn't blow up on a differently-scaled secondary monitor. That
    # pin also flattens scaling for these main windows, so on a primary
    # monitor set to a higher Windows scaling %, everything can end up
    # looking small — this lets that be sized back up manually.
    ctk.CTkLabel(
        frame, text="Main Monitor", fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_LARGE), "bold")
    ).pack(pady=(0, 10))

    # Target monitor — which physical monitor the main app (login,
    # dashboard, sales, inventory, reports) opens/maximizes on. Mirrors
    # the customer display's own Target Monitor picker above.
    ctk.CTkLabel(
        frame, text="Target Monitor", fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
    ).pack(pady=(0, 5))

    main_monitor_values = {"Auto (primary monitor)": "auto"}
    for m in monitors:
        w, h = m['right'] - m['left'], m['bottom'] - m['top']
        label = f"{w}x{h} at ({m['left']}, {m['top']})"
        if m['is_primary']:
            label += " [Primary]"
        main_monitor_values[label] = _monitor_key(m)

    current_main_monitor_choice = get_main_monitor_choice()
    current_main_monitor_label = next(
        (label for label, value in main_monitor_values.items() if value == current_main_monitor_choice),
        "Auto (primary monitor)"
    )
    main_monitor_var = tk.StringVar(value=current_main_monitor_label)

    def on_main_monitor_change(selected):
        set_main_monitor_choice(main_monitor_values[selected])

    ctk.CTkOptionMenu(
        frame, variable=main_monitor_var, values=list(main_monitor_values.keys()),
        command=on_main_monitor_change, **Theme.ctk_option_menu_style(scale=scale)
    ).pack(fill="x", padx=40)

    ctk.CTkLabel(
        frame,
        text="Takes effect the next time each screen is opened.\nEach screen always opens full-screen on this monitor.",
        fg_color="transparent", text_color=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, scale_dim(9)), justify="center"
    ).pack(pady=(8, 0))

    ctk.CTkLabel(
        frame, text="UI Scale", fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
    ).pack(pady=(15, 5))

    current_ui_scale = get_ui_scale()
    current_ui_scale_label = f"{round(current_ui_scale * 100)}%"
    ui_scale_options = _UI_SCALE_OPTIONS[:]
    if current_ui_scale_label not in ui_scale_options:
        ui_scale_options.append(current_ui_scale_label)

    ui_scale_var = tk.StringVar(value=current_ui_scale_label)

    def on_ui_scale_change(selected):
        try:
            set_ui_scale(int(selected.rstrip("%")) / 100)
        except ValueError:
            pass

    ctk.CTkOptionMenu(
        frame, variable=ui_scale_var, values=ui_scale_options,
        command=on_ui_scale_change, **Theme.ctk_option_menu_style(scale=scale)
    ).pack(fill="x", padx=40)

    ctk.CTkLabel(
        frame,
        text="If the app looks too small or too large on your main\nscreen, adjust this. Takes effect after restarting the app.",
        fg_color="transparent", text_color=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, scale_dim(9)), justify="center"
    ).pack(pady=(8, 0))

    ctk.CTkButton(
        frame, text="Close", command=win.destroy, **Theme.ctk_button_style(scale=scale)
    ).pack(pady=(20, 0))

    finalize()


def open_dashboard(current_user: str, role: str, root=None):
    scale = get_ui_scale()
    win = ctk.CTkToplevel()
    win.title(f"LiquorPOS – Dashboard ({role})")
    win.geometry(scale_geometry(900, 600))
    win.configure(**Theme.ctk_window_style())
    # Deferred via after() rather than called immediately: CTk does its own
    # deferred window setup (scaling sync, title bar work) right after
    # creation, and calling this synchronously can lose a race against
    # that — the window ends up back at its small initial size a moment
    # later. Running after a short delay guarantees this is the last thing
    # to touch the window's state.
    win.after(60, lambda: position_main_window(win))

    def quit_app():
        win.destroy()
        if root is not None:
            root.destroy()

    win.protocol("WM_DELETE_WINDOW", quit_app)

    # Header section
    header_frame = ctk.CTkFrame(win, fg_color=Theme.BG_DARK, corner_radius=0)
    header_frame.pack(fill='x', pady=(30, 10))

    ctk.CTkLabel(
        header_frame,
        text=f"Welcome, {current_user.title()}!",
        fg_color="transparent",
        text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_TITLE), "bold")
    ).pack()

    ctk.CTkLabel(
        header_frame,
        text=f"Role: {role.upper()}",
        **Theme.ctk_secondary_label_style(scale=scale)
    ).pack(pady=(5, 0))

    # Main content frame
    content_frame = ctk.CTkFrame(win, **Theme.ctk_frame_style())
    content_frame.pack(pady=40, padx=60, expand=True, fill='both')

    # Grid frame for buttons
    btn_frame = ctk.CTkFrame(content_frame, fg_color=Theme.BG_FRAME)
    btn_frame.place(relx=0.5, rely=0.5, anchor='center')

    def make_button(parent, text, command, icon=""):
        """Create a themed dashboard button"""
        btn_container = ctk.CTkFrame(parent, fg_color=Theme.BG_FRAME)

        btn = ctk.CTkButton(
            btn_container,
            text=f"{icon}\n{text}" if icon else text,
            command=command,
            **Theme.ctk_button_style(scale=scale),
            width=scale_dim(180),
            height=scale_dim(110)
        )
        btn.pack()

        return btn_container

    # Tracks the single open instance of each screen (keyed by name) so
    # clicking a dashboard button twice brings the existing window back to
    # front instead of opening a duplicate.
    open_screens = {}

    def _open_or_focus(name, opener):
        existing = open_screens.get(name)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return
        try:
            open_screens[name] = opener()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {name}: {str(e)}")

    # Button commands
    def open_inventory():
        def opener():
            from inventory_gui import open_inventory_window
            return open_inventory_window()
        _open_or_focus("Inventory", opener)

    def open_sales():
        def opener():
            from sales_gui import open_sales_window
            return open_sales_window(current_user)
        _open_or_focus("Sales", opener)

    def open_reports():
        def opener():
            from reports_gui import open_reports_window
            return open_reports_window(current_user)
        _open_or_focus("Reports", opener)

    def open_settings():
        settings_win, scroll_content, finalize = _open_scrollable_window(win, "Settings", 450)

        settings_frame = ctk.CTkFrame(scroll_content, fg_color="transparent")
        settings_frame.pack(padx=20, pady=20, fill='both', expand=True)

        ctk.CTkLabel(
            settings_frame,
            text="Settings",
            fg_color="transparent",
            text_color=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, scale_dim(20), "bold")
        ).pack(pady=(20, 30))

        # User info frame
        info_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        info_frame.pack(pady=20)

        ctk.CTkLabel(
            info_frame,
            text="Current User:",
            fg_color="transparent",
            text_color=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
        ).pack()

        ctk.CTkLabel(
            info_frame,
            text=current_user,
            fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_LARGE), 'bold')
        ).pack(pady=(5, 20))

        ctk.CTkLabel(
            info_frame,
            text="Role:",
            fg_color="transparent",
            text_color=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL))
        ).pack()

        ctk.CTkLabel(
            info_frame,
            text=role.upper(),
            fg_color="transparent",
            text_color=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_LARGE), 'bold')
        ).pack(pady=(5, 0))

        # Customize — customer display on/off, target monitor, resolution,
        # and header text all live in their own window off this button.
        ctk.CTkButton(
            settings_frame,
            text="Customize",
            command=lambda: open_customize_window(settings_win),
            **Theme.ctk_button_style(scale=scale)
        ).pack(pady=20)

        finalize()

    # Create buttons with icons (using Unicode symbols)
    btn_inventory = make_button(btn_frame, "Inventory", open_inventory, "📦")
    btn_sales = make_button(btn_frame, "Sales", open_sales, "💰")
    btn_reports = make_button(btn_frame, "Reports", open_reports, "📊")
    btn_settings = make_button(btn_frame, "Settings", open_settings, "⚙️")

    # Layout buttons in grid
    btn_inventory.grid(row=0, column=0, padx=25, pady=20)
    btn_sales.grid(row=0, column=1, padx=25, pady=20)
    btn_reports.grid(row=1, column=0, padx=25, pady=20)
    btn_settings.grid(row=1, column=1, padx=25, pady=20)

    # Footer
    footer = ctk.CTkLabel(
        win,
        text="LiquorPOS System 2025 ©",
        **Theme.ctk_secondary_label_style(scale=scale)
    )
    footer.pack(side="bottom", pady=20)
