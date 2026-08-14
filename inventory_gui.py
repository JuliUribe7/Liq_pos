# inventory_gui.py
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

from db import get_conn
from theme import Theme, bind_hover_effect


def _parse_int_or_zero(value):
    value = (value or "").strip()
    return int(value) if value else 0


def _parse_int_or_none(value):
    value = (value or "").strip()
    return int(value) if value else None


def _parse_float_or_zero(value):
    value = (value or "").strip()
    return float(value) if value else 0.0


def _parse_float_or_none(value):
    value = (value or "").strip()
    return float(value) if value else None


def _parse_date_or_none(value):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _fmt_date(value):
    return value.strftime("%Y-%m-%d") if value else ""


def _make_scrollable(parent, bg):
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    inner = tk.Frame(canvas, bg=bg)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner_configure)

    def _on_canvas_configure(event):
        canvas.itemconfig(window_id, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return inner


def _section_label(parent, text):
    tk.Label(
        parent, text=text, bg=parent['bg'], fg=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, 12, "bold")
    ).pack(anchor="w", pady=(15, 5), padx=15)


def _field_row(parent, label_text, widget_factory):
    row = tk.Frame(parent, bg=parent['bg'])
    row.pack(fill="x", padx=15, pady=4)
    tk.Label(
        row, text=label_text, bg=parent['bg'], fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 10), width=18, anchor="w"
    ).pack(side="left")
    widget = widget_factory(row)
    widget.pack(side="left", fill="x", expand=True, ipady=3)
    return widget


def _fetch_suppliers():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT supplier_id, company_name FROM suppliers
                WHERE company_name IS NOT NULL ORDER BY company_name
            """)
            rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def _fetch_item(item_id):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT item_id, barcode, supplier_id, brand, size, price, cost, type,
                   description, case_qty, vendor_item, item_notes,
                   par_level, reorder_pt, on_order, order_lot, last_order_date, last_receive_date,
                   deposit_sale_enabled, deposit_sale_amount, deposit_return_enabled, deposit_return_amount,
                   sales_tax, discount_ok, last_cost, case_cost, last_case_cost, case_price,
                   twofer_price, threefer_price, disc_pool
            FROM items WHERE item_id = %s
        """, (item_id,))
        row = cur.fetchone()
        cur.execute("SELECT quantity FROM inventory WHERE item_id = %s", (item_id,))
        inv_row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    cols = [
        'item_id', 'barcode', 'supplier_id', 'brand', 'size', 'price', 'cost', 'type',
        'description', 'case_qty', 'vendor_item', 'item_notes',
        'par_level', 'reorder_pt', 'on_order', 'order_lot', 'last_order_date', 'last_receive_date',
        'deposit_sale_enabled', 'deposit_sale_amount', 'deposit_return_enabled', 'deposit_return_amount',
        'sales_tax', 'discount_ok', 'last_cost', 'case_cost', 'last_case_cost', 'case_price',
        'twofer_price', 'threefer_price', 'disc_pool',
    ]
    data = dict(zip(cols, row))
    data['quantity'] = inv_row[0] if inv_row else 0
    return data


