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
    win.geometry("1400x750")
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
        height=14
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

    # Cart data storage
    cart_items = []
    discount_type = None
    discount_value = 0.0
    status_clear_id = None

    status_label = tk.Label(
        right_frame,
        text="",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_WARNING,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
        anchor="w",
    )
    status_label.pack(fill="x", padx=15, pady=(0, 5))

    # Total section
    total_frame = tk.Frame(right_frame, bg=Theme.BG_FRAME)
    total_frame.pack(fill="x", padx=15, pady=15)

    total_label = tk.Label(
        total_frame,
        text="Total: $0.00",
        bg=Theme.BG_FRAME,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 18, "bold")
    )
    total_label.pack(pady=10)

    def calculate_totals():
        subtotal = sum(item['quantity'] * item['price'] for item in cart_items)
        if discount_type == 'percent':
            discount_amount = subtotal * (discount_value / 100)
        elif discount_type == 'flat':
            discount_amount = min(discount_value, subtotal)
        else:
            discount_amount = 0
        taxable = subtotal - discount_amount
        tax_amount = taxable * float(os.getenv('TAX_RATE', 0))
        total = taxable + tax_amount
        return {
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'tax_amount': tax_amount,
            'total': total,
        }

    def update_total():
        totals = calculate_totals()
        total_label.config(text=f"Total: ${totals['total']:.2f}")

    def show_low_stock_warning(brand):
        nonlocal status_clear_id
        if status_clear_id is not None:
            win.after_cancel(status_clear_id)
        status_label.config(text=f"Low stock: {brand}", fg=Theme.TEXT_WARNING)
        status_clear_id = win.after(3000, lambda: status_label.config(text="") if win.winfo_exists() else None)

    # Action buttons
    button_frame = tk.Frame(right_frame, bg=Theme.BG_FRAME)
    button_frame.pack(fill="x", padx=15, pady=(0, 10))

    def add_to_cart(item_id, brand, size, price, stock):
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
            'stock': stock
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

    def add_selected_to_cart():
        selected = product_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to add.")
            return

        item = product_tree.item(selected[0])
        add_to_cart(
            item['values'][0],
            item['values'][1],
            item['values'][2],
            float(item['values'][3]),
            int(item['values'][4]),
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

    def checkout():
        if not cart_items:
            messagebox.showwarning("Empty Cart", "Please add items to cart before checkout.")
            return

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                # sales and sale_items are created/migrated by setup_database.py —
                # checkout() should not redefine their schema here.
                totals = calculate_totals()

                cur.execute("""
                    INSERT INTO sales (subtotal, discount_amount, tax_amount, total_amount, cashier)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING sale_id
                """, (
                    totals['subtotal'],
                    totals['discount_amount'],
                    totals['tax_amount'],
                    totals['total'],
                    current_user,
                ))
                sale_id = cur.fetchone()[0]

                for item in cart_items:
                    subtotal = item['quantity'] * item['price']
                    cur.execute("""
                        INSERT INTO sale_items (sale_id, item_id, quantity, price, subtotal)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (sale_id, item['item_id'], item['quantity'], item['price'], subtotal))

                    cur.execute("""
                        UPDATE inventory
                        SET quantity = quantity - %s
                        WHERE item_id = %s
                    """, (item['quantity'], item['item_id']))

                conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Sale completed! Total: ${totals['total']:.2f}\nSale ID: {sale_id}")
            if win.winfo_exists():
                clear_cart()
                load_products()

        except Exception as e:
            messagebox.showerror("Error", f"Checkout failed: {str(e)}")

    btn_add = tk.Button(
        button_frame,
        text="Add to Cart",
        command=add_selected_to_cart,
        **Theme.button_style(),
        width=12
    )
    btn_add.grid(row=0, column=0, padx=5, pady=5)
    bind_hover_effect(btn_add)

    btn_remove = tk.Button(
        button_frame,
        text="Remove",
        command=remove_from_cart,
        **Theme.button_style(),
        width=12
    )
    btn_remove.grid(row=0, column=1, padx=5, pady=5)
    bind_hover_effect(btn_remove)

    btn_clear = tk.Button(
        button_frame,
        text="Clear Cart",
        command=clear_cart,
        **Theme.button_style(),
        width=12
    )
    btn_clear.grid(row=1, column=0, padx=5, pady=5)
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
    btn_back.grid(row=1, column=1, padx=5, pady=5)
    
    # Checkout button
    checkout_btn = tk.Button(
        right_frame,
        text="CHECKOUT",
        command=checkout,
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
                    SELECT i.item_id, i.brand, i.size, i.price, inv.quantity
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

        item_id, brand, size, price, quantity = row
        added = add_to_cart(
            item_id,
            brand or "",
            size or "",
            float(price) if price else 0.0,
            quantity if quantity is not None else 0,
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