# sales_gui.py
import os
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime
from db import get_conn
from theme import Theme
from receipt import print_receipt
from customer_display import is_enabled as customer_display_enabled, open_customer_display
from ui_settings import scale_geometry, scale_dim, position_main_window, get_ui_scale

def open_sales_window(current_user: str):
    scale = get_ui_scale()
    win = ctk.CTkToplevel()
    win.title("Sales/POS")
    win.geometry(scale_geometry(1400, 850))
    win.configure(**Theme.ctk_window_style())
    win.after(60, lambda: position_main_window(win))

    customer_display = None
    if customer_display_enabled():
        customer_display = open_customer_display(win)
        if customer_display is None:
            # parent=win keeps this properly stacked above the Sales window
            # even if the deferred position_main_window() above fires (and
            # maximizes win) while this dialog's own internal wait loop is
            # pumping events — without it, an unparented dialog could end up
            # visually buried under the newly-maximized window, making Sales
            # look like it "won't show" until the hidden dialog is dismissed.
            messagebox.showinfo(
                "Customer Display",
                "Customer Display is enabled in Settings, but no second monitor was detected.",
                parent=win
            )

    # Configure ttk style — Treeview has no CTk equivalent, so it stays
    # ttk, styled to blend in with the CTk widgets around it. Its font
    # point sizes are scaled by the 'tk scaling' pin (set once in
    # login_gui.py) automatically, unlike CTk fonts which need scale_dim()
    # applied explicitly — rowheight is a literal pixel value so it does
    # need that here.
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Treeview",
                    background=Theme.BG_BUTTON,
                    foreground=Theme.TEXT_PRIMARY,
                    fieldbackground=Theme.BG_BUTTON,
                    borderwidth=0,
                    font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
                    rowheight=scale_dim(30))
    style.configure("Treeview.Heading",
                    background=Theme.BG_FRAME,
                    foreground=Theme.ACCENT_GOLD,
                    relief="flat",
                    font=(Theme.FONT_FAMILY, 11, 'bold'))
    style.map('Treeview', background=[('selected', Theme.ACCENT_GOLD)])

    # Header
    header_frame = ctk.CTkFrame(win, fg_color=Theme.BG_DARK, corner_radius=0)
    header_frame.pack(fill='x', pady=(10, 5))

    ctk.CTkLabel(
        header_frame,
        text=f"Cashier: {current_user}",
        **Theme.ctk_secondary_label_style(scale=scale)
    ).pack()

    # Alcohol/tobacco age cutoff — recomputed from today's date every time the
    # screen opens, so it's always correct without needing to be updated by hand.
    today = datetime.now().date()
    try:
        cutoff_date = today.replace(year=today.year - 21)
    except ValueError:
        # today is Feb 29 and (today.year - 21) isn't a leap year
        cutoff_date = today.replace(month=2, day=28, year=today.year - 21)

    ctk.CTkLabel(
        header_frame,
        text=f"Must be born on or before {cutoff_date.strftime('%B %d, %Y')} to purchase alcohol/tobacco",
        fg_color="transparent",
        text_color=Theme.TEXT_WARNING,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL), "bold")
    ).pack(pady=(5, 0))

    # Main container
    main_frame = ctk.CTkFrame(win, fg_color=Theme.BG_DARK, corner_radius=0)
    main_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # ---- Bottom strip (packed first so the cart above it gets the leftover
    # space) — scan/buttons on the left, totals/checkout on the right ----
    bottom_frame = ctk.CTkFrame(main_frame, fg_color=Theme.BG_DARK, corner_radius=0)
    bottom_frame.pack(side="bottom", fill="x", pady=(10, 0))

    left_panel = ctk.CTkFrame(bottom_frame, **Theme.ctk_frame_style())
    left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

    right_panel = ctk.CTkFrame(bottom_frame, width=scale_dim(380), **Theme.ctk_frame_style())
    right_panel.pack(side="right", fill="y")
    right_panel.pack_propagate(False)

    # ---- Shopping cart — the main, wide focus of the screen ----
    cart_panel = ctk.CTkFrame(main_frame, **Theme.ctk_frame_style())
    cart_panel.pack(side="top", fill="both", expand=True)

    ctk.CTkLabel(
        cart_panel,
        text="Shopping Cart",
        fg_color="transparent",
        text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(14), "bold")
    ).pack(pady=(15, 10))

    cart_frame = ctk.CTkFrame(cart_panel, fg_color=Theme.BG_FRAME, corner_radius=0)
    cart_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    cart_scroll = ttk.Scrollbar(cart_frame)
    cart_scroll.pack(side="right", fill="y")

    cart_columns = ("Item", "Qty", "Price", "Total")
    cart_tree = ttk.Treeview(
        cart_frame,
        columns=cart_columns,
        show="headings",
        yscrollcommand=cart_scroll.set
    )
    cart_scroll.config(command=cart_tree.yview)

    cart_tree.heading("Item", text="Item")
    cart_tree.heading("Qty", text="Qty")
    cart_tree.heading("Price", text="Price")
    cart_tree.heading("Total", text="Total")

    cart_tree.column("Item", width=500)
    cart_tree.column("Qty", width=100, anchor="center")
    cart_tree.column("Price", width=150, anchor="e")
    cart_tree.column("Total", width=150, anchor="e")

    cart_tree.pack(side="left", fill="both", expand=True)

    # Cart data storage
    cart_items = []
    discount_type = None
    discount_value = 0.0
    status_clear_id = None

    status_label = ctk.CTkLabel(
        left_panel,
        text="",
        fg_color="transparent",
        text_color=Theme.TEXT_WARNING,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL)),
        anchor="w",
    )

    # Order breakdown section. Padding here is intentionally tight (not
    # just cosmetic): on a 1366x768 screen — the real target resolution for
    # this register — this column has to fit 5 breakdown rows, a divider,
    # the Total line, and the CHECKOUT button in well under 300px of actual
    # height. Looser padding previously pushed the combined content past
    # what was available, and Tk responds to that by dropping the
    # last-packed widget (CHECKOUT) entirely rather than shrinking it.
    total_frame = ctk.CTkFrame(right_panel, fg_color=Theme.BG_FRAME, corner_radius=0)
    total_frame.pack(fill="both", expand=True, padx=15, pady=(8, 4))

    breakdown_frame = ctk.CTkFrame(total_frame, fg_color=Theme.BG_FRAME, corner_radius=0)
    breakdown_frame.pack(fill="x")
    breakdown_frame.columnconfigure(0, weight=1)
    breakdown_frame.columnconfigure(1, weight=0)

    def _breakdown_row(row, label_text):
        ctk.CTkLabel(
            breakdown_frame, text=label_text, fg_color="transparent",
            text_color=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL))
        ).grid(row=row, column=0, sticky="w", pady=1)
        value_label = ctk.CTkLabel(
            breakdown_frame, text="$0.00", fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), "bold")
        )
        value_label.grid(row=row, column=1, sticky="e", pady=1)
        return value_label

    items_value_label = _breakdown_row(0, "Items")
    subtotal_value_label = _breakdown_row(1, "Subtotal")
    discount_value_label = _breakdown_row(2, "Discount")
    tax_value_label = _breakdown_row(3, "Tax")
    deposit_value_label = _breakdown_row(4, "Deposit")

    ctk.CTkFrame(total_frame, fg_color=Theme.BORDER_DEFAULT, height=1, corner_radius=0).pack(fill="x", pady=3)

    total_label = ctk.CTkLabel(
        total_frame,
        text="Total: $0.00",
        fg_color="transparent",
        text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(18), "bold")
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

        # Bottle deposits are not taxed — added on top of the tax-inclusive total.
        deposit_amount = sum(
            item['quantity'] * item.get('deposit_amount', 0)
            for item in cart_items if item.get('deposit_enabled', False)
        )

        total = subtotal - discount_amount + tax_amount + deposit_amount

        return {
            'total_items': total_items,
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'tax_amount': tax_amount,
            'deposit_amount': deposit_amount,
            'total': total,
        }

    def update_total():
        totals = calculate_totals()
        items_value_label.configure(text=str(totals['total_items']))
        discount_value_label.configure(
            text=f"-${totals['discount_amount']:.2f}" if totals['discount_amount'] > 0 else "$0.00"
        )
        subtotal_value_label.configure(text=f"${totals['subtotal']:.2f}")
        tax_value_label.configure(text=f"${totals['tax_amount']:.2f}")
        deposit_value_label.configure(text=f"${totals['deposit_amount']:.2f}")
        total_label.configure(text=f"Total: ${totals['total']:.2f}")

        if customer_display is not None:
            customer_display['update'](cart_items, totals)

    def open_discount_dialog():
        nonlocal discount_type, discount_value

        dialog = ctk.CTkToplevel(win)
        dialog.title("Apply Discount")
        dialog.geometry(scale_geometry(320, 260))
        dialog.configure(**Theme.ctk_window_style())
        dialog.transient(win)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Discount Type", fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(11), "bold")
        ).pack(pady=(15, 5))

        mode_var = tk.StringVar(value=discount_type or "none")
        for label, value in [("No Discount", "none"), ("Percent Off (%)", "percent"), ("Flat Amount ($)", "flat")]:
            ctk.CTkRadioButton(
                dialog, text=label, variable=mode_var, value=value,
                fg_color=Theme.ACCENT_GOLD, hover_color=Theme.ACCENT_GOLD_DARK,
                text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(10))
            ).pack(anchor="w", padx=30, pady=2)

        ctk.CTkLabel(
            dialog, text="Value:", fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(10))
        ).pack(pady=(15, 5))

        value_entry = ctk.CTkEntry(dialog, **Theme.ctk_entry_style(scale=scale))
        value_entry.pack(padx=30, fill="x")
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

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(
            btn_frame, text="Apply", command=apply_discount,
            **Theme.ctk_button_style(scale=scale), width=scale_dim(100)
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Cancel", command=dialog.destroy,
            **Theme.ctk_button_style(scale=scale), width=scale_dim(100)
        ).pack(side="left", padx=5)

    def show_low_stock_warning(brand):
        nonlocal status_clear_id
        if status_clear_id is not None:
            win.after_cancel(status_clear_id)
        status_label.configure(text=f"Low stock: {brand}", text_color=Theme.TEXT_WARNING)
        status_clear_id = win.after(3000, lambda: status_label.configure(text="") if win.winfo_exists() else None)

    def add_to_cart(item_id, brand, size, price, stock, sales_tax=True, discount_ok=True,
                     deposit_enabled=False, deposit_amount=0.0, barcode=None):
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
            'deposit_enabled': deposit_enabled,
            'deposit_amount': deposit_amount,
            'barcode': barcode,
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
        dialog = ctk.CTkToplevel(win)
        dialog.title("Add Custom Item")
        dialog.geometry(scale_geometry(320, 220))
        dialog.configure(**Theme.ctk_window_style())
        dialog.transient(win)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Item Name (e.g. Bag)", fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(10), "bold")
        ).pack(pady=(15, 5))
        name_entry = ctk.CTkEntry(dialog, **Theme.ctk_entry_style(scale=scale))
        name_entry.pack(padx=30, fill="x")

        ctk.CTkLabel(
            dialog, text="Price ($)", fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(10), "bold")
        ).pack(pady=(15, 5))
        price_entry = ctk.CTkEntry(dialog, **Theme.ctk_entry_style(scale=scale))
        price_entry.pack(padx=30, fill="x")

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
                'deposit_enabled': False,
                'deposit_amount': 0.0,
                'barcode': None,
            })
            cart_tree.insert("", "end", values=(
                f"{name} (Custom)",
                1,
                f"${price:.2f}",
                f"${price:.2f}"
            ))
            update_total()
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(
            btn_frame, text="Add", command=confirm_add,
            **Theme.ctk_button_style(scale=scale), width=scale_dim(100)
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Cancel", command=dialog.destroy,
            **Theme.ctk_button_style(scale=scale), width=scale_dim(100)
        ).pack(side="left", padx=5)

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
        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                # sales and sale_items are created/migrated by setup_database.py —
                # checkout should not redefine their schema here.
                totals = calculate_totals()

                cur.execute("""
                    INSERT INTO sales (subtotal, discount_amount, tax_amount, deposit_amount, total_amount, cashier, payment_method, cash_tendered, change_due)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING sale_id
                """, (
                    totals['subtotal'],
                    totals['discount_amount'],
                    totals['tax_amount'],
                    totals['deposit_amount'],
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

            # Printing happens after the sale is already committed — a print/
            # drawer failure here must not look like the sale itself failed.
            try:
                print_receipt(sale_id, current_user, cart_items, totals, payment_method, cash_tendered, change_due)
                print_note = ""
            except Exception as print_err:
                print_note = f"\n\n(Receipt did not print: {print_err})"

            summary = f"Sale completed! Total: ${totals['total']:.2f}\nSale ID: {sale_id}"
            if payment_method == 'cash' and change_due is not None:
                summary += f"\nChange Due: ${change_due:.2f}"
            messagebox.showinfo("Success", summary + print_note)
            if win.winfo_exists():
                clear_cart()
            return True

        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            messagebox.showerror("Error", f"Checkout failed: {str(e)}")
            return False

    def open_payment_dialog():
        if not cart_items:
            messagebox.showwarning("Empty Cart", "Please add items to cart before checkout.")
            return

        totals = calculate_totals()

        dialog = ctk.CTkToplevel(win)
        dialog.title("Payment")
        dialog.geometry(scale_geometry(380, 540))
        dialog.configure(**Theme.ctk_window_style())
        dialog.transient(win)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Total Due", fg_color="transparent",
            text_color=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, scale_dim(11), "bold")
        ).pack(pady=(15, 0))

        ctk.CTkLabel(
            dialog, text=f"${totals['total']:.2f}", fg_color="transparent",
            text_color=Theme.ACCENT_GOLD, font=(Theme.FONT_FAMILY, scale_dim(26), "bold")
        ).pack(pady=(0, 15))

        method_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        method_frame.pack(fill="x", padx=20)

        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=15)

        def clear_content():
            for w in content_frame.winfo_children():
                w.destroy()

        def do_confirm(payment_method, cash_tendered, change_due):
            if perform_checkout(payment_method, cash_tendered, change_due):
                dialog.destroy()

        def show_cash_panel():
            btn_cash.configure(fg_color=Theme.ACCENT_GOLD, text_color=Theme.TEXT_DARK)
            btn_card.configure(fg_color=Theme.BG_BUTTON, text_color=Theme.TEXT_PRIMARY)
            clear_content()

            ctk.CTkLabel(
                content_frame, text="Amount Tendered", fg_color="transparent",
                text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(10), "bold")
            ).pack(anchor="w")

            tendered_var = tk.StringVar(value="0.00")
            tendered_entry = ctk.CTkEntry(content_frame, textvariable=tendered_var, **Theme.ctk_entry_style(scale=scale))
            tendered_entry.pack(fill="x", pady=(5, 10))

            quick_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            quick_frame.pack(fill="x", pady=(0, 10))

            balance_label = ctk.CTkLabel(
                content_frame, text="", fg_color="transparent",
                font=(Theme.FONT_FAMILY, scale_dim(14), "bold")
            )

            def refresh_balance(*_):
                try:
                    tendered = float(tendered_var.get())
                except ValueError:
                    tendered = 0.0
                diff = tendered - totals['total']
                if diff >= 0:
                    balance_label.configure(text=f"Change Due: ${diff:.2f}", text_color=Theme.TEXT_SUCCESS)
                else:
                    balance_label.configure(text=f"Balance Due: ${-diff:.2f}", text_color=Theme.TEXT_WARNING)

            def add_bill(amount):
                try:
                    current = float(tendered_var.get())
                except ValueError:
                    current = 0.0
                tendered_var.set(f"{current + amount:.2f}")

            for i, amount in enumerate([1, 5, 10, 20, 50, 100]):
                b = ctk.CTkButton(
                    quick_frame, text=f"${amount}", command=lambda a=amount: add_bill(a),
                    **Theme.ctk_button_style(scale=scale), width=scale_dim(70)
                )
                b.grid(row=i // 3, column=i % 3, padx=3, pady=3)

            btn_reset = ctk.CTkButton(
                content_frame, text="Clear Tendered",
                command=lambda: tendered_var.set("0.00"),
                **Theme.ctk_button_style(scale=scale)
            )
            btn_reset.pack(fill="x", pady=(0, 10))

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

            btn_confirm = ctk.CTkButton(
                content_frame, text="Confirm Cash Sale", command=confirm_cash,
                **Theme.ctk_primary_button_style(scale=scale), height=scale_dim(40)
            )
            btn_confirm.pack(fill="x")

        def show_card_panel():
            btn_card.configure(fg_color=Theme.ACCENT_GOLD, text_color=Theme.TEXT_DARK)
            btn_cash.configure(fg_color=Theme.BG_BUTTON, text_color=Theme.TEXT_PRIMARY)
            clear_content()

            ctk.CTkLabel(
                content_frame, text="Charge card for the total shown above.",
                fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
                font=(Theme.FONT_FAMILY, scale_dim(11)), wraplength=scale_dim(300), justify="center"
            ).pack(pady=(20, 20))

            def confirm_card():
                do_confirm('card', None, None)

            btn_confirm = ctk.CTkButton(
                content_frame, text="Confirm Card Sale", command=confirm_card,
                **Theme.ctk_primary_button_style(scale=scale), height=scale_dim(40)
            )
            btn_confirm.pack(fill="x")

        btn_cash = ctk.CTkButton(method_frame, text="Cash", command=lambda: show_cash_panel(), **Theme.ctk_button_style(scale=scale))
        btn_cash.pack(side="left", fill="x", expand=True, padx=(0, 5))
        btn_card = ctk.CTkButton(method_frame, text="Card", command=lambda: show_card_panel(), **Theme.ctk_button_style(scale=scale))
        btn_card.pack(side="left", fill="x", expand=True, padx=(5, 0))

        ctk.CTkButton(
            dialog, text="Cancel", command=dialog.destroy,
            **Theme.ctk_button_style(scale=scale)
        ).pack(fill="x", padx=20, pady=(0, 15))

        show_cash_panel()

    def no_sale():
        messagebox.showinfo("No Sale", "Register opened. No sale recorded.")

    def on_barcode_scan(event=None):
        barcode = barcode_entry.get().strip()
        if not barcode:
            return

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.item_id, i.brand, i.size, i.price, inv.quantity, i.sales_tax, i.discount_ok,
                           i.deposit_sale_enabled, i.deposit_sale_amount, i.barcode
                    FROM items i
                    LEFT JOIN inventory inv ON i.item_id = inv.item_id
                    WHERE REPLACE(i.barcode, ' ', '') = REPLACE(%s, ' ', '')
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

        item_id, brand, size, price, quantity, sales_tax, discount_ok, deposit_enabled, deposit_amount, item_barcode = row
        added = add_to_cart(
            item_id,
            brand or "",
            size or "",
            float(price) if price else 0.0,
            quantity if quantity is not None else 0,
            bool(sales_tax) if sales_tax is not None else True,
            bool(discount_ok) if discount_ok is not None else True,
            bool(deposit_enabled) if deposit_enabled is not None else False,
            float(deposit_amount) if deposit_amount is not None else 0.0,
            item_barcode,
        )
        if added:
            barcode_entry.delete(0, tk.END)
        barcode_entry.focus_set()

    # ---- Populate bottom-left: scan field + status + action buttons ----
    scan_section = ctk.CTkFrame(left_panel, fg_color=Theme.BG_FRAME, corner_radius=0)
    scan_section.pack(fill="x", padx=15, pady=15)

    ctk.CTkLabel(
        scan_section,
        text="Scan Item:",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(11), 'bold')
    ).pack(anchor="w", pady=(0, 5))

    barcode_entry = ctk.CTkEntry(scan_section, **Theme.ctk_entry_style(scale=scale))
    barcode_entry.pack(fill="x", pady=5)
    barcode_entry.bind('<Return>', on_barcode_scan)
    barcode_entry.bind('<KP_Enter>', on_barcode_scan)

    status_label.pack(fill="x", padx=15, pady=(0, 5))

    button_frame = ctk.CTkFrame(left_panel, fg_color=Theme.BG_FRAME, corner_radius=0)
    button_frame.pack(fill="x", padx=15, pady=(0, 15))
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=1)

    btn_remove = ctk.CTkButton(
        button_frame,
        text="Remove",
        command=remove_from_cart,
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(120)
    )
    btn_remove.grid(row=0, column=0, padx=5, pady=3, sticky="ew")

    btn_discount = ctk.CTkButton(
        button_frame,
        text="Discount",
        command=open_discount_dialog,
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(120)
    )
    btn_discount.grid(row=0, column=1, padx=5, pady=3, sticky="ew")

    btn_custom_item = ctk.CTkButton(
        button_frame,
        text="Custom Item",
        command=add_custom_item,
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(120)
    )
    btn_custom_item.grid(row=1, column=0, padx=5, pady=3, sticky="ew")

    btn_clear = ctk.CTkButton(
        button_frame,
        text="Clear Cart",
        command=clear_cart,
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(120)
    )
    btn_clear.grid(row=1, column=1, padx=5, pady=3, sticky="ew")

    btn_no_sale = ctk.CTkButton(
        button_frame,
        text="No Sale",
        command=no_sale,
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(120)
    )
    btn_no_sale.grid(row=2, column=0, columnspan=2, padx=5, pady=3, sticky="ew")

    # ---- Populate bottom-right: checkout button under the totals ----
    checkout_btn = ctk.CTkButton(
        right_panel,
        text="CHECKOUT",
        command=open_payment_dialog,
        **{**Theme.ctk_primary_button_style(scale=scale), 'font': (Theme.FONT_FAMILY, scale_dim(16), 'bold')},
        height=scale_dim(50)
    )
    # side="bottom" is important, not cosmetic: total_frame above is packed
    # with expand=True and claims space greedily, so without an explicit
    # side here Tk can squeeze this button down to near-zero height on a
    # shorter screen instead of shrinking total_frame — anchoring it to the
    # bottom reserves its full size first no matter how little vertical
    # room is left.
    checkout_btn.pack(side="bottom", fill="x", padx=15, pady=(0, 15))

    barcode_entry.focus_set()

    return win