def _fetch_computed_stats(item_id):
    if item_id is None:
        return {'last_sale': None, 'mtd': 0, 'ytd': 0}
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(s.sale_date) FROM sale_items si
                JOIN sales s ON si.sale_id = s.sale_id WHERE si.item_id = %s
            """, (item_id,))
            last_sale = cur.fetchone()[0]

            cur.execute("""
                SELECT COALESCE(SUM(si.quantity), 0) FROM sale_items si
                JOIN sales s ON si.sale_id = s.sale_id
                WHERE si.item_id = %s AND date_trunc('month', s.sale_date) = date_trunc('month', CURRENT_DATE)
            """, (item_id,))
            mtd = cur.fetchone()[0]

            cur.execute("""
                SELECT COALESCE(SUM(si.quantity), 0) FROM sale_items si
                JOIN sales s ON si.sale_id = s.sale_id
                WHERE si.item_id = %s AND date_trunc('year', s.sale_date) = date_trunc('year', CURRENT_DATE)
            """, (item_id,))
            ytd = cur.fetchone()[0]
        conn.close()
        return {'last_sale': last_sale, 'mtd': mtd, 'ytd': ytd}
    except Exception:
        return {'last_sale': None, 'mtd': 0, 'ytd': 0}


def _open_item_detail_dialog(parent_win, mode, item_id=None, prefill_barcode=None, item_list=None, on_saved=None):
    item_list = item_list or []
    suppliers = _fetch_suppliers()
    supplier_name_to_id = {name: sid for sid, name in suppliers}

    dialog = tk.Toplevel(parent_win)
    dialog.title("Item Details")
    dialog.geometry("780x680")
    dialog.config(bg=Theme.BG_DARK)
    dialog.transient(parent_win)

    state = {'item_id': item_id, 'mode': mode}

    # --- Top nav/status bar ---
    nav_frame = tk.Frame(dialog, bg=Theme.BG_DARK)
    nav_frame.pack(fill="x", padx=15, pady=(15, 5))

    status_label = tk.Label(nav_frame, text="", bg=Theme.BG_DARK, fg=Theme.TEXT_SUCCESS,
                             font=(Theme.FONT_FAMILY, 10, "bold"))
    status_label.pack(side="right")

    def flash_status(text, ok=True):
        status_label.config(text=text, fg=Theme.TEXT_SUCCESS if ok else Theme.TEXT_ERROR)
        dialog.after(2500, lambda: status_label.config(text="") if dialog.winfo_exists() else None)

    nav_btns_frame = tk.Frame(nav_frame, bg=Theme.BG_DARK)
    nav_btns_frame.pack(side="left")

    # --- Notebook ---
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TNotebook", background=Theme.BG_DARK, borderwidth=0)
    style.configure("TNotebook.Tab", background=Theme.BG_BUTTON, foreground=Theme.TEXT_PRIMARY,
                     padding=[14, 8], font=(Theme.FONT_FAMILY, 10, 'bold'))
    style.map("TNotebook.Tab", background=[('selected', Theme.ACCENT_GOLD)],
              foreground=[('selected', Theme.TEXT_DARK)])

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=15, pady=10)

    details_tab = tk.Frame(notebook, bg=Theme.BG_FRAME)
    costs_tab = tk.Frame(notebook, bg=Theme.BG_FRAME)
    notebook.add(details_tab, text="Details")
    notebook.add(costs_tab, text="Costs & Pricing")

    # ================= Details tab =================
    details_inner = _make_scrollable(details_tab, Theme.BG_FRAME)

    brand_var = tk.StringVar()
    description_var = tk.StringVar()
    type_var = tk.StringVar()
    size_var = tk.StringVar()
    case_qty_var = tk.StringVar()
    vendor_var = tk.StringVar()
    vendor_item_var = tk.StringVar()
    barcode_var = tk.StringVar(value=prefill_barcode or "")
    par_level_var = tk.StringVar(value="0")
    reorder_pt_var = tk.StringVar(value="0")
    on_order_var = tk.StringVar(value="0")
    order_lot_var = tk.StringVar(value="case")
    last_order_var = tk.StringVar()
    last_receive_var = tk.StringVar()
    deposit_sale_enabled_var = tk.BooleanVar(value=False)
    deposit_sale_amount_var = tk.StringVar(value="0.00")
    deposit_return_enabled_var = tk.BooleanVar(value=False)
    deposit_return_amount_var = tk.StringVar(value="0.00")
    sales_tax_var = tk.BooleanVar(value=True)
    discount_ok_var = tk.BooleanVar(value=True)
    on_hand_var = tk.StringVar(value="0")

    _section_label(details_inner, "Product Info")
    _field_row(details_inner, "Brand", lambda p: tk.Entry(p, textvariable=brand_var, **Theme.entry_style()))
    _field_row(details_inner, "Description", lambda p: tk.Entry(p, textvariable=description_var, **Theme.entry_style()))
    _field_row(details_inner, "Type", lambda p: tk.Entry(p, textvariable=type_var, **Theme.entry_style()))
    _field_row(details_inner, "Size", lambda p: tk.Entry(p, textvariable=size_var, **Theme.entry_style()))
    _field_row(details_inner, "Case Qty", lambda p: tk.Entry(p, textvariable=case_qty_var, **Theme.entry_style()))
    _field_row(details_inner, "Barcode", lambda p: tk.Entry(p, textvariable=barcode_var, **Theme.entry_style()))
    _field_row(details_inner, "On Hand", lambda p: tk.Entry(p, textvariable=on_hand_var, **Theme.entry_style()))

    _section_label(details_inner, "Vendor & Purchasing")
    vendor_combo = _field_row(details_inner, "Vendor", lambda p: ttk.Combobox(
        p, textvariable=vendor_var, values=[name for _, name in suppliers], state="normal"))
    _field_row(details_inner, "Vendor Item", lambda p: tk.Entry(p, textvariable=vendor_item_var, **Theme.entry_style()))
    _field_row(details_inner, "Last Order (YYYY-MM-DD)", lambda p: tk.Entry(p, textvariable=last_order_var, **Theme.entry_style()))
    _field_row(details_inner, "Last Receive (YYYY-MM-DD)", lambda p: tk.Entry(p, textvariable=last_receive_var, **Theme.entry_style()))

    _section_label(details_inner, "Stock & Reorder")
    _field_row(details_inner, "Par Level", lambda p: tk.Entry(p, textvariable=par_level_var, **Theme.entry_style()))
    _field_row(details_inner, "Reorder Point", lambda p: tk.Entry(p, textvariable=reorder_pt_var, **Theme.entry_style()))
    _field_row(details_inner, "On Order", lambda p: tk.Entry(p, textvariable=on_order_var, **Theme.entry_style()))

    order_lot_row = tk.Frame(details_inner, bg=Theme.BG_FRAME)
    order_lot_row.pack(fill="x", padx=15, pady=4)
    tk.Label(order_lot_row, text="Order Lot", bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY,
             font=(Theme.FONT_FAMILY, 10), width=18, anchor="w").pack(side="left")
    for label, value in [("Case", "case"), ("Unit", "unit")]:
        tk.Radiobutton(order_lot_row, text=label, variable=order_lot_var, value=value,
                        bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_BUTTON,
                        activebackground=Theme.BG_FRAME, font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=5)

    _section_label(details_inner, "Deposits & Tax")

    deposit_sale_row = tk.Frame(details_inner, bg=Theme.BG_FRAME)
    deposit_sale_row.pack(fill="x", padx=15, pady=4)
    tk.Checkbutton(deposit_sale_row, text="Deposit on Sale", variable=deposit_sale_enabled_var,
                    bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_BUTTON,
                    activebackground=Theme.BG_FRAME, font=(Theme.FONT_FAMILY, 10)).pack(side="left")
    tk.Entry(deposit_sale_row, textvariable=deposit_sale_amount_var, **Theme.entry_style(), width=10).pack(side="left", padx=10, ipady=3)

    deposit_return_row = tk.Frame(details_inner, bg=Theme.BG_FRAME)
    deposit_return_row.pack(fill="x", padx=15, pady=4)
    tk.Checkbutton(deposit_return_row, text="Deposit on Return", variable=deposit_return_enabled_var,
                    bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_BUTTON,
                    activebackground=Theme.BG_FRAME, font=(Theme.FONT_FAMILY, 10)).pack(side="left")
    tk.Entry(deposit_return_row, textvariable=deposit_return_amount_var, **Theme.entry_style(), width=10).pack(side="left", padx=10, ipady=3)

    tax_discount_row = tk.Frame(details_inner, bg=Theme.BG_FRAME)
    tax_discount_row.pack(fill="x", padx=15, pady=4)
    tk.Checkbutton(tax_discount_row, text="Sales Tax", variable=sales_tax_var,
                    bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_BUTTON,
                    activebackground=Theme.BG_FRAME, font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=(0, 20))
    tk.Checkbutton(tax_discount_row, text="Discount OK", variable=discount_ok_var,
                    bg=Theme.BG_FRAME, fg=Theme.TEXT_PRIMARY, selectcolor=Theme.BG_BUTTON,
                    activebackground=Theme.BG_FRAME, font=(Theme.FONT_FAMILY, 10)).pack(side="left")

    _section_label(details_inner, "Notes")
    notes_text = tk.Text(details_inner, height=4, **Theme.entry_style())
    notes_text.pack(fill="x", padx=15, pady=(4, 10))

    stats_label = tk.Label(details_inner, text="", bg=Theme.BG_FRAME, fg=Theme.TEXT_SECONDARY,
                            font=(Theme.FONT_FAMILY, 10), justify="left", anchor="w")
    stats_label.pack(fill="x", padx=15, pady=(0, 15))

    # ================= Costs & Pricing tab =================
    costs_inner = _make_scrollable(costs_tab, Theme.BG_FRAME)

    unit_cost_var = tk.StringVar(value="0.00")
    case_cost_var = tk.StringVar(value="0.00")
    last_cost_var = tk.StringVar(value="")
    last_case_cost_var = tk.StringVar(value="")
    markup_var = tk.StringVar(value="0.00%")
    margin_var = tk.StringVar(value="0.00%")
    price_var = tk.StringVar(value="0.00")
    case_price_var = tk.StringVar(value="0.00")
    twofer_price_var = tk.StringVar(value="")
    threefer_price_var = tk.StringVar(value="")
    disc_pool_var = tk.StringVar(value="")

    _section_label(costs_inner, "Costs")
    _field_row(costs_inner, "Unit Cost", lambda p: tk.Entry(p, textvariable=unit_cost_var, **Theme.entry_style()))
    _field_row(costs_inner, "Case Cost", lambda p: tk.Entry(p, textvariable=case_cost_var, **Theme.entry_style()))
    _field_row(costs_inner, "Last Cost", lambda p: tk.Entry(p, textvariable=last_cost_var, state="readonly", **Theme.entry_style()))
    _field_row(costs_inner, "Last Case Cost", lambda p: tk.Entry(p, textvariable=last_case_cost_var, state="readonly", **Theme.entry_style()))
    _field_row(costs_inner, "Markup %", lambda p: tk.Entry(p, textvariable=markup_var, state="readonly", **Theme.entry_style()))
    _field_row(costs_inner, "Margin %", lambda p: tk.Entry(p, textvariable=margin_var, state="readonly", **Theme.entry_style()))

    _section_label(costs_inner, "Prices")
    _field_row(costs_inner, "Standard Price", lambda p: tk.Entry(p, textvariable=price_var, **Theme.entry_style()))
    _field_row(costs_inner, "Case Price", lambda p: tk.Entry(p, textvariable=case_price_var, **Theme.entry_style()))
    _field_row(costs_inner, "TwoFer Price", lambda p: tk.Entry(p, textvariable=twofer_price_var, **Theme.entry_style()))
    _field_row(costs_inner, "ThreeFer Price", lambda p: tk.Entry(p, textvariable=threefer_price_var, **Theme.entry_style()))
    _field_row(costs_inner, "Discount Pool", lambda p: tk.Entry(p, textvariable=disc_pool_var, **Theme.entry_style()))

    def refresh_markup_margin(*_):
        try:
            cost = float(unit_cost_var.get() or 0)
            price = float(price_var.get() or 0)
        except ValueError:
            return
        if cost > 0:
            markup_var.set(f"{((price - cost) / cost * 100):.2f}%")
        else:
            markup_var.set("--")
        if price > 0:
            margin_var.set(f"{((price - cost) / price * 100):.2f}%")
        else:
            margin_var.set("--")

    unit_cost_var.trace_add("write", refresh_markup_margin)
    price_var.trace_add("write", refresh_markup_margin)

    # ================= Load / populate =================
    def populate_fields(data):
        stats = _fetch_computed_stats(data['item_id'] if data else None)

        brand_var.set(data['brand'] if data else "")
        description_var.set((data.get('description') if data else "") or "")
        type_var.set((data.get('type') if data else "") or "")
        size_var.set((data.get('size') if data else "") or "")
        case_qty_var.set(str(data.get('case_qty')) if data and data.get('case_qty') is not None else "")
        vendor_var.set("")
        if data and data.get('supplier_id'):
            for sid, name in suppliers:
                if sid == data['supplier_id']:
                    vendor_var.set(name)
                    break
        vendor_item_var.set((data.get('vendor_item') if data else "") or "")
        barcode_var.set((data.get('barcode') if data else prefill_barcode) or "")
        par_level_var.set(str(data.get('par_level', 0)) if data else "0")
        reorder_pt_var.set(str(data.get('reorder_pt', 0)) if data else "0")
        on_order_var.set(str(data.get('on_order', 0)) if data else "0")
        order_lot_var.set((data.get('order_lot') if data else "case") or "case")
        last_order_var.set(_fmt_date(data.get('last_order_date')) if data else "")
        last_receive_var.set(_fmt_date(data.get('last_receive_date')) if data else "")
        deposit_sale_enabled_var.set(bool(data.get('deposit_sale_enabled')) if data else False)
        deposit_sale_amount_var.set(f"{data.get('deposit_sale_amount', 0):.2f}" if data else "0.00")
        deposit_return_enabled_var.set(bool(data.get('deposit_return_enabled')) if data else False)
        deposit_return_amount_var.set(f"{data.get('deposit_return_amount', 0):.2f}" if data else "0.00")
        sales_tax_var.set(bool(data.get('sales_tax', True)) if data else True)
        discount_ok_var.set(bool(data.get('discount_ok', True)) if data else True)
        on_hand_var.set(str(data.get('quantity', 0)) if data else "0")

        notes_text.delete("1.0", tk.END)
        if data and data.get('item_notes'):
            notes_text.insert("1.0", data['item_notes'])

        last_sale_text = _fmt_date(stats['last_sale']) if stats['last_sale'] else "Never"
        stats_label.config(text=f"Last Sale: {last_sale_text}    MTD Sold: {stats['mtd']}    YTD Sold: {stats['ytd']}")

        unit_cost_var.set(f"{data.get('cost') or 0:.2f}" if data else "0.00")
        case_cost_var.set(f"{data.get('case_cost') or 0:.2f}" if data else "0.00")
        last_cost_var.set(f"{data['last_cost']:.2f}" if data and data.get('last_cost') is not None else "")
        last_case_cost_var.set(f"{data['last_case_cost']:.2f}" if data and data.get('last_case_cost') is not None else "")
        price_var.set(f"{data.get('price') or 0:.2f}" if data else "0.00")
        case_price_var.set(f"{data.get('case_price') or 0:.2f}" if data else "0.00")
        twofer_price_var.set(f"{data['twofer_price']:.2f}" if data and data.get('twofer_price') is not None else "")
        threefer_price_var.set(f"{data['threefer_price']:.2f}" if data and data.get('threefer_price') is not None else "")
        disc_pool_var.set((data.get('disc_pool') if data else "") or "")
        refresh_markup_margin()

        update_nav_state()

    def load_item(new_item_id):
        state['item_id'] = new_item_id
        data = _fetch_item(new_item_id) if new_item_id is not None else None
        populate_fields(data)

    # ================= Navigation =================
    def current_index():
        try:
            return item_list.index(state['item_id'])
        except ValueError:
            return -1

    def go_first():
        if item_list:
            load_item(item_list[0])

    def go_prev():
        idx = current_index()
        if idx > 0:
            load_item(item_list[idx - 1])

    def go_next():
        idx = current_index()
        if 0 <= idx < len(item_list) - 1:
            load_item(item_list[idx + 1])

    def go_last():
        if item_list:
            load_item(item_list[-1])

    nav_first_btn = tk.Button(nav_btns_frame, text="|< First", command=go_first, **Theme.button_style(), width=8)
    nav_prev_btn = tk.Button(nav_btns_frame, text="< Prev", command=go_prev, **Theme.button_style(), width=8)
    nav_next_btn = tk.Button(nav_btns_frame, text="Next >", command=go_next, **Theme.button_style(), width=8)
    nav_last_btn = tk.Button(nav_btns_frame, text="Last >|", command=go_last, **Theme.button_style(), width=8)
    for b in (nav_first_btn, nav_prev_btn, nav_next_btn, nav_last_btn):
        b.pack(side="left", padx=3)
        bind_hover_effect(b)

    def update_nav_state():
        nav_enabled = state['mode'] == 'edit' and bool(item_list)
        widget_state = "normal" if nav_enabled else "disabled"
        for b in (nav_first_btn, nav_prev_btn, nav_next_btn, nav_last_btn):
            b.config(state=widget_state)

    # ================= Save / Close =================
    def do_save():
        brand = brand_var.get().strip()
        if not brand:
            messagebox.showerror("Missing Brand", "Brand is required.", parent=dialog)
            return
        try:
            barcode = barcode_var.get().strip() or None
            supplier_id = supplier_name_to_id.get(vendor_var.get().strip())
            size = size_var.get().strip() or None
            item_type = type_var.get().strip() or None
            description = description_var.get().strip() or None
            case_qty = _parse_int_or_none(case_qty_var.get())
            vendor_item = vendor_item_var.get().strip() or None
            item_notes = notes_text.get("1.0", tk.END).strip() or None
            par_level = _parse_int_or_zero(par_level_var.get())
            reorder_pt = _parse_int_or_zero(reorder_pt_var.get())
            on_order = _parse_int_or_zero(on_order_var.get())
            order_lot = order_lot_var.get()
            last_order_date = _parse_date_or_none(last_order_var.get())
            last_receive_date = _parse_date_or_none(last_receive_var.get())
            deposit_sale_enabled = deposit_sale_enabled_var.get()
            deposit_sale_amount = _parse_float_or_zero(deposit_sale_amount_var.get())
            deposit_return_enabled = deposit_return_enabled_var.get()
            deposit_return_amount = _parse_float_or_zero(deposit_return_amount_var.get())
            sales_tax = sales_tax_var.get()
            discount_ok = discount_ok_var.get()
            cost = _parse_float_or_zero(unit_cost_var.get())
            case_cost = _parse_float_or_zero(case_cost_var.get())
            price = _parse_float_or_zero(price_var.get())
            case_price = _parse_float_or_zero(case_price_var.get())
            twofer_price = _parse_float_or_none(twofer_price_var.get())
            threefer_price = _parse_float_or_none(threefer_price_var.get())
            disc_pool = disc_pool_var.get().strip() or None
            on_hand = _parse_int_or_zero(on_hand_var.get())
        except ValueError as e:
            messagebox.showerror("Invalid Value", f"Please check numeric/date fields: {e}", parent=dialog)
            return

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                if state['item_id'] is None:
                    cur.execute("""
                        INSERT INTO items (
                            barcode, supplier_id, brand, size, price, cost, type,
                            description, case_qty, vendor_item, item_notes,
                            par_level, reorder_pt, on_order, order_lot, last_order_date, last_receive_date,
                            deposit_sale_enabled, deposit_sale_amount, deposit_return_enabled, deposit_return_amount,
                            sales_tax, discount_ok, case_cost, case_price, twofer_price, threefer_price, disc_pool
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s
                        ) RETURNING item_id
                    """, (
                        barcode, supplier_id, brand, size, price, cost, item_type,
                        description, case_qty, vendor_item, item_notes,
                        par_level, reorder_pt, on_order, order_lot, last_order_date, last_receive_date,
                        deposit_sale_enabled, deposit_sale_amount, deposit_return_enabled, deposit_return_amount,
                        sales_tax, discount_ok, case_cost, case_price, twofer_price, threefer_price, disc_pool,
                    ))
                    new_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO inventory (item_id, barcode, quantity) VALUES (%s, %s, %s)",
                        (new_id, barcode, on_hand)
                    )
                    state['item_id'] = new_id
                    state['mode'] = 'edit'
                else:
                    cur.execute("SELECT cost, case_cost FROM items WHERE item_id = %s", (state['item_id'],))
                    prev_cost, prev_case_cost = cur.fetchone()
                    cur.execute("""
                        UPDATE items SET
                            barcode = %s, supplier_id = %s, brand = %s, size = %s, price = %s, cost = %s, type = %s,
                            description = %s, case_qty = %s, vendor_item = %s, item_notes = %s,
                            par_level = %s, reorder_pt = %s, on_order = %s, order_lot = %s,
                            last_order_date = %s, last_receive_date = %s,
                            deposit_sale_enabled = %s, deposit_sale_amount = %s,
                            deposit_return_enabled = %s, deposit_return_amount = %s,
                            sales_tax = %s, discount_ok = %s,
                            last_cost = %s, case_cost = %s, last_case_cost = %s,
                            case_price = %s, twofer_price = %s, threefer_price = %s, disc_pool = %s
                        WHERE item_id = %s
                    """, (
                        barcode, supplier_id, brand, size, price, cost, item_type,
                        description, case_qty, vendor_item, item_notes,
                        par_level, reorder_pt, on_order, order_lot,
                        last_order_date, last_receive_date,
                        deposit_sale_enabled, deposit_sale_amount,
                        deposit_return_enabled, deposit_return_amount,
                        sales_tax, discount_ok,
                        prev_cost, case_cost, prev_case_cost,
                        case_price, twofer_price, threefer_price, disc_pool,
                        state['item_id'],
                    ))
                    cur.execute("SELECT inv_id FROM inventory WHERE item_id = %s", (state['item_id'],))
                    if cur.fetchone():
                        cur.execute("UPDATE inventory SET quantity = %s, barcode = %s WHERE item_id = %s",
                                    (on_hand, barcode, state['item_id']))
                    else:
                        cur.execute("INSERT INTO inventory (item_id, barcode, quantity) VALUES (%s, %s, %s)",
                                    (state['item_id'], barcode, on_hand))
                conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save item: {str(e)}", parent=dialog)
            return

        flash_status("Saved ✓")
        if on_saved:
            on_saved()
        load_item(state['item_id'])

    def do_close():
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=Theme.BG_DARK)
    btn_frame.pack(fill="x", padx=15, pady=(0, 15))
    save_btn = tk.Button(btn_frame, text="Save", command=do_save, **Theme.primary_button_style(), width=14)
    save_btn.pack(side="left", padx=(0, 10))
    close_btn = tk.Button(btn_frame, text="Close", command=do_close, **Theme.button_style(), width=14)
    close_btn.pack(side="left")
    bind_hover_effect(close_btn)

    dialog.grab_set()
    load_item(item_id)


def open_inventory_window():
    win = tk.Toplevel()
    win.title("Inventory Management")
    win.geometry("1500x750")
    win.config(**Theme.window_style())

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

    # Search + barcode row
    search_frame = tk.Frame(main_container, **Theme.frame_style())
    search_frame.pack(pady=(0, 15), fill="x")

    search_inner = tk.Frame(search_frame, bg=Theme.BG_FRAME)
    search_inner.pack(padx=20, pady=15, fill="x")

    tk.Label(
        search_inner,
        text="Search:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(side="left", padx=(0, 10))

    search_entry = tk.Entry(search_inner, **Theme.entry_style(), width=30)
    search_entry.pack(side="left", padx=5, ipady=6)

    def search_items():
        load_inventory(search_entry.get().strip())

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

    tk.Label(
        search_inner,
        text="Scan Barcode:",
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 11, 'bold')
    ).pack(side="left", padx=(30, 10))

    inv_barcode_entry = tk.Entry(search_inner, **Theme.entry_style(), width=20)
    inv_barcode_entry.pack(side="left", padx=5, ipady=6)

    def on_inventory_barcode_scan(event=None):
        barcode = inv_barcode_entry.get().strip()
        if not barcode:
            return
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT item_id FROM items WHERE barcode = %s", (barcode,))
                row = cur.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Barcode lookup failed: {str(e)}")
            inv_barcode_entry.focus_set()
            return
        inv_barcode_entry.delete(0, tk.END)
        inv_barcode_entry.focus_set()
        if row:
            open_item_dialog(mode="edit", item_id=row[0])
        else:
            if messagebox.askyesno("Not Found", f"No item found for barcode {barcode}. Create a new item with this barcode?"):
                open_item_dialog(mode="new", prefill_barcode=barcode)

    inv_barcode_entry.bind('<Return>', on_inventory_barcode_scan)

    # Treeview Frame
    tree_frame = tk.Frame(main_container, **Theme.frame_style())
    tree_frame.pack(fill="both", expand=True, pady=(0, 15))

    # Scrollbars
    vsb = ttk.Scrollbar(tree_frame, orient="vertical")
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

    # Treeview
    columns = ("Item ID", "Barcode", "Brand", "Description", "Size", "Type", "Price", "Cost", "Quantity", "Vendor")
    tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set
    )

    vsb.config(command=tree.yview)
    hsb.config(command=tree.xview)

    for col in columns:
        tree.heading(col, text=col)

    tree.column("Item ID", width=70)
    tree.column("Barcode", width=120)
    tree.column("Brand", width=220)
    tree.column("Description", width=180)
    tree.column("Size", width=80)
    tree.column("Type", width=100)
    tree.column("Price", width=80)
    tree.column("Cost", width=80)
    tree.column("Quantity", width=80)
    tree.column("Vendor", width=160)

    tree.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
    vsb.grid(row=0, column=1, sticky="ns", pady=15)
    hsb.grid(row=1, column=0, sticky="ew", padx=15)

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    loaded_item_ids = []

    # Load inventory data
    def load_inventory(search_term=""):
        for item in tree.get_children():
            tree.delete(item)
        loaded_item_ids.clear()

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                base_query = """
                    SELECT i.item_id, i.barcode, i.brand, i.description, i.size, i.type,
                           i.price, i.cost, inv.quantity, s.company_name
                    FROM items i
                    LEFT JOIN inventory inv ON i.item_id = inv.item_id
                    LEFT JOIN suppliers s ON i.supplier_id = s.supplier_id
                """
                if search_term:
                    query = base_query + """
                        WHERE
                            LOWER(i.brand) LIKE LOWER(%s) OR
                            i.barcode LIKE %s OR
                            LOWER(i.type) LIKE LOWER(%s)
                        ORDER BY i.item_id
                    """
                    search_pattern = f"%{search_term}%"
                    cur.execute(query, (search_pattern, search_pattern, search_pattern))
                else:
                    cur.execute(base_query + " ORDER BY i.item_id")

                rows = cur.fetchall()
                for row in rows:
                    loaded_item_ids.append(row[0])
                    tree.insert("", "end", values=(
                        row[0], row[1] or "", row[2] or "", row[3] or "", row[4] or "",
                        row[5] or "", f"{row[6]:.2f}" if row[6] else "0.00",
                        f"{row[7]:.2f}" if row[7] else "0.00",
                        row[8] if row[8] is not None else 0, row[9] or "N/A"
                    ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory: {str(e)}")

    def get_selected_item_id():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an item first.")
            return None
        return tree.item(selected[0])['values'][0]

    def open_item_dialog(mode, item_id=None, prefill_barcode=None):
        _open_item_detail_dialog(
            win, mode, item_id=item_id, prefill_barcode=prefill_barcode,
            item_list=list(loaded_item_ids),
            on_saved=lambda: load_inventory(search_entry.get().strip())
        )

    def on_row_double_click(event=None):
        item_id = get_selected_item_id()
        if item_id is not None:
            open_item_dialog(mode="edit", item_id=item_id)

    tree.bind('<Double-1>', on_row_double_click)

    # Action buttons frame
    action_frame = tk.Frame(main_container, **Theme.frame_style())
    action_frame.pack(pady=10)

    action_inner = tk.Frame(action_frame, bg=Theme.BG_FRAME)
    action_inner.pack(padx=20, pady=15)

    def make_toolbar_btn(text, command):
        b = tk.Button(action_inner, text=text, command=command, **Theme.button_style(), width=14)
        b.pack(side="left", padx=6)
        bind_hover_effect(b)
        return b

    make_toolbar_btn("New", lambda: open_item_dialog(mode="new"))
    make_toolbar_btn("Edit", lambda: (lambda iid: open_item_dialog(mode="edit", item_id=iid) if iid is not None else None)(get_selected_item_id()))

    def delete_item():
        item_id = get_selected_item_id()
        if item_id is None:
            return
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM sale_items WHERE item_id = %s", (item_id,))
                sold_count = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check sale history: {str(e)}")
            return

        if sold_count > 0:
            messagebox.showwarning(
                "Cannot Delete",
                "This item has sale history and can't be deleted (it would break past sales records). "
                "Set its quantity to 0 instead if it's discontinued."
            )
            return

        if not messagebox.askyesno("Confirm Delete", "Delete this item permanently?"):
            return

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM inventory WHERE item_id = %s", (item_id,))
                cur.execute("DELETE FROM items WHERE item_id = %s", (item_id,))
                conn.commit()
            conn.close()
            messagebox.showinfo("Deleted", "Item deleted.")
            load_inventory(search_entry.get().strip())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete item: {str(e)}")

    make_toolbar_btn("Delete", delete_item)

    def show_low_stock():
        for item in tree.get_children():
            tree.delete(item)
        loaded_item_ids.clear()

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.item_id, i.barcode, i.brand, i.description, i.size, i.type,
                           i.price, i.cost, inv.quantity, s.company_name
                    FROM items i
                    LEFT JOIN inventory inv ON i.item_id = inv.item_id
                    LEFT JOIN suppliers s ON i.supplier_id = s.supplier_id
                    WHERE inv.quantity <= COALESCE(NULLIF(i.reorder_pt, 0), 5)
                    ORDER BY inv.quantity
                """)
                rows = cur.fetchall()
                for row in rows:
                    loaded_item_ids.append(row[0])
                    tree.insert("", "end", values=(
                        row[0], row[1] or "", row[2] or "", row[3] or "", row[4] or "",
                        row[5] or "", f"{row[6]:.2f}" if row[6] else "0.00",
                        f"{row[7]:.2f}" if row[7] else "0.00",
                        row[8] if row[8] is not None else 0, row[9] or "N/A"
                    ))
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load low stock items: {str(e)}")

    make_toolbar_btn("Show Low Stock", show_low_stock)

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
    back_btn.pack(side="left", padx=6)

    # Load initial data
    load_inventory()

    # Bind Enter key to search
    search_entry.bind('<Return>', lambda e: search_items())
