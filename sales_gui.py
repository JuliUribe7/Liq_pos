# sales_gui.py
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from db import get_conn
from theme import Theme, bind_hover_effect

def open_sales_window(current_user: str):
    win = tk.Toplevel()
    win.title("Sales/POS")
    win.geometry("1400x850")
    win.config(**Theme.window_style())

    # Configure ttk style
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
        text="Point of Sale",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 20, "bold")
    ).pack()

    tk.Label(
        header_frame,
        text=f"Cashier: {current_user}",
        **Theme.secondary_label_style()
    ).pack()

    # Main container
    main_frame = tk.Frame(win, bg=Theme.BG_DARK)
    main_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # Left side - Product search and selection
    left_frame = tk.Frame(main_frame, **Theme.frame_style())
    left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

    # Search section
    search_frame = tk.Frame(left_frame, bg=Theme.BG_FRAME)
    search_frame.pack(pady=15, padx=15, fill="x")

    tk.Label(
        search_frame,
        text="Scan Barcode:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(anchor="w", pady=(0, 5))

    barcode_entry = tk.Entry(search_frame, **Theme.entry_style())
    barcode_entry.pack(fill="x", pady=5, ipady=6)

    tk.Label(
        search_frame,
        text="Search Product:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(anchor="w", pady=(0, 5))

    search_entry = tk.Entry(search_frame, **Theme.entry_style())
    search_entry.pack(fill="x", pady=5, ipady=6)

    # Product list
    tk.Label(
        left_frame,
        text="Available Products:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 12, "bold")
    ).pack(pady=(10, 5), padx=15)
    
    product_frame = tk.Frame(left_frame, bg=Theme.BG_FRAME)
    product_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))

    product_scroll = ttk.Scrollbar(product_frame)
    product_scroll.pack(side="right", fill="y")

    product_columns = ("ID", "Brand", "Size", "Price", "Stock")
    product_tree = ttk.Treeview(
        product_frame,
        columns=product_columns,
        show="headings",
        yscrollcommand=product_scroll.set,
        height=18
    )
    product_scroll.config(command=product_tree.yview)

    product_tree.heading("ID", text="ID")
    product_tree.heading("Brand", text="Brand")
    product_tree.heading("Size", text="Size")
    product_tree.heading("Price", text="Price")
    product_tree.heading("Stock", text="Stock")

    product_tree.column("ID", width=50)
    product_tree.column("Brand", width=300)
    product_tree.column("Size", width=80)
    product_tree.column("Price", width=80)
    product_tree.column("Stock", width=70)

    product_tree.pack(side="left", fill="both", expand=True)

    # Right side - Cart and checkout
    right_frame = tk.Frame(main_frame, **Theme.frame_style(), width=450)
    right_frame.pack(side="right", fill="both")
    right_frame.pack_propagate(False)

    tk.Label(
        right_frame,
        text="Shopping Cart",
        bg=Theme.BG_FRAME,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 14, "bold")
    ).pack(pady=(15, 10))

    # Cart treeview
    cart_frame = tk.Frame(right_frame, bg=Theme.BG_FRAME)
    cart_frame.pack(fill="both", expand=True, padx=15)

    cart_scroll = ttk.Scrollbar(cart_frame)
    cart_scroll.pack(side="right", fill="y")

    cart_columns = ("Item", "Qty", "Price", "Total")
    cart_tree = ttk.Treeview(
        cart_frame,
        columns=cart_columns,
        show="headings",
        yscrollcommand=cart_scroll.set,
        height=10
    )
    cart_scroll.config(command=cart_tree.yview)

    cart_tree.heading("Item", text="Item")
    cart_tree.heading("Qty", text="Qty")
    cart_tree.heading("Price", text="Price")
    cart_tree.heading("Total", text="Total")

    cart_tree.column("Item", width=200)
    cart_tree.column("Qty", width=50)
    cart_tree.column("Price", width=70)
    cart_tree.column("Total", width=80)

    cart_tree.pack(side="left", fill="both", expand=True)

    # Scrollable controls area (status/breakdown/buttons/checkout) — fixed-height
    # region with its own scrollbar so future buttons never get clipped off the
    # bottom of the window and never require manually resizing it.
    controls_outer = tk.Frame(right_frame, bg=Theme.BG_FRAME)
    controls_outer.pack(side="bottom", fill="x")

    controls_canvas = tk.Canvas(controls_outer, bg=Theme.BG_FRAME, highlightthickness=0, height=460)
    controls_canvas.pack(side="left", fill="both", expand=True)

    controls_scroll = ttk.Scrollbar(controls_outer, orient="vertical", command=controls_canvas.yview)
    controls_scroll.pack(side="right", fill="y")
    controls_canvas.configure(yscrollcommand=controls_scroll.set)

    controls_frame = tk.Frame(controls_canvas, bg=Theme.BG_FRAME)
    controls_window = controls_canvas.create_window((0, 0), window=controls_frame, anchor="nw")

    def _controls_configure(event=None):
        controls_canvas.configure(scrollregion=controls_canvas.bbox("all"))
    controls_frame.bind("<Configure>", _controls_configure)

    def _controls_canvas_resize(event):
        controls_canvas.itemconfig(controls_window, width=event.width)
    controls_canvas.bind("<Configure>", _controls_canvas_resize)

    def _controls_mousewheel(event):
        controls_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    controls_canvas.bind("<Enter>", lambda e: controls_canvas.bind_all("<MouseWheel>", _controls_mousewheel))
    controls_canvas.bind("<Leave>", lambda e: controls_canvas.unbind_all("<MouseWheel>"))

    # Cart data storage
    cart_items = []
    discount_type = None
    discount_value = 0.0
    status_clear_id = None

    status_label = tk.Label(
        controls_frame,
        text="",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_WARNING,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
        anchor="w",
    )
    status_label.pack(fill="x", padx=15, pady=(0, 5))

    # Order breakdown section
    total_frame = tk.Frame(controls_frame, bg=Theme.BG_FRAME)
    total_frame.pack(fill="x", padx=15, pady=15)

    breakdown_frame = tk.Frame(total_frame, bg=Theme.BG_FRAME)
    breakdown_frame.pack(fill="x")
    breakdown_frame.columnconfigure(0, weight=1)
    breakdown_frame.columnconfigure(1, weight=0)

    def _breakdown_row(row, label_text):
        tk.Label(
            breakdown_frame, text=label_text, bg=Theme.BG_FRAME,
            fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).grid(row=row, column=0, sticky="w", pady=2)
        value_label = tk.Label(
            breakdown_frame, text="$0.00", bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold")
        )
        value_label.grid(row=row, column=1, sticky="e", pady=2)
        return value_label

    items_value_label = _breakdown_row(0, "Items")
    subtotal_value_label = _breakdown_row(1, "Subtotal")
    discount_value_label = _breakdown_row(2, "Discount")
    tax_value_label = _breakdown_row(3, "Tax")

    tk.Frame(total_frame, bg=Theme.BORDER_DEFAULT, height=1).pack(fill="x", pady=8)

    total_label = tk.Label(
        total_frame,
        text="Total: $0.00",
        bg=Theme.BG_FRAME,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 18, "bold")
    )
    total_label.pack(pady=(0, 5))

    def calculate_totals():
        subtotal = sum(item['quantity'] * item['price'] for item in cart_items)
        total_items = sum(item['quantity'] for item in cart_items)

        # Discount only applies against items flagged discount_ok (e.g. alcohol
        # may be legally excluded). Tax only applies against items flagged
        # sales_tax, computed on each item's post-discount amount.
        discount_pool = sum(
            item['quantity'] * item['price'] for item in cart_items
            if item.get('discount_ok', True)
        )
        if discount_type == 'percent':
            discount_amount = discount_pool * (discount_value / 100)
        elif discount_type == 'flat':
            discount_amount = min(discount_value, discount_pool)
        else:
            discount_amount = 0
        discount_ratio = (discount_amount / discount_pool) if discount_pool > 0 else 0

        taxable_base = 0.0
        for item in cart_items:
            item_subtotal = item['quantity'] * item['price']
            if item.get('discount_ok', True):
                post_discount = item_subtotal * (1 - discount_ratio)
            else:
                post_discount = item_subtotal
            if item.get('sales_tax', True):
                taxable_base += post_discount

        tax_amount = taxable_base * float(os.getenv('TAX_RATE', 0))
        total = subtotal - discount_amount + tax_amount

        return {
            'total_items': total_items,
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'tax_amount': tax_amount,
            'total': total,
        }

    def update_total():
        totals = calculate_totals()
        items_value_label.config(text=str(totals['total_items']))
        subtotal_value_label.config(text=f"${totals['subtotal']:.2f}")
        discount_value_label.config(
            text=f"-${totals['discount_amount']:.2f}" if totals['discount_amount'] > 0 else "$0.00"
        )
        tax_value_label.config(text=f"${totals['tax_amount']:.2f}")
        total_label.config(text=f"Total: ${totals['total']:.2f}")

    def open_discount_dialog():
        nonlocal discount_type, discount_value

        dialog = tk.Toplevel(win)
        dialog.title("Apply Discount")
        dialog.geometry("320x260")
        dialog.config(bg=Theme.BG_FRAME)
        dialog.transient(win)
        dialog.grab_set()

        tk.Label(
            dialog, text="Discount Type", bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, 11, "bold")
        ).pack(pady=(15, 5))

        mode_var = tk.StringVar(value=discount_type or "none")
        for label, value in [("No Discount", "none"), ("Percent Off (%)", "percent"), ("Flat Amount ($)", "flat")]:
            tk.Radiobutton(
                dialog, text=label, variable=mode_var, value=value,
                bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY,
                selectcolor=Theme.BG_BUTTON, activebackground=Theme.BG_FRAME,
                font=(Theme.FONT_FAMILY, 10)
            ).pack(anchor="w", padx=30)

        tk.Label(
            dialog, text="Value:", bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, 10)
        ).pack(pady=(15, 5))

        value_entry = tk.Entry(dialog, **Theme.entry_style())
        value_entry.pack(padx=30, fill="x", ipady=4)
        if discount_value:
            value_entry.insert(0, str(discount_value))

        def apply_discount():
            nonlocal discount_type, discount_value
            mode = mode_var.get()
            if mode == "none":
                discount_type = None
                discount_value = 0.0
            else:
                raw = value_entry.get().strip()
                try:
                    parsed = float(raw)
                    if parsed < 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Invalid Value", "Enter a non-negative number.", parent=dialog)
                    return
                discount_type = mode
                discount_value = parsed
            update_total()
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=Theme.BG_FRAME)
        btn_frame.pack(pady=20)
        tk.Button(
            btn_frame, text="Apply", command=apply_discount,
            **Theme.button_style(), width=10
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            **Theme.button_style(), width=10
        ).pack(side="left", padx=5)

    def show_low_stock_warning(brand):
        nonlocal status_clear_id
        if status_clear_id is not None:
            win.after_cancel(status_clear_id)
        status_label.config(text=f"Low stock: {brand}", fg=Theme.TEXT_WARNING)
        status_clear_id = win.after(3000, lambda: status_label.config(text="") if win.winfo_exists() else None)

    # Action buttons
    button_frame = tk.Frame(controls_frame, bg=Theme.BG_FRAME)
    button_frame.pack(fill="x", padx=15, pady=(0, 10))

    def add_to_cart(item_id, brand, size, price, stock, sales_tax=True, discount_ok=True):
        # Check if item already in cart
        for cart_item in cart_items:
            if cart_item['item_id'] == item_id:
                cart_item['quantity'] += 1
                new_quantity = cart_item['quantity']
                for tree_item in cart_tree.get_children():
                    if cart_tree.item(tree_item)['values'][0] == f"{brand} - {size}":
                        cart_tree.item(tree_item, values=(
                            f"{brand} - {size}",
                            cart_item['quantity'],
                            f"${price:.2f}",
                            f"${cart_item['quantity'] * price:.2f}"
                        ))
                        break
                update_total()
                if stock - new_quantity <= 0:
                    show_low_stock_warning(brand)
                return True

        # Add new item to cart
        cart_items.append({
            'item_id': item_id,
            'brand': brand,
            'size': size,
            'price': price,
            'quantity': 1,
            'stock': stock,
            'sales_tax': sales_tax,
            'discount_ok': discount_ok,
        })

        cart_tree.insert("", "end", values=(
            f"{brand} - {size}",
            1,
            f"${price:.2f}",
            f"${price:.2f}"
        ))
        update_total()
        if stock - 1 <= 0:
            show_low_stock_warning(brand)
        return True

    def add_custom_item():
        dialog = tk.Toplevel(win)
        dialog.title("Add Custom Item")
        dialog.geometry("320x220")
        dialog.config(bg=Theme.BG_FRAME)
        dialog.transient(win)
        dialog.grab_set()

        tk.Label(
            dialog, text="Item Name (e.g. Bag)", bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, 10, "bold")
        ).pack(pady=(15, 5))
        name_entry = tk.Entry(dialog, **Theme.entry_style())
        name_entry.pack(padx=30, fill="x", ipady=4)

        tk.Label(
            dialog, text="Price ($)", bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, 10, "bold")
        ).pack(pady=(15, 5))
        price_entry = tk.Entry(dialog, **Theme.entry_style())
        price_entry.pack(padx=30, fill="x", ipady=4)

        def confirm_add():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Missing Name", "Enter a name for the item.", parent=dialog)
                return
            try:
                price = float(price_entry.get().strip())
                if price < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Price", "Enter a non-negative number.", parent=dialog)
                return

            cart_items.append({
                'item_id': None,
                'brand': name,
                'size': "",
                'price': price,
                'quantity': 1,
                'stock': None,
                'is_custom': True,
                'sales_tax': True,
                'discount_ok': True,
            })
            cart_tree.insert("", "end", values=(
                f"{name} (Custom)",
                1,
                f"${price:.2f}",
                f"${price:.2f}"
            ))
            update_total()
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=Theme.BG_FRAME)
        btn_frame.pack(pady=15)
        tk.Button(
            btn_frame, text="Add", command=confirm_add,
            **Theme.button_style(), width=10
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            **Theme.button_style(), width=10
        ).pack(side="left", padx=5)

    def fetch_item_flags(item_id):
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT sales_tax, discount_ok FROM items WHERE item_id = %s", (item_id,))
                row = cur.fetchone()
            conn.close()
            if row:
                sales_tax, discount_ok = row
                return (
                    bool(sales_tax) if sales_tax is not None else True,
                    bool(discount_ok) if discount_ok is not None else True,
                )
        except Exception:
            pass
        return True, True

    def add_selected_to_cart():
        selected = product_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to add.")
            return

        item = product_tree.item(selected[0])
        item_id = item['values'][0]
        sales_tax, discount_ok = fetch_item_flags(item_id)
        add_to_cart(
            item_id,
            item['values'][1],
            item['values'][2],
            float(item['values'][3]),
            int(item['values'][4]),
            sales_tax,
            discount_ok,
        )

    def remove_from_cart():
        selected = cart_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an item to remove.")
            return

        idx = cart_tree.index(selected[0])
        cart_tree.delete(selected[0])
        if 0 <= idx < len(cart_items):
            cart_items.pop(idx)
        update_total()

    def clear_cart():
        for item in cart_tree.get_children():
            cart_tree.delete(item)
        cart_items.clear()
        update_total()

    def perform_checkout(payment_method, cash_tendered, change_due):
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                # sales and sale_items are created/migrated by setup_database.py —
                # checkout should not redefine their schema here.
                totals = calculate_totals()

                cur.execute("""
                    INSERT INTO sales (subtotal, discount_amount, tax_amount, total_amount, cashier, payment_method, cash_tendered, change_due)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING sale_id
                """, (
                    totals['subtotal'],
                    totals['discount_amount'],
                    totals['tax_amount'],
                    totals['total'],
                    current_user,
                    payment_method,
                    cash_tendered,
                    change_due,
                ))
                sale_id = cur.fetchone()[0]

                for item in cart_items:
                    subtotal = item['quantity'] * item['price']
                    is_custom = item.get('is_custom', False)
                    item_name = item['brand'] if is_custom else None

                    cur.execute("""
                        INSERT INTO sale_items (sale_id, item_id, quantity, price, subtotal, item_name, is_custom)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (sale_id, item['item_id'], item['quantity'], item['price'], subtotal, item_name, is_custom))

                    if not is_custom and item['item_id'] is not None:
                        cur.execute("""
                            UPDATE inventory
                            SET quantity = quantity - %s
                            WHERE item_id = %s
                        """, (item['quantity'], item['item_id']))

                conn.commit()
            conn.close()

            summary = f"Sale completed! Total: ${totals['total']:.2f}\nSale ID: {sale_id}"
            if payment_method == 'cash' and change_due is not None:
                summary += f"\nChange Due: ${change_due:.2f}"
            messagebox.showinfo("Success", summary)
            if win.winfo_exists():
                clear_cart()
                load_products()
            return True

        except Exception as e:
            messagebox.showerror("Error", f"Checkout failed: {str(e)}")
            return False

    def open_payment_dialog():
        if not cart_items:
            messagebox.showwarning("Empty Cart", "Please add items to cart before checkout.")
            return

        totals = calculate_totals()

        dialog = tk.Toplevel(win)
        dialog.title("Payment")
        dialog.geometry("380x540")
        dialog.config(bg=Theme.BG_FRAME)
        dialog.transient(win)
        dialog.grab_set()

        tk.Label(
            dialog, text="Total Due", bg=Theme.BG_FRAME,
            fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 11, "bold")
        ).pack(pady=(15, 0))

        tk.Label(
            dialog, text=f"${totals['total']:.2f}", bg=Theme.BG_FRAME,
            fg=Theme.ACCENT_GOLD, font=(Theme.FONT_FAMILY, 26, "bold")
        ).pack(pady=(0, 15))

        method_frame = tk.Frame(dialog, bg=Theme.BG_FRAME)
        method_frame.pack(fill="x", padx=20)

        content_frame = tk.Frame(dialog, bg=Theme.BG_FRAME)
        content_frame.pack(fill="both", expand=True, padx=20, pady=15)

        def clear_content():
            for w in content_frame.winfo_children():
                w.destroy()

        def do_confirm(payment_method, cash_tendered, change_due):
            if perform_checkout(payment_method, cash_tendered, change_due):
                dialog.destroy()

        def show_cash_panel():
            btn_cash.config(bg=Theme.ACCENT_GOLD, fg=Theme.TEXT_DARK)
            btn_card.config(bg=Theme.BG_BUTTON, fg=Theme.TEXT_PRIMARY)
            clear_content()

            tk.Label(
                content_frame, text="Amount Tendered", bg=Theme.BG_FRAME,
                fg=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, 10, "bold")
            ).pack(anchor="w")

            tendered_var = tk.StringVar(value="0.00")
            tendered_entry = tk.Entry(content_frame, textvariable=tendered_var, **Theme.entry_style())
            tendered_entry.pack(fill="x", pady=(5, 10), ipady=6)

            quick_frame = tk.Frame(content_frame, bg=Theme.BG_FRAME)
            quick_frame.pack(fill="x", pady=(0, 10))

            balance_label = tk.Label(
                content_frame, text="", bg=Theme.BG_FRAME,
                font=(Theme.FONT_FAMILY, 14, "bold")
            )

            def refresh_balance(*_):
                try:
                    tendered = float(tendered_var.get())
                except ValueError:
                    tendered = 0.0
                diff = tendered - totals['total']
                if diff >= 0:
                    balance_label.config(text=f"Change Due: ${diff:.2f}", fg=Theme.TEXT_SUCCESS)
                else:
                    balance_label.config(text=f"Balance Due: ${-diff:.2f}", fg=Theme.TEXT_WARNING)

            def add_bill(amount):
                try:
                    current = float(tendered_var.get())
                except ValueError:
                    current = 0.0
                tendered_var.set(f"{current + amount:.2f}")

            for i, amount in enumerate([1, 5, 10, 20, 50, 100]):
                b = tk.Button(
                    quick_frame, text=f"${amount}", command=lambda a=amount: add_bill(a),
                    **Theme.button_style(), width=6
                )
                b.grid(row=i // 3, column=i % 3, padx=3, pady=3)
                bind_hover_effect(b)

            btn_reset = tk.Button(
                content_frame, text="Clear Tendered",
                command=lambda: tendered_var.set("0.00"),
                **Theme.button_style()
            )
            btn_reset.pack(fill="x", pady=(0, 10))
            bind_hover_effect(btn_reset)

            balance_label.pack(pady=(0, 15))
            tendered_var.trace_add("write", refresh_balance)
            refresh_balance()

            def confirm_cash():
                try:
                    tendered = float(tendered_var.get())
                except ValueError:
                    messagebox.showerror("Invalid Amount", "Enter a valid tendered amount.", parent=dialog)
                    return
                if tendered < totals['total']:
                    messagebox.showerror("Insufficient Amount", "Amount tendered is less than the total due.", parent=dialog)
                    return
                do_confirm('cash', tendered, tendered - totals['total'])

            btn_confirm = tk.Button(
                content_frame, text="Confirm Cash Sale", command=confirm_cash,
                **Theme.primary_button_style(), height=2
            )
            btn_confirm.pack(fill="x")

        def show_card_panel():
            btn_card.config(bg=Theme.ACCENT_GOLD, fg=Theme.TEXT_DARK)
            btn_cash.config(bg=Theme.BG_BUTTON, fg=Theme.TEXT_PRIMARY)
            clear_content()

            tk.Label(
                content_frame, text="Charge card for the total shown above.",
                bg=Theme.BG_FRAME, fg=Theme.TEXT_SECONDARY,
                font=(Theme.FONT_FAMILY, 11), wraplength=300, justify="center"
            ).pack(pady=(20, 20))

            def confirm_card():
                do_confirm('card', None, None)

            btn_confirm = tk.Button(
                content_frame, text="Confirm Card Sale", command=confirm_card,
                **Theme.primary_button_style(), height=2
            )
            btn_confirm.pack(fill="x")

        btn_cash = tk.Button(method_frame, text="Cash", command=lambda: show_cash_panel(), **Theme.button_style())
        btn_cash.pack(side="left", fill="x", expand=True, padx=(0, 5))
        btn_card = tk.Button(method_frame, text="Card", command=lambda: show_card_panel(), **Theme.button_style())
        btn_card.pack(side="left", fill="x", expand=True, padx=(5, 0))

        tk.Button(
            dialog, text="Cancel", command=dialog.destroy,
            **Theme.button_style()
        ).pack(fill="x", padx=20, pady=(0, 15))

        show_cash_panel()

    def no_sale():
        messagebox.showinfo("No Sale", "Register opened. No sale recorded.")

    btn_add = tk.Button(
        button_frame,
        text="Add to Cart",
        command=add_selected_to_cart,
        **Theme.button_style(),
        width=12
    )
    btn_add.grid(row=0, column=0, padx=5, pady=3)
    bind_hover_effect(btn_add)

    btn_remove = tk.Button(
        button_frame,
        text="Remove",
        command=remove_from_cart,
        **Theme.button_style(),
        width=12
    )
    btn_remove.grid(row=0, column=1, padx=5, pady=3)
    bind_hover_effect(btn_remove)

    btn_clear = tk.Button(
        button_frame,
        text="Clear Cart",
        command=clear_cart,
        **Theme.button_style(),
        width=12
    )
    btn_clear.grid(row=1, column=0, padx=5, pady=3)
    bind_hover_effect(btn_clear)

    # Back button
    btn_back = tk.Button(
        button_frame,
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
    btn_back.grid(row=1, column=1, padx=5, pady=3)

    btn_discount = tk.Button(
        button_frame,
        text="Discount",
        command=open_discount_dialog,
        **Theme.button_style(),
        width=12
    )
    btn_discount.grid(row=2, column=0, padx=5, pady=3)
    bind_hover_effect(btn_discount)

    btn_custom_item = tk.Button(
        button_frame,
        text="Custom Item",
        command=add_custom_item,
        **Theme.button_style(),
        width=12
    )
    btn_custom_item.grid(row=2, column=1, padx=5, pady=3)
    bind_hover_effect(btn_custom_item)

    btn_no_sale = tk.Button(
        button_frame,
        text="No Sale",
        command=no_sale,
        **Theme.button_style(),
        width=12
    )
    btn_no_sale.grid(row=3, column=0, columnspan=2, padx=5, pady=3, sticky="ew")
    bind_hover_effect(btn_no_sale)

    # Checkout button
    checkout_btn = tk.Button(
        controls_frame,
        text="CHECKOUT",
        command=open_payment_dialog,
        **Theme.primary_button_style(),
        height=2
    )
    checkout_btn.pack(fill="x", padx=15, pady=(5, 15))

    # Load products function
    def load_products(search_term=""):
        for item in product_tree.get_children():
            product_tree.delete(item)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                if search_term:
                    cur.execute("""
                        SELECT i.item_id, i.brand, i.size, i.price, inv.quantity
                        FROM items i
                        LEFT JOIN inventory inv ON i.item_id = inv.item_id
                        WHERE LOWER(i.brand) LIKE LOWER(%s) OR i.barcode LIKE %s
                        ORDER BY i.brand
                    """, (f"%{search_term}%", f"%{search_term}%"))
                else:
                    cur.execute("""
                        SELECT i.item_id, i.brand, i.size, i.price, inv.quantity
                        FROM items i
                        LEFT JOIN inventory inv ON i.item_id = inv.item_id
                        WHERE inv.quantity > 0
                        ORDER BY i.brand
                        LIMIT 100
                    """)

                for row in cur.fetchall():
                    product_tree.insert("", "end", values=(
                        row[0],
                        row[1] or "",
                        row[2] or "",
                        f"{row[3]:.2f}" if row[3] else "0.00",
                        row[4] if row[4] is not None else 0
                    ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {str(e)}")

    def on_barcode_scan(event=None):
        barcode = barcode_entry.get().strip()
        if not barcode:
            return

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.item_id, i.brand, i.size, i.price, inv.quantity, i.sales_tax, i.discount_ok
                    FROM items i
                    LEFT JOIN inventory inv ON i.item_id = inv.item_id
                    WHERE i.barcode = %s
                """, (barcode,))
                row = cur.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Barcode lookup failed: {str(e)}")
            barcode_entry.focus_set()
            return

        if not row:
            messagebox.showwarning("Barcode Not Found", f"No item found for barcode: {barcode}")
            barcode_entry.focus_set()
            return

        item_id, brand, size, price, quantity, sales_tax, discount_ok = row
        added = add_to_cart(
            item_id,
            brand or "",
            size or "",
            float(price) if price else 0.0,
            quantity if quantity is not None else 0,
            bool(sales_tax) if sales_tax is not None else True,
            bool(discount_ok) if discount_ok is not None else True,
        )
        if added:
            barcode_entry.delete(0, tk.END)
        barcode_entry.focus_set()

    # Search functionality
    def on_search(*args):
        load_products(search_entry.get().strip())

    search_entry.bind('<KeyRelease>', on_search)
    barcode_entry.bind('<Return>', on_barcode_scan)

    # Double-click to add to cart
    product_tree.bind('<Double-1>', lambda e: add_selected_to_cart())

    # Load initial products
    load_products()
    barcode_entry.focus_set()