# login_gui.py
import ctypes
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from utils import verify_password
from db import get_user_by_username, create_user
from dashboard import open_dashboard
from theme import Theme
from ui_settings import get_ui_scale, scale_dim, scale_geometry, position_main_window


def _make_process_dpi_aware():
    """Without this, Windows silently scales/repositions everything the app
    draws on a secondary monitor whenever it has a different DPI scaling
    setting than the primary monitor — Tkinter's .geometry() coordinates and
    win32api.EnumDisplayMonitors()'s reported rects stop matching what's
    actually on screen, which is what made the customer display render its
    content off to one side / partly off-screen. Must run before any Tk
    window (even the login window) is created."""
    try:
        # PER_MONITOR_AWARE_V2 — best behavior on Windows 10 1703+.
        # DPI_AWARENESS_CONTEXT is a pointer-sized HANDLE; without declaring
        # argtypes, ctypes marshals the -4 sentinel as a 32-bit int, which
        # doesn't sign-extend correctly on 64-bit Windows and makes this
        # call silently fail (returns 0, no exception) — the process was
        # left DPI-unaware the whole time despite this code appearing to
        # set it, which is what caused the customer display to stay
        # off-center no matter what else was changed.
        user32 = ctypes.windll.user32
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_int
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4).value):
            return
    except Exception:
        pass
    try:
        # PER_MONITOR_DPI_AWARE fallback for older Windows 8.1/10 builds.
        # Returns an HRESULT; S_OK is 0.
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_make_process_dpi_aware()

# CustomTkinter tries to set its own process DPI awareness the first time a
# CTk/CTkToplevel is created. Our own DPI-awareness call above (needed for
# the customer display's per-monitor positioning) has to be the one that
# wins, so CTk's automatic version is turned off here rather than letting
# the two potentially race or disagree.
ctk.deactivate_automatic_dpi_awareness()
ctk.set_appearance_mode("dark")

# CTk recolors each window's title bar dark on Windows by briefly hiding
# the window, changing the color, then restoring whatever state it was in
# right before that dance started — captured at window-creation time,
# which is before our own code maximizes it via position_main_window().
# If that restore fires after our maximize call, it silently un-maximizes
# the window a moment later. Disabling this (purely cosmetic, and not
# visibly taking effect anyway) removes that race entirely.
ctk.CTk._deactivate_windows_window_header_manipulation = True
ctk.CTkToplevel._deactivate_windows_window_header_manipulation = True

_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60
_failed_attempts: dict[str, int] = {}
_lockout_until: dict[str, float] = {}


def _is_locked_out(username: str) -> bool:
    until = _lockout_until.get(username)
    if until is None:
        return False
    if time.time() >= until:
        _failed_attempts.pop(username, None)
        _lockout_until.pop(username, None)
        return False
    return True


def _record_failed_attempt(username: str) -> None:
    attempts = _failed_attempts.get(username, 0) + 1
    _failed_attempts[username] = attempts
    if attempts >= _MAX_FAILED_ATTEMPTS:
        _lockout_until[username] = time.time() + _LOCKOUT_SECONDS


def _clear_login_attempts(username: str) -> None:
    _failed_attempts.pop(username, None)
    _lockout_until.pop(username, None)


def try_login(username: str, password: str):
    username = username.strip()
    password = password.strip()
    if not username or not password:
        return False, "Invalid username or password."

    if _is_locked_out(username):
        return False, "Too many failed attempts. Try again in a moment."

    row = get_user_by_username(username)
    if not row:
        _record_failed_attempt(username)
        return False, "Invalid username or password."
    _uname, stored_hash, role, active = row
    if not active:
        return False, "Account is inactive."
    if not verify_password(password, stored_hash):
        _record_failed_attempt(username)
        return False, "Invalid username or password."

    _clear_login_attempts(username)
    return True, role


