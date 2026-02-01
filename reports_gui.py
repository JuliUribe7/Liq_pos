# reports_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from db import get_conn
from theme import Theme, bind_hover_effect

def open_reports_window():
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
                        COUNT(si.sale_item_id) as items_count
                    FROM sales s
                    LEFT JOIN sale_items si ON s.sale_id = si.sale_id
                    WHERE {date_filter}
                    GROUP BY s.sale_id, s.sale_date, s.cashier, s.total_amount
                    ORDER BY s.sale_date DESC
                """
                
                cur.execute(query)
                rows = cur.fetchall()
                
                total_sales = 0
                total_transactions = 0
                
                for row in rows:
                    sale_id, sale_date, cashier, total, items = row
                    sales_tree.insert("", "end", values=(
                        sale_id,
                        sale_date.strftime("%Y-%m-%d %H:%M") if sale_date else "",
                        cashier or "",
                        f"${total:.2f}" if total else "$0.00",
                        items or 0
                    ))
                    total_sales += total if total else 0
                    total_transactions += 1

                summary_text = f"Transactions: {total_transactions} | Total Sales: ${total_sales:.2f}"
                if total_transactions > 0:
                    avg_sale = total_sales / total_transactions
                    summary_text += f" | Average: ${avg_sale:.2f}"
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

    sales_columns = ("Sale ID", "Date", "Cashier", "Total", "Items")
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

    sales_tree.column("Sale ID", width=80)
    sales_tree.column("Date", width=150)
    sales_tree.column("Cashier", width=150)
    sales_tree.column("Total", width=120)
    sales_tree.column("Items", width=120)

    sales_tree.pack(side="left", fill="both", expand=True)

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

                cur.execute("SELECT COUNT(*) FROM inventory WHERE quantity <= 5 AND quantity > 0")
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