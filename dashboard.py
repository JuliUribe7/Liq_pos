# dashboard.py
import tkinter as tk
from tkinter import messagebox
from theme import Theme, bind_hover_effect

def open_dashboard(current_user: str, role: str):
    win = tk.Toplevel()
    win.title(f"LiquorPOS – Dashboard ({role})")
    win.geometry("900x600")
    win.config(**Theme.window_style())

    # Header section
    header_frame = tk.Frame(win, bg=Theme.BG_DARK)
    header_frame.pack(fill='x', pady=(30, 10))

    tk.Label(
        header_frame,
        text=f"Welcome, {current_user.title()}!",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold")
    ).pack()

    tk.Label(
        header_frame,
        text=f"Role: {role.upper()}",
        **Theme.secondary_label_style()
    ).pack(pady=(5, 0))

    # Main content frame
    content_frame = tk.Frame(win, **Theme.frame_style())
    content_frame.pack(pady=40, padx=60, expand=True, fill='both')

    # Grid frame for buttons
    btn_frame = tk.Frame(content_frame, bg=Theme.BG_FRAME)
    btn_frame.place(relx=0.5, rely=0.5, anchor='center')

    def make_button(parent, text, command, icon=""):
        """Create a themed dashboard button"""
        btn_container = tk.Frame(parent, bg=Theme.BG_FRAME)
        
        btn = tk.Button(
            btn_container,
            text=f"{icon}\n{text}" if icon else text,
            command=command,
            **Theme.button_style(),
            width=15,
            height=4
        )
        btn.pack()
        
        # Bind hover effect
        bind_hover_effect(btn)
        
        return btn_container

    # Button commands
    def open_inventory():
        try:
            from inventory_gui import open_inventory_window
            open_inventory_window()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Inventory: {str(e)}")

    def open_sales():
        try:
            from sales_gui import open_sales_window
            open_sales_window(current_user)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Sales: {str(e)}")

    def open_reports():
        try:
            from reports_gui import open_reports_window
            open_reports_window()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Reports: {str(e)}")

    def open_settings():
        settings_win = tk.Toplevel(win)
        settings_win.title("Settings")
        settings_win.geometry("450x400")
        settings_win.config(**Theme.window_style())
        settings_win.resizable(False, False)
        
        # Settings frame
        settings_frame = tk.Frame(settings_win, **Theme.frame_style())
        settings_frame.pack(padx=30, pady=30, fill='both', expand=True)
        
        tk.Label(
            settings_frame,
            text="Settings",
            bg=Theme.BG_FRAME,
            fg=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, 20, "bold")
        ).pack(pady=(20, 30))
        
        # User info frame
        info_frame = tk.Frame(settings_frame, bg=Theme.BG_FRAME)
        info_frame.pack(pady=20)
        
        tk.Label(
            info_frame,
            text="Current User:",
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack()
        
        tk.Label(
            info_frame,
            text=current_user,
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LARGE, 'bold')
        ).pack(pady=(5, 20))
        
        tk.Label(
            info_frame,
            text="Role:",
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack()
        
        tk.Label(
            info_frame,
            text=role.upper(),
            bg=Theme.BG_FRAME,
            fg=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LARGE, 'bold')
        ).pack(pady=(5, 0))

        def logout():
            settings_win.destroy()
            win.destroy()

        tk.Button(
            settings_frame,
            text="Logout",
            command=logout,
            bg="#DC3545",
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LARGE, "bold"),
            relief="flat",
            width=20,
            height=2,
            activebackground="#C82333",
            cursor='hand2'
        ).pack(pady=40)

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
    footer = tk.Label(
        win,
        text="LiquorPOS System 2025 ©",
        **Theme.secondary_label_style()
    )
    footer.pack(side="bottom", pady=20)

    # Center window on screen
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (win.winfo_width() // 2)
    y = (win.winfo_screenheight() // 2) - (win.winfo_height() // 2)
    win.geometry(f'+{x}+{y}')

    win.mainloop()