def open_create_account_window(parent):
    scale = get_ui_scale()
    win = ctk.CTkToplevel(parent)
    win.title("LiquorPOS – Create Account")
    win.geometry(scale_geometry(450, 620))
    win.configure(**Theme.ctk_window_style())
    win.resizable(False, False)

    main_frame = ctk.CTkFrame(win, width=scale_dim(380), height=scale_dim(600), **Theme.ctk_frame_style())
    main_frame.place(relx=0.5, rely=0.5, anchor="center")
    # Without this, the frame shrinks to fit its packed children instead
    # of holding the explicit width/height above — CTkFrame doesn't lock
    # its own size the way tk.Frame + place(width=,height=) used to. This
    # is what was actually causing the login/create-account cards to
    # render far smaller than intended: the width/height above were being
    # silently ignored in favor of the frame auto-fitting its content.
    main_frame.pack_propagate(False)

    # Title
    ctk.CTkLabel(
        main_frame,
        text="Create Account",
        fg_color="transparent",
        text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(20), "bold"),
    ).pack(pady=(25, 5))

    ctk.CTkLabel(
        main_frame,
        text="Add a new user for the system",
        fg_color="transparent",
        text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(10)),
    ).pack(pady=(0, 20))

    # Username
    ctk.CTkLabel(
        main_frame,
        text="Username",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), "bold"),
        anchor="w",
    ).pack(anchor="w", padx=40, pady=(10, 5))

    e_user = ctk.CTkEntry(main_frame, **Theme.ctk_entry_style(scale=scale))
    e_user.pack(padx=40, pady=(0, 10), fill="x")

    # Password
    ctk.CTkLabel(
        main_frame,
        text="Password",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), "bold"),
        anchor="w",
    ).pack(anchor="w", padx=40, pady=(10, 5))

    e_pass = ctk.CTkEntry(main_frame, show="●", **Theme.ctk_entry_style(scale=scale))
    e_pass.pack(padx=40, pady=(0, 10), fill="x")

    # Confirm Password
    ctk.CTkLabel(
        main_frame,
        text="Confirm Password",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), "bold"),
        anchor="w",
    ).pack(anchor="w", padx=40, pady=(10, 5))

    e_confirm = ctk.CTkEntry(main_frame, show="●", **Theme.ctk_entry_style(scale=scale))
    e_confirm.pack(padx=40, pady=(0, 15), fill="x")

    # Role dropdown
    ctk.CTkLabel(
        main_frame,
        text="Role",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), "bold"),
        anchor="w",
    ).pack(anchor="w", padx=40, pady=(5, 5))

    role_var = tk.StringVar(value="cashier")
    role_menu = ctk.CTkOptionMenu(
        main_frame, variable=role_var, values=["cashier", "admin"],
        **Theme.ctk_option_menu_style(scale=scale)
    )
    role_menu.pack(padx=40, pady=(0, 20), fill="x")

    def on_create():
        username = e_user.get().strip()
        pw1 = e_pass.get()
        pw2 = e_confirm.get()
        role = role_var.get()

        if not username or not pw1:
            messagebox.showerror("Error", "Username and password are required.")
            return
        if pw1 != pw2:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        try:
            create_user(username, pw1, role)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create user:\n{e}")
            return

        messagebox.showinfo("Success", f"User '{username}' created.")
        win.destroy()

    btn_create = ctk.CTkButton(
        main_frame,
        text="Create Account",
        command=on_create,
        **Theme.ctk_primary_button_style(scale=scale),
        height=scale_dim(40),
    )
    btn_create.pack(padx=40, pady=(10, 0), fill="x")


