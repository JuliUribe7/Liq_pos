# reports_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from db import get_conn
from theme import Theme, bind_hover_effect
from receipt import print_receipt, STORE_NAME

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

    # Takings Tab — cash and card are always shown separately, never combined
    # into one figure, per spec ("do NOT mix them, they must be separate").
    takings_tab = tk.Frame(notebook, bg=Theme.BG_DARK)
    notebook.add(takings_tab, text="Takings")

    tk.Label(
        takings_tab,
        text="Takings",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 14, "bold")
    ).pack(pady=15)

    takings_date_frame = tk.Frame(takings_tab, **Theme.frame_style())
    takings_date_frame.pack(pady=(0, 15), padx=20, fill="x")

    takings_date_inner = tk.Frame(takings_date_frame, bg=Theme.BG_FRAME)
    takings_date_inner.pack(padx=20, pady=15)

    tk.Label(
        takings_date_inner,
        text="Period:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(side="left", padx=(0, 15))

    takings_period_var = tk.StringVar(value="today")
    for text, value in periods:
        tk.Radiobutton(
            takings_date_inner,
            text=text,
            variable=takings_period_var,
            value=value,
            bg=Theme.BG_FRAME,
            fg=Theme.TEXT_PRIMARY,
            selectcolor=Theme.BG_BUTTON,
            activebackground=Theme.BG_FRAME,
            activeforeground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, 10)
        ).pack(side="left", padx=10)

    takings_columns_frame = tk.Frame(takings_tab, bg=Theme.BG_DARK)
    takings_columns_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    takings_labels = {}

    def _takings_column(title):
        col = tk.Frame(takings_columns_frame, **Theme.frame_style())
        col.pack(side="left", fill="both", expand=True, padx=10)

        tk.Label(
            col, text=title, bg=Theme.BG_FRAME, fg=Theme.ACCENT_GOLD,
            font=(Theme.FONT_FAMILY, 13, "bold")
        ).pack(pady=(15, 10))

        for stat_name in ("Sales", "Refunds", "Balance"):
            row = tk.Frame(col, bg=Theme.BG_BUTTON, relief="flat", bd=0)
            row.pack(fill="x", padx=15, pady=6)
            tk.Label(
                row, text=stat_name, bg=Theme.BG_BUTTON, fg=Theme.TEXT_SECONDARY,
                font=(Theme.FONT_FAMILY, 10)
            ).pack(anchor="w", padx=15, pady=(10, 2))
            value_label = tk.Label(
                row, text="--", bg=Theme.BG_BUTTON, fg=Theme.TEXT_PRIMARY,
                font=(Theme.FONT_FAMILY, 14, "bold")
            )
            value_label.pack(anchor="w", padx=15, pady=(0, 10))
            takings_labels[f"{title} {stat_name}"] = value_label

    _takings_column("Cash")
    _takings_column("Card")

    def load_takings():
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                period = takings_period_var.get()
                if period == "today":
                    date_filter = "DATE(sale_date) = CURRENT_DATE"
                elif period == "week":
                    date_filter = "sale_date >= CURRENT_DATE - INTERVAL '7 days'"
                elif period == "month":
                    date_filter = "sale_date >= CURRENT_DATE - INTERVAL '30 days'"
                else:
                    date_filter = "1=1"

                # Voided (incomplete) sales are excluded entirely — they never
                # really happened, so they shouldn't count toward takings.
                for method, title in [('cash', 'Cash'), ('card', 'Card')]:
                    cur.execute(f"""
                        SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
                        FROM sales
                        WHERE payment_method = %s AND is_refund = FALSE
                          AND status != 'incomplete' AND {date_filter}
                    """, (method,))
                    sales_count, sales_total = cur.fetchone()
                    sales_total = float(sales_total)

                    cur.execute(f"""
                        SELECT COUNT(*), COALESCE(SUM(ABS(total_amount)), 0)
                        FROM sales
                        WHERE payment_method = %s AND is_refund = TRUE
                          AND status != 'incomplete' AND {date_filter}
                    """, (method,))
                    refund_count, refund_total = cur.fetchone()
                    refund_total = float(refund_total)

                    net_balance = sales_total - refund_total

                    takings_labels[f"{title} Sales"].config(text=f"{sales_count} orders / ${sales_total:.2f}")
                    takings_labels[f"{title} Refunds"].config(text=f"{refund_count} orders / ${refund_total:.2f}")
                    takings_labels[f"{title} Balance"].config(text=f"${net_balance:.2f}")
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load takings: {str(e)}")

    takings_load_btn = tk.Button(
        takings_date_inner,
        text="Load Takings",
        command=load_takings,
        **Theme.button_style(),
        width=14
    )
    takings_load_btn.pack(side="left", padx=20)
    bind_hover_effect(takings_load_btn)

    # Trending Tab
    trending_tab = tk.Frame(notebook, bg=Theme.BG_DARK)
    notebook.add(trending_tab, text="Trending")

    tk.Label(
        trending_tab,
        text="Trending — Items Most Sold",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 14, "bold")
    ).pack(pady=15)

    trending_tree_container = tk.Frame(trending_tab, **Theme.frame_style())
    trending_tree_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    trending_tree_frame = tk.Frame(trending_tree_container, bg=Theme.BG_FRAME)
    trending_tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    trending_scroll = ttk.Scrollbar(trending_tree_frame)
    trending_scroll.pack(side="right", fill="y")

    trending_columns = ("Rank", "Item", "Qty Sold", "Price")
    trending_tree = ttk.Treeview(
        trending_tree_frame,
        columns=trending_columns,
        show="headings",
        yscrollcommand=trending_scroll.set
    )
    trending_scroll.config(command=trending_tree.yview)

    trending_tree.heading("Rank", text="Rank")
    trending_tree.heading("Item", text="Item")
    trending_tree.heading("Qty Sold", text="Qty Sold")
    trending_tree.heading("Price", text="Price")

    trending_tree.column("Rank", width=60, anchor="center")
    trending_tree.column("Item", width=350)
    trending_tree.column("Qty Sold", width=100, anchor="center")
    trending_tree.column("Price", width=100, anchor="e")

    trending_tree.pack(side="left", fill="both", expand=True)

    # "Show every 10 entries" — a page at a time, fetching 11 rows to know
    # whether a next page exists without a separate COUNT query.
    TRENDING_PAGE_SIZE = 10
    trending_page = {"offset": 0}

    def load_trending():
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.item_id, i.brand, i.price, SUM(si.quantity) AS qty_sold
                    FROM sale_items si
                    JOIN items i ON si.item_id = i.item_id
                    JOIN sales s ON si.sale_id = s.sale_id
                    WHERE s.status != 'incomplete'
                    GROUP BY i.item_id, i.brand, i.price
                    ORDER BY qty_sold DESC
                    LIMIT %s OFFSET %s
                """, (TRENDING_PAGE_SIZE + 1, trending_page["offset"]))
                rows = cur.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trending items: {str(e)}")
            return

        for item in trending_tree.get_children():
            trending_tree.delete(item)

        has_next = len(rows) > TRENDING_PAGE_SIZE
        rows = rows[:TRENDING_PAGE_SIZE]
        start_rank = trending_page["offset"] + 1

        for i, (item_id, brand, price, qty_sold) in enumerate(rows):
            trending_tree.insert("", "end", values=(
                start_rank + i,
                brand or "",
                qty_sold or 0,
                f"${float(price):.2f}" if price is not None else "$0.00"
            ))

        page_number = (trending_page["offset"] // TRENDING_PAGE_SIZE) + 1
        trending_page_label.config(text=f"Page {page_number}")
        trending_prev_btn.config(state="normal" if trending_page["offset"] > 0 else "disabled")
        trending_next_btn.config(state="normal" if has_next else "disabled")

    def trending_prev_page():
        trending_page["offset"] = max(0, trending_page["offset"] - TRENDING_PAGE_SIZE)
        load_trending()

    def trending_next_page():
        trending_page["offset"] += TRENDING_PAGE_SIZE
        load_trending()

    trending_nav_frame = tk.Frame(trending_tab, bg=Theme.BG_DARK)
    trending_nav_frame.pack(pady=(0, 15))

    trending_prev_btn = tk.Button(
        trending_nav_frame, text="< Prev", command=trending_prev_page,
        **Theme.button_style(), width=10
    )
    trending_prev_btn.pack(side="left", padx=5)
    bind_hover_effect(trending_prev_btn)

    trending_page_label = tk.Label(
        trending_nav_frame, text="Page 1", bg=Theme.BG_DARK, fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, "bold")
    )
    trending_page_label.pack(side="left", padx=15)

    trending_next_btn = tk.Button(
        trending_nav_frame, text="Next >", command=trending_next_page,
        **Theme.button_style(), width=10
    )
    trending_next_btn.pack(side="left", padx=5)
    bind_hover_effect(trending_next_btn)

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

    # Day Report Tab — a single formatted text report for one business date,
    # mirroring a real printed end-of-day report. Several lines from the
    # original reference (Close Nbr/Sta#, customer-account payments, expense/
    # house payouts, bottle-return redemption, per-card-network breakdown,
    # two-way non-taxable/tax-exempt split, and Over/Short reconciliation
    # against a physical cash count) are intentionally omitted — none of
    # those concepts exist anywhere else in this app.
    day_report_tab = tk.Frame(notebook, bg=Theme.BG_DARK)
    notebook.add(day_report_tab, text="Day Report")

    tk.Label(
        day_report_tab,
        text="Day Report",
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 14, "bold")
    ).pack(pady=15)

    day_date_frame = tk.Frame(day_report_tab, **Theme.frame_style())
    day_date_frame.pack(pady=(0, 15), padx=20, fill="x")

    day_date_inner = tk.Frame(day_date_frame, bg=Theme.BG_FRAME)
    day_date_inner.pack(padx=20, pady=15)

    tk.Label(
        day_date_inner,
        text="Business Date (YYYY-MM-DD):",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(side="left", padx=(0, 10))

    day_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    day_date_entry = tk.Entry(day_date_inner, textvariable=day_date_var, **Theme.entry_style(), width=14)
    day_date_entry.pack(side="left", ipady=6)

    day_text_container = tk.Frame(day_report_tab, **Theme.frame_style())
    day_text_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    day_text_scroll = ttk.Scrollbar(day_text_container)
    day_text_scroll.pack(side="right", fill="y")

    day_report_text = tk.Text(
        day_text_container,
        bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY,
        font=("Consolas", 10),
        relief="flat", wrap="none",
        yscrollcommand=day_text_scroll.set,
        state="disabled"
    )
    day_report_text.pack(side="left", fill="both", expand=True, padx=15, pady=15)
    day_text_scroll.config(command=day_report_text.yview)

    DAY_REPORT_WIDTH = 50

    def _day_line(left, right, width=DAY_REPORT_WIDTH):
        left, right = str(left), str(right)
        space = max(1, width - len(left) - len(right))
        return f"{left}{' ' * space}{right}"

    def _money(value):
        value = float(value or 0)
        return f"-${abs(value):.2f}" if value < 0 else f"${value:.2f}"

    def generate_day_report():
        date_str = day_date_var.get().strip()
        try:
            business_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Enter the date as YYYY-MM-DD.")
            return

        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                # Sales by hour (gross, completed, non-refund sales only)
                cur.execute("""
                    SELECT EXTRACT(HOUR FROM sale_date)::int AS hr, COUNT(*),
                           COALESCE(SUM(COALESCE(subtotal, total_amount + discount_amount - tax_amount - deposit_amount) - discount_amount), 0)
                    FROM sales
                    WHERE DATE(sale_date) = %s AND is_refund = FALSE AND status != 'incomplete'
                    GROUP BY hr ORDER BY hr
                """, (business_date,))
                hourly = cur.fetchall()

                cur.execute("""
                    SELECT COUNT(*), COALESCE(SUM(COALESCE(subtotal, total_amount + discount_amount - tax_amount - deposit_amount) - discount_amount), 0),
                           COALESCE(SUM(tax_amount), 0), COALESCE(SUM(deposit_amount), 0)
                    FROM sales
                    WHERE DATE(sale_date) = %s AND is_refund = FALSE AND status != 'incomplete'
                """, (business_date,))
                nbr_sales, sales_pretax, sales_tax, bottle_deposits = cur.fetchone()
                sales_pretax = float(sales_pretax)
                sales_tax = float(sales_tax)
                bottle_deposits = float(bottle_deposits)
                total_in = sales_pretax + sales_tax + bottle_deposits

                cur.execute("""
                    SELECT COALESCE(SUM(ABS(total_amount)), 0)
                    FROM sales
                    WHERE DATE(sale_date) = %s AND is_refund = TRUE AND status != 'incomplete'
                """, (business_date,))
                refunds = float(cur.fetchone()[0])
                total_deposit_expected = total_in - refunds

                cash_total = card_total = 0.0
                for method in ('cash', 'card'):
                    cur.execute("""
                        SELECT COALESCE(SUM(total_amount), 0) FROM sales
                        WHERE DATE(sale_date) = %s AND payment_method = %s
                          AND is_refund = FALSE AND status != 'incomplete'
                    """, (business_date, method))
                    val = float(cur.fetchone()[0])
                    if method == 'cash':
                        cash_total = val
                    else:
                        card_total = val

                cur.execute("""
                    SELECT COALESCE(SUM(si.quantity), 0)
                    FROM sale_items si
                    JOIN sales s ON si.sale_id = s.sale_id
                    WHERE DATE(s.sale_date) = %s AND s.is_refund = FALSE AND s.status != 'incomplete'
                """, (business_date,))
                nbr_items = cur.fetchone()[0] or 0

                cur.execute("""
                    SELECT COALESCE(SUM(si.quantity * si.price), 0)
                    FROM sale_items si
                    JOIN sales s ON si.sale_id = s.sale_id
                    JOIN items i ON si.item_id = i.item_id
                    WHERE DATE(s.sale_date) = %s AND s.is_refund = FALSE AND s.status != 'incomplete'
                      AND i.sales_tax = FALSE
                """, (business_date,))
                non_taxable = float(cur.fetchone()[0])
            conn.close()
        except Exception as e:
            if conn is not None:
                conn.close()
            messagebox.showerror("Error", f"Failed to generate day report: {str(e)}")
            return

        lines = []
        lines.append(f"Company: {STORE_NAME}")
        lines.append(f"Business Date: {business_date.strftime('%m/%d/%Y %A')}")
        lines.append(f"Report Created: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")
        lines.append("=" * DAY_REPORT_WIDTH)
        lines.append("SALES BY HOUR")
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(f"{'Hour':<8}{'#Sls':>6}{'%of#':>8}{'$Sales':>14}{'%of$':>8}")
        for hr, count, hr_sales in hourly:
            hr_sales = float(hr_sales)
            pct_count = (count / nbr_sales * 100) if nbr_sales else 0
            pct_sales = (hr_sales / sales_pretax * 100) if sales_pretax else 0
            lines.append(
                f"{hr:02d}:00{'':<3}{count:>6}{pct_count:>7.1f}%{hr_sales:>13.2f} {pct_sales:>6.1f}%"
            )
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(_day_line("Total", f"{nbr_sales}   {_money(sales_pretax)}"))
        lines.append("")

        lines.append("TOTAL IN")
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(_day_line("Sales", _money(sales_pretax)))
        lines.append(_day_line("Sales Tax", _money(sales_tax)))
        lines.append(_day_line("Bottle Deposits", _money(bottle_deposits)))
        lines.append(_day_line("Total In", _money(total_in)))
        lines.append("")

        lines.append("PAYOUTS/CHARGES")
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(_day_line("Refunds", _money(refunds)))
        lines.append(_day_line("Total Payouts/Charges", _money(refunds)))
        lines.append("")

        lines.append("DEPOSIT (by tender)")
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(_day_line("Cash", _money(cash_total)))
        lines.append(_day_line("Card", _money(card_total)))
        lines.append(_day_line("Sub-Total", _money(cash_total + card_total)))
        lines.append(_day_line("Total Deposit Expected", _money(total_deposit_expected)))
        lines.append("")

        lines.append("SALES BREAKDOWN")
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(f"Nbr Items: {nbr_items}   Nbr Sales: {nbr_sales}")
        avg_ticket = (sales_pretax / nbr_sales) if nbr_sales else 0
        avg_price = (sales_pretax / nbr_items) if nbr_items else 0
        lines.append(_day_line("Avg Ticket (excl tax)", _money(avg_ticket)))
        lines.append(_day_line("Avg Price (excl tax)", _money(avg_price)))
        lines.append("")

        lines.append("TAXES BREAKDOWN")
        lines.append("-" * DAY_REPORT_WIDTH)
        lines.append(_day_line("Sales Tax", _money(sales_tax)))
        lines.append(_day_line("Non-Taxable Items", _money(non_taxable)))

        day_report_text.config(state="normal")
        day_report_text.delete("1.0", tk.END)
        day_report_text.insert("1.0", "\n".join(lines))
        day_report_text.config(state="disabled")

    day_generate_btn = tk.Button(
        day_date_inner,
        text="Generate Report",
        command=generate_day_report,
        **Theme.button_style(),
        width=16
    )
    day_generate_btn.pack(side="left", padx=15)
    bind_hover_effect(day_generate_btn)

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
    load_takings()
    load_trending()