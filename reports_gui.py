# reports_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from db import get_conn
from theme import Theme, bind_hover_effect
from receipt import print_receipt

def open_reports_window(current_user):
    win = tk.Toplevel()
    win.title("Reports & Analytics")
    win.geometry("1200x700")
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
    
    # Configure notebook style
    style.configure("TNotebook", background=Theme.BG_DARK, borderwidth=0)
    style.configure("TNotebook.Tab", 
                    background=Theme.BG_BUTTON,
                    foreground=Theme.TEXT_PRIMARY,
                    padding=[20, 10],
                    font=(Theme.FONT_FAMILY, 11))
    style.map("TNotebook.Tab",
              background=[("selected", Theme.BG_FRAME)],
              foreground=[("selected", Theme.ACCENT_GOLD)])

    # Header
    header_frame = tk.Frame(win, bg=Theme.BG_DARK)
    header_frame.pack(fill='x', pady=(20, 10))

    tk.Label(
        header_frame,
        text="Reports & Analytics",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 20, "bold")
    ).pack()

    # Notebook for different reports
    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=20, pady=10)

    # Sales Report Tab
    sales_tab = tk.Frame(notebook, bg=Theme.BG_DARK)
    notebook.add(sales_tab, text="Sales Report")

    # Date filter frame
    date_frame = tk.Frame(sales_tab, **Theme.frame_style())
    date_frame.pack(pady=15, padx=20, fill="x")

    date_inner = tk.Frame(date_frame, bg=Theme.BG_FRAME)
    date_inner.pack(padx=20, pady=15)

    tk.Label(
        date_inner,
        text="Period:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(side="left", padx=(0, 15))

    period_var = tk.StringVar(value="today")
    periods = [("Today", "today"), ("This Week", "week"), ("This Month", "month"), ("All Time", "all")]
    
    for text, value in periods:
        tk.Radiobutton(
            date_inner,
            text=text,
            variable=period_var,
            value=value,
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY,
            selectcolor=Theme.BG_BUTTON,
            activebackground=Theme.BG_FRAME,
            activeforeground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, 10)
        ).pack(side="left", padx=10)

    def load_sales_report():
        for item in sales_tree.get_children():
            sales_tree.delete(item)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                period = period_var.get()
                
                if period == "today":
                    date_filter = "DATE(sale_date) = CURRENT_DATE"
                elif period == "week":
                    date_filter = "sale_date >= CURRENT_DATE - INTERVAL '7 days'"
                elif period == "month":
                    date_filter = "sale_date >= CURRENT_DATE - INTERVAL '30 days'"
                else:
                    date_filter = "1=1"

                query = f"""
                    SELECT
                        s.sale_id,
                        s.sale_date,
                        s.cashier,
                        s.total_amount,
                        COUNT(si.sale_item_id) as items_count,
                        s.status,
                        s.is_refund
                    FROM sales s
                    LEFT JOIN sale_items si ON s.sale_id = si.sale_id
                    WHERE {date_filter}
                    GROUP BY s.sale_id, s.sale_date, s.cashier, s.total_amount, s.status, s.is_refund
                    ORDER BY s.sale_date DESC
                """

                cur.execute(query)
                rows = cur.fetchall()

                total_sales = 0
                total_transactions = 0

                for row in rows:
                    sale_id, sale_date, cashier, total, items, status, is_refund = row
                    total = float(total) if total else 0.0
                    total_str = f"-${abs(total):.2f}" if total < 0 else f"${total:.2f}"
                    sales_tree.insert("", "end", values=(
                        sale_id,
                        sale_date.strftime("%Y-%m-%d %H:%M") if sale_date else "",
                        cashier or "",
                        total_str,
                        items or 0,
                        status or "complete",
                        "Yes" if is_refund else "No"
                    ))
                    total_sales += total
                    total_transactions += 1

                total_sales_str = f"-${abs(total_sales):.2f}" if total_sales < 0 else f"${total_sales:.2f}"
                summary_text = f"Transactions: {total_transactions} | Total Sales: {total_sales_str}"
                if total_transactions > 0:
                    avg_sale = total_sales / total_transactions
                    avg_str = f"-${abs(avg_sale):.2f}" if avg_sale < 0 else f"${avg_sale:.2f}"
                    summary_text += f" | Average: {avg_str}"
                summary_label.config(text=summary_text)

            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sales report: {str(e)}")

    refresh_btn = tk.Button(
        date_inner,
        text="Load Report",
        command=load_sales_report,
        **Theme.button_style(),
        width=12
    )
    refresh_btn.pack(side="left", padx=20)
    bind_hover_effect(refresh_btn)

    # Sales treeview frame
    tree_container = tk.Frame(sales_tab, **Theme.frame_style())
    tree_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    tree_frame = tk.Frame(tree_container, bg=Theme.BG_FRAME)
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    sales_scroll = ttk.Scrollbar(tree_frame)
    sales_scroll.pack(side="right", fill="y")

    sales_columns = ("Sale ID", "Date", "Cashier", "Total", "Items", "Status", "Is Refund")
    sales_tree = ttk.Treeview(
        tree_frame,
        columns=sales_columns,
        show="headings",
        yscrollcommand=sales_scroll.set
    )
    sales_scroll.config(command=sales_tree.yview)

    sales_tree.heading("Sale ID", text="Sale ID")
    sales_tree.heading("Date", text="Date & Time")
    sales_tree.heading("Cashier", text="Cashier")
    sales_tree.heading("Total", text="Total")
    sales_tree.heading("Items", text="Items Count")
    sales_tree.heading("Status", text="Status")
    sales_tree.heading("Is Refund", text="Is Refund")

    sales_tree.column("Sale ID", width=80)
    sales_tree.column("Date", width=150)
    sales_tree.column("Cashier", width=150)
    sales_tree.column("Total", width=120)
    sales_tree.column("Items", width=120)
    sales_tree.column("Status", width=100)
    sales_tree.column("Is Refund", width=90)

    sales_tree.pack(side="left", fill="both", expand=True)

    def void_selected_sale():
        selected = sales_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sale to void.")
            return

        values = sales_tree.item(selected[0])['values']
        sale_id, current_status = values[0], values[5]
        if current_status == "incomplete":
            messagebox.showinfo("Already Voided", "This sale is already marked incomplete.")
            return

        if not messagebox.askyesno(
            "Void Sale",
            f"Mark Sale ID {sale_id} as incomplete? This only flags the record — "
            "it does not restock inventory or adjust cash totals."
        ):
            return

        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("UPDATE sales SET status = 'incomplete' WHERE sale_id = %s", (sale_id,))
                conn.commit()
            conn.close()
            load_sales_report()
        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            messagebox.showerror("Error", f"Failed to void sale: {str(e)}")

    void_btn = tk.Button(
        sales_tab,
        text="Void Selected Sale",
        command=void_selected_sale,
        **Theme.button_style(),
        width=18
    )
    void_btn.pack(pady=(0, 10))
    bind_hover_effect(void_btn)

    def refund_selected_sale():
        selected = sales_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a sale to refund.")
            return

        sale_id = sales_tree.item(selected[0])['values'][0]

        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT subtotal, discount_amount, tax_amount, deposit_amount, total_amount,
                           payment_method, status, is_refund
                    FROM sales WHERE sale_id = %s
                """, (sale_id,))
                orig = cur.fetchone()
                if orig is None:
                    messagebox.showerror("Error", "Sale not found.")
                    return
                (orig_subtotal, orig_discount, orig_tax, orig_deposit, orig_total,
                 orig_payment_method, orig_status, orig_is_refund) = orig

                if orig_status == 'incomplete':
                    messagebox.showwarning(
                        "Cannot Refund", "This sale is voided/incomplete and cannot be refunded."
                    )
                    return
                if orig_is_refund:
                    messagebox.showwarning(
                        "Cannot Refund", "This is already a refund record and cannot itself be refunded."
                    )
                    return

                cur.execute(
                    "SELECT COUNT(*) FROM sales WHERE original_sale_id = %s AND is_refund = TRUE",
                    (sale_id,)
                )
                if cur.fetchone()[0] > 0:
                    messagebox.showwarning("Already Refunded", "This sale has already been refunded.")
                    return

                cur.execute("""
                    SELECT si.item_id, si.quantity, si.price, si.item_name, si.is_custom, i.brand, i.barcode
                    FROM sale_items si
                    LEFT JOIN items i ON si.item_id = i.item_id
                    WHERE si.sale_id = %s
                """, (sale_id,))
                orig_items = cur.fetchall()
            conn.close()
        except Exception as e:
            if conn is not None:
                conn.close()
            messagebox.showerror("Error", f"Failed to load sale for refund: {str(e)}")
            return

        if not messagebox.askyesno(
            "Refund Sale",
            f"Refund Sale ID {sale_id} for ${float(orig_total):.2f} ({orig_payment_method})?\n\n"
            "This will restock inventory for all items and cannot be undone."
        ):
            return

        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sales (subtotal, discount_amount, tax_amount, deposit_amount, total_amount,
                                        cashier, payment_method, is_refund, original_sale_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                    RETURNING sale_id
                """, (
                    -float(orig_subtotal), -float(orig_discount), -float(orig_tax), -float(orig_deposit),
                    -float(orig_total), current_user, orig_payment_method, sale_id,
                ))
                refund_sale_id = cur.fetchone()[0]

                refund_cart_items = []
                for item_id, qty, price, item_name, is_custom, brand, barcode in orig_items:
                    qty = int(qty)
                    price = float(price)
                    subtotal = -(qty * price)
                    name = item_name if is_custom else (brand or "")

                    cur.execute("""
                        INSERT INTO sale_items (sale_id, item_id, quantity, price, subtotal, item_name, is_custom)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (refund_sale_id, item_id, -qty, price, subtotal, item_name, is_custom))

                    if not is_custom and item_id is not None:
                        cur.execute(
                            "UPDATE inventory SET quantity = quantity + %s WHERE item_id = %s",
                            (qty, item_id)
                        )

                    refund_cart_items.append({
                        'brand': name,
                        'quantity': -qty,
                        'price': price,
                        'is_custom': is_custom,
                        'barcode': barcode,
                    })

                conn.commit()
            conn.close()
        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            messagebox.showerror("Error", f"Failed to process refund: {str(e)}")
            return

        refund_totals = {
            'total_items': sum(item['quantity'] for item in refund_cart_items),
            'subtotal': -float(orig_subtotal),
            'discount_amount': -float(orig_discount),
            'tax_amount': -float(orig_tax),
            'deposit_amount': -float(orig_deposit),
            'total': -float(orig_total),
        }

        # For cash refunds, "tendered" is the cash handed back to the customer
        # and there's no change — matches the reference refund receipt exactly
        # ("Paid by Cash: -47.82", "Change Due: 0.00").
        if orig_payment_method == 'cash':
            receipt_tendered, receipt_change = refund_totals['total'], 0.0
        else:
            receipt_tendered, receipt_change = None, None

        try:
            print_receipt(
                refund_sale_id, current_user, refund_cart_items, refund_totals,
                orig_payment_method, receipt_tendered, receipt_change
            )
            print_note = ""
        except Exception as print_err:
            print_note = f"\n\n(Receipt did not print: {print_err})"

        messagebox.showinfo(
            "Refund Complete",
            f"Refund processed. New Sale ID: {refund_sale_id}{print_note}"
        )
        load_sales_report()

    refund_btn = tk.Button(
        sales_tab,
        text="Refund Selected Sale",
        command=refund_selected_sale,
        **Theme.button_style(),
        width=18
    )
    refund_btn.pack(pady=(0, 10))
    bind_hover_effect(refund_btn)

    # Summary label
    summary_label = tk.Label(
        sales_tab,
        text="Transactions: 0 | Total Sales: $0.00",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 12, "bold")
    )
    summary_label.pack(pady=15)

    # Inventory Report Tab
    inventory_tab = tk.Frame(notebook, bg=Theme.BG_DARK)
    notebook.add(inventory_tab, text="Inventory Report")

    inv_header = tk.Label(
        inventory_tab,
        text="Inventory Summary",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 14, "bold")
    )
    inv_header.pack(pady=15)

    # Inventory stats frame
    stats_outer = tk.Frame(inventory_tab, **Theme.frame_style())
    stats_outer.pack(pady=10, fill="x", padx=20)

    stats_frame = tk.Frame(stats_outer, bg=Theme.BG_FRAME)
    stats_frame.pack(padx=20, pady=20)

    stat_labels = {}
    stat_names = ["Total Items", "Total Stock", "Low Stock", "Out of Stock", "Total Value"]
    
    for i, name in enumerate(stat_names):
        frame = tk.Frame(stats_frame, bg=Theme.BG_BUTTON, relief="flat", bd=0)
        frame.pack(side="left", padx=15, pady=5)
        
        tk.Label(
            frame,
            text=name,
            bg=Theme.BG_BUTTON,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, 10)
        ).pack(pady=(15, 5), padx=20)
        
        label = tk.Label(
            frame,
            text="0",
            bg=Theme.BG_BUTTON,
            fg=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, 16, "bold")
        )
        label.pack(pady=(5, 15), padx=20)
        stat_labels[name] = label

    def load_inventory_stats():
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM items")
                total_items = cur.fetchone()[0]
                stat_labels["Total Items"].config(text=str(total_items))

                cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory")
                total_stock = cur.fetchone()[0]
                stat_labels["Total Stock"].config(text=str(total_stock))

                cur.execute("""
                    SELECT COUNT(*) FROM inventory inv
                    JOIN items i ON i.item_id = inv.item_id
                    WHERE inv.quantity > 0 AND inv.quantity <= COALESCE(NULLIF(i.reorder_pt, 0), 5)
                """)
                low_stock = cur.fetchone()[0]
                stat_labels["Low Stock"].config(text=str(low_stock))

                cur.execute("SELECT COUNT(*) FROM inventory WHERE quantity = 0")
                out_stock = cur.fetchone()[0]
                stat_labels["Out of Stock"].config(text=str(out_stock))

                cur.execute("""
                    SELECT COALESCE(SUM(i.cost * inv.quantity), 0)
                    FROM items i
                    JOIN inventory inv ON i.item_id = inv.item_id
                """)
                total_value = cur.fetchone()[0]
                stat_labels["Total Value"].config(text=f"${total_value:.2f}")

            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory stats: {str(e)}")

    # Category section
    tk.Label(
        inventory_tab,
        text="Product Categories",
        bg=Theme.BG_DARK,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 12, "bold")
    ).pack(pady=(20, 10))

    cat_container = tk.Frame(inventory_tab, **Theme.frame_style())
    cat_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    cat_tree_frame = tk.Frame(cat_container, bg=Theme.BG_FRAME)
    cat_tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    cat_scroll = ttk.Scrollbar(cat_tree_frame)
    cat_scroll.pack(side="right", fill="y")

    cat_columns = ("Type", "Count", "Total Stock", "Avg Price")
    cat_tree = ttk.Treeview(
        cat_tree_frame,
        columns=cat_columns,
        show="headings",
        yscrollcommand=cat_scroll.set
    )
    cat_scroll.config(command=cat_tree.yview)

    for col in cat_columns:
        cat_tree.heading(col, text=col)
        cat_tree.column(col, width=200)

    cat_tree.pack(side="left", fill="both", expand=True)

    def load_category_stats():
        for item in cat_tree.get_children():
            cat_tree.delete(item)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COALESCE(i.type, 'Unknown') as type,
                        COUNT(*) as count,
                        COALESCE(SUM(inv.quantity), 0) as total_stock,
                        COALESCE(AVG(i.price), 0) as avg_price
                    FROM items i
                    LEFT JOIN inventory inv ON i.item_id = inv.item_id
                    GROUP BY i.type
                    ORDER BY count DESC
                """)
                
                for row in cur.fetchall():
                    cat_tree.insert("", "end", values=(
                        row[0],
                        row[1],
                        row[2],
                        f"${row[3]:.2f}"
                    ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load category stats: {str(e)}")

    refresh_inv_btn = tk.Button(
        inventory_tab,
        text="Refresh Statistics",
        command=lambda: (load_inventory_stats(), load_category_stats()),
        **Theme.button_style(),
        width=18
    )
    refresh_inv_btn.pack(pady=15)
    bind_hover_effect(refresh_inv_btn)

    # Back button at bottom
    back_btn = tk.Button(
        win,
        text="← Back to Dashboard",
        command=win.destroy,
        bg="#DC3545",
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
        relief="flat",
        width=20,
        activebackground="#C82333",
        cursor='hand2'
    )
    back_btn.pack(pady=(0, 20))

    # Load initial data
    load_inventory_stats()
    load_category_stats()