def run_login():
    scale = get_ui_scale()
    root = ctk.CTk()
    # Pin Tk's own point-to-pixel scaling to the classic 96 DPI ratio,
    # times the user's chosen UI scale (Settings > Customize, default
    # 100%). Without this pin, making the process DPI-aware (above) causes
    # Tk to auto-scale every font's point size to match whatever DPI
    # Windows reports for the monitor a window is on — on a secondary
    # monitor with a different scaling %, that blew fonts up far past
    # their layout slice and shoved content into a corner instead of
    # centering it. Pinning it keeps font-to-pixel sizing identical on
    # every monitor regardless of its Windows scaling setting, while still
    # letting the DPI-awareness call above give correct real-pixel window
    # placement/geometry — but it also means the main app windows no
    # longer auto-adjust to the primary monitor's own scaling, hence the
    # separate manual UI Scale knob to size them back up if needed.
    #
    # CTk normally auto-detects the real per-monitor DPI and scales its
    # own widgets to match it with zero extra code — but that relies on
    # its own DPI-awareness setup, which we deliberately disabled above
    # (ctk.deactivate_automatic_dpi_awareness()) so it wouldn't conflict
    # with our own PER_MONITOR_AWARE_V2 call. Disabling that also disables
    # CTk's auto-scaling entirely (confirmed: it drops to a flat 1.0
    # regardless of the real monitor), so CTk widgets need scale_dim()/
    # scale_geometry() applied manually too — including font point sizes
    # via Theme.ctk_*_style(scale=...), since this pin does not affect
    # CTk's fonts at all (confirmed separately).
    root.tk.call('tk', 'scaling', (96 / 72) * scale)
    root.title("LiquorPOS – Login")
    root.geometry(scale_geometry(450, 620))
    root.configure(**Theme.ctk_window_style())
    root.resizable(False, False)
    # Fill the screen instead of floating as a small fixed-size window —
    # the login card below is centered with .place(), so it still renders
    # as a normal-looking centered card, just on a full-screen background.
    # Honors Settings > Customize > Main Monitor's Target Monitor choice.
    # Deferred via after() rather than called immediately: CTk does its
    # own deferred window setup (scaling sync, title bar work) right after
    # creation, and calling this synchronously can lose a race against
    # that — the window ends up back at its small initial size a moment
    # later. Running after a short delay guarantees this is the last thing
    # to touch the window's state.
    root.after(60, lambda: position_main_window(root))

    # Main container frame
    main_frame = ctk.CTkFrame(root, width=scale_dim(380), height=scale_dim(550), **Theme.ctk_frame_style())
    # Without this, the frame shrinks to fit its packed children instead
    # of holding the explicit width/height above — this was what was
    # actually causing the login card to render far smaller than intended.
    main_frame.pack_propagate(False)
    main_frame.place(relx=0.5, rely=0.5, anchor='center')
    # place()'s relx/rely is supposed to auto-recenter whenever root
    # resizes, but that didn't reliably happen after the deferred maximize
    # above on at least one real machine, leaving the card stuck centered
    # against the small pre-maximize window size instead. Explicitly
    # re-issuing the same place() call on every <Configure> guarantees
    # correct centering regardless of that timing quirk.
    root.bind('<Configure>', lambda e: main_frame.place(relx=0.5, rely=0.5, anchor='center'))

    # Logo/Title section
    title = ctk.CTkLabel(
        main_frame,
        text="LiquorPOS",
        fg_color="transparent",
        text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(28), 'bold')
    )
    title.pack(pady=(40, 10))

    subtitle = ctk.CTkLabel(
        main_frame,
        text="Point of Sale System",
        **Theme.ctk_secondary_label_style(scale=scale)
    )
    subtitle.pack(pady=(0, 40))

    # Username section
    ctk.CTkLabel(
        main_frame,
        text="Username",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), 'bold'),
        anchor='w',
    ).pack(anchor='w', padx=40, pady=(10, 5))

    e_user = ctk.CTkEntry(main_frame, **Theme.ctk_entry_style(scale=scale))
    e_user.pack(padx=40, pady=(0, 20), fill='x')

    # Password section
    ctk.CTkLabel(
        main_frame,
        text="Password",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), 'bold'),
        anchor='w',
    ).pack(anchor='w', padx=40, pady=(10, 5))

    e_pass = ctk.CTkEntry(main_frame, show="●", **Theme.ctk_entry_style(scale=scale))
    e_pass.pack(padx=40, pady=(0, 20), fill='x')

    def on_login():
        ok, msg = try_login(e_user.get(), e_pass.get())
        if ok:
            role = msg
            root.withdraw()
            open_dashboard(current_user=e_user.get(), role=role, root=root)
        else:
            messagebox.showerror("Login Failed", msg)
            e_pass.delete(0, tk.END)

    # Login button
    btn_login = ctk.CTkButton(
        main_frame,
        text="Login",
        command=on_login,
        **Theme.ctk_primary_button_style(scale=scale),
        height=scale_dim(40),
    )
    btn_login.pack(padx=40, pady=(0, 10), fill='x')

    # Create Account button
    btn_create = ctk.CTkButton(
        main_frame,
        text="Create Account",
        command=lambda: open_create_account_window(root),
        **Theme.ctk_primary_button_style(scale=scale),
        height=scale_dim(40),
    )
    btn_create.pack(padx=40, pady=(0, 15), fill='x')

    # Bind Enter key to login
    e_pass.bind('<Return>', lambda e: on_login())
    e_user.bind('<Return>', lambda e: e_pass.focus())

    # Footer info
    info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    info_frame.pack(side='bottom', pady=20)

    ctk.CTkLabel(
        info_frame,
        text="Use 'Create Account' to add new users.",
        fg_color="transparent",
        text_color=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, scale_dim(9))
    ).pack()

    root.mainloop()


if __name__ == "__main__":
    run_login()
