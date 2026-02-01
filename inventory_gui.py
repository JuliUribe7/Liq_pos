# inventory_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from db import get_conn
from theme import Theme, bind_hover_effect

def open_inventory_window():
    win = tk.Toplevel()
    win.title("Inventory Management")
    win.geometry("1400x700")
    win.config(**Theme.window_style())

    # Configure ttk style for treeview
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Treeview",
                    background=Theme.BG_BUTTON,
                    foreground=Theme.TEXT_PRIMARY,
                    fieldbackground=Theme.BG_BUTTON,
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    background=Theme.BG_FRAME,
                    foreground=Theme.ACCENT_GOLD,
                    relief="flat",
                    font=(Theme.FONT_FAMILY, 11, 'bold'))
    style.map('Treeview', background=[('selected', Theme.ACCENT_GOLD)])

    # Header
    header_frame = tk.Frame(win, bg=Theme.BG_DARK)
    header_frame.pack(fill='x', pady=(20, 10))

    tk.Label(
        header_frame,
        text="Inventory Management",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 20, "bold")
    ).pack()

    # Main container
    main_container = tk.Frame(win, bg=Theme.BG_DARK)
    main_container.pack(fill='both', expand=True, padx=20, pady=10)

    # Search Frame
    search_frame = tk.Frame(main_container, **Theme.frame_style())
    search_frame.pack(pady=(0, 15), fill="x")

    search_inner = tk.Frame(search_frame, bg=Theme.BG_FRAME)
    search_inner.pack(padx=20, pady=15)

    tk.Label(
        search_inner,
        text="Search:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(side="left", padx=(0, 10))

    search_entry = tk.Entry(search_inner, **Theme.entry_style(), width=40)
    search_entry.pack(side="left", padx=5, ipady=6)

    def search_items():
        search_term = search_entry.get().strip()
        load_inventory(search_term)

    search_btn = tk.Button(
        search_inner,
        text="Search",
        command=search_items,
        **Theme.button_style(),
        width=10
    )
    search_btn.pack(side="left", padx=5)
    bind_hover_effect(search_btn)

    refresh_btn = tk.Button(
        search_inner,
        text="Refresh",
        command=lambda: load_inventory(),
        **Theme.button_style(),
        width=10
    )
    refresh_btn.pack(side="left", padx=5)
    bind_hover_effect(refresh_btn)

    # Treeview Frame
    tree_frame = tk.Frame(main_container, **Theme.frame_style())
    tree_frame.pack(fill="both", expand=True, pady=(0, 15))

    # Scrollbars
    vsb = ttk.Scrollbar(tree_frame, orient="vertical")
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

    # Treeview
    columns = ("Item ID", "Barcode", "Brand", "Size", "Type", "Price", "Cost", "Quantity", "Supplier")
    tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set
    )

    vsb.config(command=tree.yview)
    hsb.config(command=tree.xview)

    # Column headings
    for col in columns:
        tree.heading(col, text=col)

    # Column widths
    tree.column("Item ID", width=70)
    tree.column("Barcode", width=130)
    tree.column("Brand", width=280)
    tree.column("Size", width=90)
    tree.column("Type", width=120)
    tree.column("Price", width=90)
    tree.column("Cost", width=90)
    tree.column("Quantity", width=90)
    tree.column("Supplier", width=180)

    tree.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
    vsb.grid(row=0, column=1, sticky="ns", pady=15)
    hsb.grid(row=1, column=0, sticky="ew", padx=15)

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Load inventory data
    def load_inventory(search_term=""):
        for item in tree.get_children():
            tree.delete(item)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                if search_term:
                    query = """
                        SELECT 
                            i.item_id, i.barcode, i.brand, i.size, i.type,
                            i.price, i.cost, inv.quantity, s.company_name
                        FROM items i
                        LEFT JOIN inventory inv ON i.item_id = inv.item_id
                        LEFT JOIN suppliers s ON i.supplier_id = s.supplier_id
                        WHERE 
                            LOWER(i.brand) LIKE LOWER(%s) OR
                            i.barcode LIKE %s OR
                            LOWER(i.type) LIKE LOWER(%s)
                        ORDER BY i.item_id
                    """
                    search_pattern = f"%{search_term}%"
                    cur.execute(query, (search_pattern, search_pattern, search_pattern))
                else:
                    query = """
                        SELECT 
                            i.item_id, i.barcode, i.brand, i.size, i.type,
                            i.price, i.cost, inv.quantity, s.company_name
                        FROM items i
                        LEFT JOIN inventory inv ON i.item_id = inv.item_id
                        LEFT JOIN suppliers s ON i.supplier_id = s.supplier_id
                        ORDER BY i.item_id
                    """
                    cur.execute(query)

                rows = cur.fetchall()
                for row in rows:
                    tree.insert("", "end", values=(
                        row[0], row[1] or "", row[2] or "", row[3] or "",
                        row[4] or "", f"{row[5]:.2f}" if row[5] else "0.00",
                        f"{row[6]:.2f}" if row[6] else "0.00",
                        row[7] if row[7] is not None else 0, row[8] or "N/A"
                    ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory: {str(e)}")

    # Action buttons frame
    action_frame = tk.Frame(main_container, **Theme.frame_style())
    action_frame.pack(pady=10)

    action_inner = tk.Frame(action_frame, bg=Theme.BG_FRAME)
    action_inner.pack(padx=20, pady=15)

    def update_quantity():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an item to update.")
            return

        item = tree.item(selected[0])
        item_id = item['values'][0]
        current_qty = item['values'][7]

        # Create update dialog
        dialog = tk.Toplevel(win)
        dialog.title("Update Quantity")
        dialog.geometry("400x250")
        dialog.config(**Theme.window_style())
        dialog.resizable(False, False)

        dialog_frame = tk.Frame(dialog, **Theme.frame_style())
        dialog_frame.pack(padx=30, pady=30, fill='both', expand=True)

        tk.Label(
            dialog_frame,
            text="Update Quantity",
            bg=Theme.BG_FRAME,
            fg=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, 16, 'bold')
        ).pack(pady=(10, 20))

        tk.Label(
            dialog_frame,
            text=f"Current Quantity: {current_qty}",
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 12)
        ).pack(pady=10)

        tk.Label(
            dialog_frame,
            text="New Quantity:",
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, 11, 'bold')
        ).pack(pady=(10, 5))
        
        qty_entry = tk.Entry(dialog_frame, **Theme.entry_style(), width=20)
        qty_entry.pack(pady=5, ipady=6)
        qty_entry.insert(0, str(current_qty))
        qty_entry.focus()
        qty_entry.select_range(0, tk.END)

        def save_quantity():
            try:
                new_qty = int(qty_entry.get())
                conn = get_conn()
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE inventory 
                        SET quantity = %s 
                        WHERE item_id = %s
                    """, (new_qty, item_id))
                    conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Quantity updated successfully!")
                dialog.destroy()
                load_inventory()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update: {str(e)}")

        # Button frame for Save and Cancel
        btn_frame = tk.Frame(dialog_frame, bg=Theme.BG_FRAME)
        btn_frame.pack(pady=20)

        save_btn = tk.Button(
            btn_frame,
            text="Save",
            command=save_quantity,
            **Theme.primary_button_style(),
            width=12
        )
        save_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            bg=Theme.BG_BUTTON,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
            relief="flat",
            width=12,
            activebackground=Theme.BG_BUTTON_HOVER,
            cursor='hand2'
        )
        cancel_btn.pack(side="left", padx=5)

        # Bind Enter key to save
        qty_entry.bind('<Return>', lambda e: save_quantity())
        
        # Center dialog on parent window
        dialog.transient(win)
        dialog.grab_set()
        dialog.update_idletasks()
        x = win.winfo_x() + (win.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = win.winfo_y() + (win.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

    update_btn = tk.Button(
        action_inner,
        text="Update Quantity",
        command=update_quantity,
        **Theme.button_style(),
        width=18
    )
    update_btn.pack(side="left", padx=10)
    bind_hover_effect(update_btn)

    def show_low_stock():
        for item in tree.get_children():
            tree.delete(item)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        i.item_id, i.barcode, i.brand, i.size, i.type,
                        i.price, i.cost, inv.quantity, s.company_name
                    FROM items i
                    LEFT JOIN inventory inv ON i.item_id = inv.item_id
                    LEFT JOIN suppliers s ON i.supplier_id = s.supplier_id
                    WHERE inv.quantity <= 5
                    ORDER BY inv.quantity
                """)
                rows = cur.fetchall()
                for row in rows:
                    tree.insert("", "end", values=(
                        row[0], row[1] or "", row[2] or "", row[3] or "",
                        row[4] or "", f"{row[5]:.2f}" if row[5] else "0.00",
                        f"{row[6]:.2f}" if row[6] else "0.00",
                        row[7] if row[7] is not None else 0, row[8] or "N/A"
                    ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load low stock items: {str(e)}")

    low_stock_btn = tk.Button(
        action_inner,
        text="Show Low Stock",
        command=show_low_stock,
        **Theme.button_style(),
        width=18
    )
    low_stock_btn.pack(side="left", padx=10)
    bind_hover_effect(low_stock_btn)

    # Back button
    back_btn = tk.Button(
        action_inner,
        text="← Back",
        command=win.destroy,
        bg="#DC3545",
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
        relief="flat",
        width=12,
        activebackground="#C82333",
        cursor='hand2'
    )
    back_btn.pack(side="left", padx=10)

    # Load initial data
    load_inventory()

    # Bind Enter key to search
    search_entry.bind('<Return>', lambda e: search_items())