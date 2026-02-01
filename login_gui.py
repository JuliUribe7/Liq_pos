# login_gui.py
import tkinter as tk
from tkinter import messagebox
from utils import verify_password
from db import get_user_by_username, create_user
from dashboard import open_dashboard
from theme import Theme, bind_hover_effect


def try_login(username: str, password: str):
    row = get_user_by_username(username.strip())
    if not row:
        return False, "User not found."
    _uname, stored_hash, role, active = row
    if not active:
        return False, "Account is inactive."
    if not verify_password(password, stored_hash):
        return False, "Incorrect password."
    return True, role


def open_create_account_window(parent):
    win = tk.Toplevel(parent)
    win.title("LiquorPOS – Create Account")
    win.geometry("450x620")
    win.config(**Theme.window_style())
    win.resizable(False, False)

    main_frame = tk.Frame(win, **Theme.frame_style())
    main_frame.place(relx=0.5, rely=0.5, anchor="center", width=380, height=600)

    # Title
    tk.Label(
        main_frame,
        text="Create Account",
        bg=Theme.BG_FRAME,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 20, "bold"),
    ).pack(pady=(25, 5))

    tk.Label(
        main_frame,
        text="Add a new user for the system",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, 10),
    ).pack(pady=(0, 20))

    # Username
    tk.Label(
        main_frame,
        text="Username",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
    ).pack(anchor="w", padx=40, pady=(10, 5))

    e_user = tk.Entry(main_frame, **Theme.entry_style())
    e_user.pack(padx=40, pady=(0, 10), fill="x", ipady=6)

    # Password
    tk.Label(
        main_frame,
        text="Password",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
    ).pack(anchor="w", padx=40, pady=(10, 5))

    e_pass = tk.Entry(main_frame, show="●", **Theme.entry_style())
    e_pass.pack(padx=40, pady=(0, 10), fill="x", ipady=6)

    # Confirm Password
    tk.Label(
        main_frame,
        text="Confirm Password",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
    ).pack(anchor="w", padx=40, pady=(10, 5))

    e_confirm = tk.Entry(main_frame, show="●", **Theme.entry_style())
    e_confirm.pack(padx=40, pady=(0, 15), fill="x", ipady=6)

    # Role dropdown
    tk.Label(
        main_frame,
        text="Role",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
    ).pack(anchor="w", padx=40, pady=(5, 5))

    role_var = tk.StringVar(value="cashier")
    role_menu = tk.OptionMenu(main_frame, role_var, "cashier", "admin")
    role_menu.config(
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        highlightthickness=0,
        bd=0,
        activebackground=Theme.BG_FRAME,
        activeforeground=Theme.TEXT_PRIMARY,
    )
    role_menu["menu"].config(bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY)
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

    btn_create = tk.Button(
        main_frame,
        text="Create Account",
        command=on_create,
        **Theme.primary_button_style(),
        height=2,
    )
    btn_create.pack(padx=40, pady=(10, 0), fill="x")
    bind_hover_effect(btn_create)


def run_login():
    root = tk.Tk()
    root.title("LiquorPOS – Login")
    root.geometry("450x620")
    root.config(**Theme.window_style())
    root.resizable(False, False)

    # Main container frame
    main_frame = tk.Frame(root, **Theme.frame_style())
    main_frame.place(relx=0.5, rely=0.5, anchor='center', width=380, height=550)

    # Logo/Title section
    title = tk.Label(
        main_frame,
        text="LiquorPOS",
        bg=Theme.BG_FRAME,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 28, 'bold')
    )
    title.pack(pady=(40, 10))

    subtitle = tk.Label(
        main_frame,
        text="Point of Sale System",
        **Theme.secondary_label_style()
    )
    subtitle.config(bg=Theme.BG_FRAME)
    subtitle.pack(pady=(0, 40))

    # Username section
    tk.Label(
        main_frame,
        text="Username",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, 'bold')
    ).pack(anchor='w', padx=40, pady=(10, 5))

    e_user = tk.Entry(main_frame, **Theme.entry_style())
    e_user.pack(padx=40, pady=(0, 20), fill='x', ipady=8)

    # Password section
    tk.Label(
        main_frame,
        text="Password",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, 'bold')
    ).pack(anchor='w', padx=40, pady=(10, 5))

    e_pass = tk.Entry(main_frame, show="●", **Theme.entry_style())
    e_pass.pack(padx=40, pady=(0, 20), fill='x', ipady=8)

    def on_login():
        ok, msg = try_login(e_user.get(), e_pass.get())
        if ok:
            role = msg
            root.withdraw()
            open_dashboard(current_user=e_user.get(), role=role)
        else:
            messagebox.showerror("Login Failed", msg)
            e_pass.delete(0, tk.END)

    # Login button
    btn_login = tk.Button(
        main_frame,
        text="Login",
        command=on_login,
        **Theme.primary_button_style(),
        height=2
    )
    btn_login.pack(padx=40, pady=(0, 10), fill='x')
    bind_hover_effect(btn_login)

    # Create Account button
    btn_create = tk.Button(
        main_frame,
        text="Create Account",
        command=lambda: open_create_account_window(root),
        **Theme.primary_button_style(),
        height=2
    )
    btn_create.pack(padx=40, pady=(0, 15), fill='x')
    bind_hover_effect(btn_create)

    # Bind Enter key to login
    e_pass.bind('<Return>', lambda e: on_login())
    e_user.bind('<Return>', lambda e: e_pass.focus())

    # Footer info (you can keep or update this text)
    info_frame = tk.Frame(main_frame, bg=Theme.BG_FRAME)
    info_frame.pack(side='bottom', pady=20)

    tk.Label(
        info_frame,
        text="Use 'Create Account' to add new users.",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_SECONDARY,
        font=(Theme.FONT_FAMILY, 9)
    ).pack()

    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f'+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    run_login()