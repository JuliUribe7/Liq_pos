# inventory_gui.py
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from db import get_conn
from theme import Theme
from ui_settings import scale_geometry, scale_dim, position_main_window, get_ui_scale


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


_DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%m/%d/%y", "%m-%d-%y",
    "%b %d %Y", "%b %d, %Y", "%B %d %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y",
]


def _parse_date_or_none(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: \"{value}\" (try e.g. 2026-08-24 or 08/24/2026)")


def _fmt_date(value):
    return value.strftime("%Y-%m-%d") if value else ""


def _make_scrollable(parent, bg):
    """Returns (inner_frame, canvas). Caller is responsible for wiring up
    mousewheel scrolling centrally (see _open_item_detail_dialog) — binding
    it here per-canvas via bind_all on Enter/Leave is unreliable across
    ttk.Notebook tab switches and dialog teardown, since Leave doesn't
    reliably fire when a tab is hidden or the dialog is closed."""
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    inner = ctk.CTkFrame(canvas, fg_color=bg, corner_radius=0)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner_configure)

    def _on_canvas_configure(event):
        canvas.itemconfig(window_id, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    return inner, canvas


def _section_label(parent, text, scale=1.0):
    ctk.CTkLabel(
        parent, text=text, fg_color="transparent", text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(12), "bold")
    ).pack(anchor="w", pady=(15, 5), padx=15)


def _field_row(parent, label_text, widget_factory, scale=1.0):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=15, pady=4)
    ctk.CTkLabel(
        row, text=label_text, fg_color="transparent", text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(10)), width=scale_dim(140), anchor="w"
    ).pack(side="left")
    widget = widget_factory(row)
    widget.pack(side="left", fill="x", expand=True)
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
                   sales_tax, discount_ok, avg_cost, case_cost, case_price,
                   disc_pool
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
        'sales_tax', 'discount_ok', 'avg_cost', 'case_cost', 'case_price',
        'disc_pool',
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
    scale = get_ui_scale()
    item_list = item_list or []
    suppliers = _fetch_suppliers()
    # Keys are trimmed so vendor names with stray leading/trailing whitespace
    # (real data quality issue in the legacy import) still match on lookup.
    # Duplicate names (e.g. multiple "EMPIRE MERCHANTS" rows) are inherently
    # ambiguous by name alone — see supplier_id tracking below, which avoids
    # ever re-resolving by name unless the user actually changes the field.
    supplier_name_to_id = {name.strip(): sid for sid, name in suppliers}

    dialog = ctk.CTkToplevel(parent_win)
    dialog.title("Item Details")
    dialog.geometry(scale_geometry(780, 680))
    dialog.configure(**Theme.ctk_window_style())
    dialog.transient(parent_win)

    # state['supplier_id']/['vendor_loaded_name'] track the vendor as actually
    # loaded from the DB, independent of the combobox's displayed text, so
    # re-saving without touching Vendor never risks losing/reassigning it.
    state = {'item_id': item_id, 'mode': mode, 'supplier_id': None, 'vendor_loaded_name': ""}

    # --- Top nav/status bar ---
    nav_frame = ctk.CTkFrame(dialog, fg_color=Theme.BG_DARK, corner_radius=0)
    nav_frame.pack(fill="x", padx=15, pady=(15, 5))

    status_label = ctk.CTkLabel(nav_frame, text="", fg_color="transparent", text_color=Theme.TEXT_SUCCESS,
                                 font=(Theme.FONT_FAMILY, scale_dim(10), "bold"))
    status_label.pack(side="right")

    def flash_status(text, ok=True):
        status_label.configure(text=text, text_color=Theme.TEXT_SUCCESS if ok else Theme.TEXT_ERROR)
        dialog.after(2500, lambda: status_label.configure(text="") if dialog.winfo_exists() else None)

    nav_btns_frame = ctk.CTkFrame(nav_frame, fg_color=Theme.BG_DARK, corner_radius=0)
    nav_btns_frame.pack(side="left")

    # --- Notebook — kept as ttk (no CTk equivalent low-risk enough for this
    # dialog's tab-switching + scroll-canvas interplay); styled to blend in. ---
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

    # Mousewheel scrolling is wired once, centrally, for the whole dialog
    # (see below the tabs) rather than per-canvas — this is what keeps it
    # working reliably across tab switches and dialog close/reopen.
    tab_canvases = {}

    # ================= Details tab =================
    details_inner, details_canvas = _make_scrollable(details_tab, Theme.BG_FRAME)
    tab_canvases[details_tab] = details_canvas

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

    _section_label(details_inner, "Product Info", scale=scale)
    _field_row(details_inner, "Brand", lambda p: ctk.CTkEntry(p, textvariable=brand_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Description", lambda p: ctk.CTkEntry(p, textvariable=description_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Type", lambda p: ctk.CTkEntry(p, textvariable=type_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Size", lambda p: ctk.CTkEntry(p, textvariable=size_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Case Qty", lambda p: ctk.CTkEntry(p, textvariable=case_qty_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Barcode", lambda p: ctk.CTkEntry(p, textvariable=barcode_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "On Hand", lambda p: ctk.CTkEntry(p, textvariable=on_hand_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)

    _section_label(details_inner, "Vendor & Purchasing", scale=scale)
    all_vendor_names = [name for _, name in suppliers]
    vendor_combo = _field_row(details_inner, "Vendor", lambda p: ttk.Combobox(
        p, textvariable=vendor_var, values=all_vendor_names, state="normal"), scale=scale)

    def on_vendor_selected(event=None):
        # Resolve by matching the selected text against `suppliers` (not by
        # positional index — the dropdown's values list is filtered live as
        # you type, so its index no longer lines up with `suppliers`' order).
        selected_name = vendor_var.get().strip()
        for sid, name in suppliers:
            if name.strip() == selected_name:
                state['supplier_id'] = sid
                state['vendor_loaded_name'] = name.strip()
                break
        vendor_combo['values'] = all_vendor_names

    vendor_combo.bind("<<ComboboxSelected>>", on_vendor_selected)

    def on_vendor_keyrelease(event=None):
        # Live filter: narrows the dropdown to vendors whose name contains
        # what's typed so far (case-insensitive), so you can see and pick the
        # correct spelling instead of hand-typing it blind.
        if event is not None and event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
        typed = vendor_var.get().strip().lower()
        if not typed:
            vendor_combo['values'] = all_vendor_names
            return
        matches = [name for name in all_vendor_names if typed in name.strip().lower()]
        vendor_combo['values'] = matches or all_vendor_names
        if matches:
            vendor_combo.event_generate('<Down>')

    vendor_combo.bind("<KeyRelease>", on_vendor_keyrelease)
    _field_row(details_inner, "Vendor Item", lambda p: ctk.CTkEntry(p, textvariable=vendor_item_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Last Order", lambda p: ctk.CTkEntry(p, textvariable=last_order_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Last Receive", lambda p: ctk.CTkEntry(p, textvariable=last_receive_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)

    _section_label(details_inner, "Stock & Reorder", scale=scale)
    _field_row(details_inner, "Par Level", lambda p: ctk.CTkEntry(p, textvariable=par_level_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "Reorder Point", lambda p: ctk.CTkEntry(p, textvariable=reorder_pt_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(details_inner, "On Order", lambda p: ctk.CTkEntry(p, textvariable=on_order_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)

    order_lot_row = ctk.CTkFrame(details_inner, fg_color="transparent")
    order_lot_row.pack(fill="x", padx=15, pady=4)
    ctk.CTkLabel(order_lot_row, text="Order Lot", fg_color="transparent", text_color=Theme.TEXT_PRIMARY,
                 font=(Theme.FONT_FAMILY, scale_dim(10)), width=scale_dim(140), anchor="w").pack(side="left")
    for label, value in [("Case", "case"), ("Unit", "unit")]:
        ctk.CTkRadioButton(order_lot_row, text=label, variable=order_lot_var, value=value,
                            fg_color=Theme.ACCENT_GOLD, hover_color=Theme.ACCENT_GOLD_DARK,
                            text_color=Theme.TEXT_PRIMARY, font=(Theme.FONT_FAMILY, scale_dim(10))).pack(side="left", padx=5)

    _section_label(details_inner, "Deposits & Tax", scale=scale)

    deposit_sale_row = ctk.CTkFrame(details_inner, fg_color="transparent")
    deposit_sale_row.pack(fill="x", padx=15, pady=4)
    ctk.CTkCheckBox(deposit_sale_row, text="Deposit on Sale", variable=deposit_sale_enabled_var,
                     **Theme.ctk_checkbox_style(scale=scale)).pack(side="left")
    ctk.CTkEntry(deposit_sale_row, textvariable=deposit_sale_amount_var, width=scale_dim(100), **Theme.ctk_entry_style(scale=scale)).pack(side="left", padx=10)

    deposit_return_row = ctk.CTkFrame(details_inner, fg_color="transparent")
    deposit_return_row.pack(fill="x", padx=15, pady=4)
    ctk.CTkCheckBox(deposit_return_row, text="Deposit on Return", variable=deposit_return_enabled_var,
                     **Theme.ctk_checkbox_style(scale=scale)).pack(side="left")
    ctk.CTkEntry(deposit_return_row, textvariable=deposit_return_amount_var, width=scale_dim(100), **Theme.ctk_entry_style(scale=scale)).pack(side="left", padx=10)

    tax_discount_row = ctk.CTkFrame(details_inner, fg_color="transparent")
    tax_discount_row.pack(fill="x", padx=15, pady=4)
    ctk.CTkCheckBox(tax_discount_row, text="Sales Tax", variable=sales_tax_var,
                    **Theme.ctk_checkbox_style(scale=scale)).pack(side="left", padx=(0, 20))
    ctk.CTkCheckBox(tax_discount_row, text="Discount OK", variable=discount_ok_var,
                    **Theme.ctk_checkbox_style(scale=scale)).pack(side="left")

    _section_label(details_inner, "Notes", scale=scale)
    notes_text = tk.Text(details_inner, height=4, bg=Theme.BG_INPUT, fg=Theme.TEXT_PRIMARY,
                          font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL), relief="flat",
                          insertbackground=Theme.TEXT_PRIMARY, highlightthickness=2,
                          highlightbackground=Theme.BORDER_DEFAULT, highlightcolor=Theme.BORDER_FOCUS)
    notes_text.pack(fill="x", padx=15, pady=(4, 10))

    stats_label = ctk.CTkLabel(details_inner, text="", fg_color="transparent", text_color=Theme.TEXT_SECONDARY,
                                font=(Theme.FONT_FAMILY, scale_dim(10)), justify="left", anchor="w")
    stats_label.pack(fill="x", padx=15, pady=(0, 15))

    # ================= Costs & Pricing tab =================
    costs_inner, costs_canvas = _make_scrollable(costs_tab, Theme.BG_FRAME)
    tab_canvases[costs_tab] = costs_canvas

    latest_cost_var = tk.StringVar(value="0.00")
    case_cost_var = tk.StringVar(value="0.00")
    avg_cost_var = tk.StringVar(value="")
    qty_received_var = tk.StringVar(value="0")
    markup_var = tk.StringVar(value="0.00%")
    margin_var = tk.StringVar(value="0.00%")
    price_var = tk.StringVar(value="0.00")
    case_price_var = tk.StringVar(value="0.00")
    disc_pool_var = tk.StringVar(value="")

    _section_label(costs_inner, "Costs", scale=scale)
    _field_row(costs_inner, "Latest Cost", lambda p: ctk.CTkEntry(p, textvariable=latest_cost_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Case Cost", lambda p: ctk.CTkEntry(p, textvariable=case_cost_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Avg Cost", lambda p: ctk.CTkEntry(p, textvariable=avg_cost_var, state="readonly", **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Qty Received", lambda p: ctk.CTkEntry(p, textvariable=qty_received_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Markup %", lambda p: ctk.CTkEntry(p, textvariable=markup_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Margin %", lambda p: ctk.CTkEntry(p, textvariable=margin_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)

    ctk.CTkLabel(
        costs_inner,
        text="Qty Received: how many units you're adding to On Hand right now at the Latest Cost above. "
             "Leave at 0 if you're not receiving stock this edit (e.g. just correcting On Hand). "
             "Avg Cost recalculates from this using the weighted-average method.",
        fg_color="transparent", text_color=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, scale_dim(9)),
        wraplength=scale_dim(500), justify="left", anchor="w"
    ).pack(fill="x", padx=15, pady=(0, 10))

    price_warning_label = ctk.CTkLabel(
        costs_inner, text="", fg_color="transparent", text_color=Theme.TEXT_WARNING,
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_SMALL), "bold"),
        wraplength=scale_dim(500), justify="left", anchor="w"
    )
    price_warning_label.pack(fill="x", padx=15, pady=(0, 5))

    _section_label(costs_inner, "Prices", scale=scale)
    _field_row(costs_inner, "Standard Price", lambda p: ctk.CTkEntry(p, textvariable=price_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Case Price", lambda p: ctk.CTkEntry(p, textvariable=case_price_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)
    _field_row(costs_inner, "Discount Pool", lambda p: ctk.CTkEntry(p, textvariable=disc_pool_var, **Theme.ctk_entry_style(scale=scale)), scale=scale)

    # Price, Markup %, and Margin % are three mutually-derivable views of the
    # same relationship (given Cost). Editing any one recalculates the other
    # two. pricing_lock prevents the resulting var.set() calls from re-firing
    # each other's trace handlers (which would otherwise infinite-loop).
    pricing_lock = {'active': False}

    def _current_cost():
        try:
            latest_cost = float(latest_cost_var.get() or 0)
        except ValueError:
            latest_cost = 0.0
        try:
            avg_cost = float(avg_cost_var.get() or 0)
        except ValueError:
            avg_cost = 0.0
        # Falls back to Latest Cost for items that haven't gone through a
        # weighted-average recalculation yet (avg_cost never set).
        if avg_cost > 0:
            return avg_cost, "avg cost"
        return latest_cost, "cost"

    def _refresh_warning(cost, cost_label, price):
        if not price_var.get().strip() or price <= 0:
            price_warning_label.configure(text="⚠ Price is blank — set a selling price before saving.")
        elif cost > 0 and price < cost:
            price_warning_label.configure(
                text=f"⚠ Price (${price:.2f}) is below {cost_label} (${cost:.2f}) — this item would sell at a loss."
            )
        else:
            price_warning_label.configure(text="")

    def _parse_pct(var):
        text = var.get().strip().rstrip('%').strip()
        return float(text) if text else None

    def on_price_changed(*_):
        if pricing_lock['active']:
            return
        pricing_lock['active'] = True
        try:
            cost, cost_label = _current_cost()
            try:
                price = float(price_var.get() or 0)
            except ValueError:
                price = 0.0
            markup_var.set(f"{((price - cost) / cost * 100):.2f}%" if cost > 0 else "--")
            margin_var.set(f"{((price - cost) / price * 100):.2f}%" if price > 0 else "--")
            _refresh_warning(cost, cost_label, price)
        finally:
            pricing_lock['active'] = False

    def on_markup_changed(*_):
        if pricing_lock['active']:
            return
        pricing_lock['active'] = True
        try:
            cost, cost_label = _current_cost()
            try:
                markup_pct = _parse_pct(markup_var)
            except ValueError:
                return
            if markup_pct is None or cost <= 0:
                return
            new_price = cost * (1 + markup_pct / 100)
            price_var.set(f"{new_price:.2f}")
            margin_var.set(f"{((new_price - cost) / new_price * 100):.2f}%" if new_price > 0 else "--")
            _refresh_warning(cost, cost_label, new_price)
        finally:
            pricing_lock['active'] = False

    def on_margin_changed(*_):
        if pricing_lock['active']:
            return
        pricing_lock['active'] = True
        try:
            cost, cost_label = _current_cost()
            try:
                margin_pct = _parse_pct(margin_var)
            except ValueError:
                return
            if margin_pct is None or cost <= 0 or margin_pct >= 100:
                return
            new_price = cost / (1 - margin_pct / 100)
            price_var.set(f"{new_price:.2f}")
            markup_var.set(f"{((new_price - cost) / cost * 100):.2f}%" if cost > 0 else "--")
            _refresh_warning(cost, cost_label, new_price)
        finally:
            pricing_lock['active'] = False

    latest_cost_var.trace_add("write", on_price_changed)
    avg_cost_var.trace_add("write", on_price_changed)
    price_var.trace_add("write", on_price_changed)
    markup_var.trace_add("write", on_markup_changed)
    margin_var.trace_add("write", on_margin_changed)

    # ================= Load / populate =================
    def populate_fields(data):
        stats = _fetch_computed_stats(data['item_id'] if data else None)

        brand_var.set(data['brand'] if data else "")
        description_var.set((data.get('description') if data else "") or "")
        type_var.set((data.get('type') if data else "") or "")
        size_var.set((data.get('size') if data else "") or "")
        case_qty_var.set(str(data.get('case_qty')) if data and data.get('case_qty') is not None else "")
        vendor_var.set("")
        state['supplier_id'] = None
        state['vendor_loaded_name'] = ""
        if data and data.get('supplier_id'):
            for sid, name in suppliers:
                if sid == data['supplier_id']:
                    vendor_var.set(name)
                    state['supplier_id'] = sid
                    state['vendor_loaded_name'] = name.strip()
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
        stats_label.configure(text=f"Last Sale: {last_sale_text}    MTD Sold: {stats['mtd']}    YTD Sold: {stats['ytd']}")

        latest_cost_var.set(f"{data.get('cost') or 0:.2f}" if data else "0.00")
        case_cost_var.set(f"{data.get('case_cost') or 0:.2f}" if data else "0.00")
        avg_cost_var.set(f"{data['avg_cost']:.2f}" if data and data.get('avg_cost') is not None else "")
        qty_received_var.set("0")
        price_var.set(f"{data.get('price') or 0:.2f}" if data else "0.00")
        case_price_var.set(f"{data.get('case_price') or 0:.2f}" if data else "0.00")
        disc_pool_var.set((data.get('disc_pool') if data else "") or "")
        on_price_changed()

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

    nav_first_btn = ctk.CTkButton(nav_btns_frame, text="|< First", command=go_first, **Theme.ctk_button_style(scale=scale), width=scale_dim(90))
    nav_prev_btn = ctk.CTkButton(nav_btns_frame, text="< Prev", command=go_prev, **Theme.ctk_button_style(scale=scale), width=scale_dim(90))
    nav_next_btn = ctk.CTkButton(nav_btns_frame, text="Next >", command=go_next, **Theme.ctk_button_style(scale=scale), width=scale_dim(90))
    nav_last_btn = ctk.CTkButton(nav_btns_frame, text="Last >|", command=go_last, **Theme.ctk_button_style(scale=scale), width=scale_dim(90))
    for b in (nav_first_btn, nav_prev_btn, nav_next_btn, nav_last_btn):
        b.pack(side="left", padx=3)

    def update_nav_state():
        nav_enabled = state['mode'] == 'edit' and bool(item_list)
        widget_state = "normal" if nav_enabled else "disabled"
        for b in (nav_first_btn, nav_prev_btn, nav_next_btn, nav_last_btn):
            b.configure(state=widget_state)

    # ================= Save / Close =================
    def do_save():
        brand = brand_var.get().strip()
        if not brand:
            messagebox.showerror("Missing Brand", "Brand is required.", parent=dialog)
            return
        vendor_text = vendor_var.get().strip()
        if not vendor_text:
            supplier_id = None
        elif vendor_text == state['vendor_loaded_name']:
            # Field wasn't actually changed from what was loaded — keep the
            # originally-loaded supplier_id rather than re-resolving by name
            # (name text alone is ambiguous: several suppliers share names
            # like "EMPIRE MERCHANTS", and some have stray whitespace).
            supplier_id = state['supplier_id']
        elif vendor_text in supplier_name_to_id:
            supplier_id = supplier_name_to_id[vendor_text]
        else:
            messagebox.showerror(
                "Unknown Vendor",
                f"\"{vendor_text}\" doesn't match any vendor. Pick one from the dropdown.",
                parent=dialog
            )
            return

        try:
            barcode = barcode_var.get().strip() or None
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
            cost = _parse_float_or_zero(latest_cost_var.get())
            case_cost = _parse_float_or_zero(case_cost_var.get())
            price = _parse_float_or_zero(price_var.get())
            case_price = _parse_float_or_zero(case_price_var.get())
            disc_pool = disc_pool_var.get().strip() or None
            on_hand = _parse_int_or_zero(on_hand_var.get())
            qty_received = _parse_int_or_zero(qty_received_var.get())
        except ValueError as e:
            messagebox.showerror("Invalid Value", f"Please check numeric/date fields: {e}", parent=dialog)
            return

        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                if state['item_id'] is None:
                    # First-ever cost basis for a brand-new item is just what
                    # was typed as Latest Cost (no prior purchases to average with).
                    new_avg_cost = cost if cost > 0 else None
                    cur.execute("""
                        INSERT INTO items (
                            barcode, supplier_id, brand, size, price, cost, type,
                            description, case_qty, vendor_item, item_notes,
                            par_level, reorder_pt, on_order, order_lot, last_order_date, last_receive_date,
                            deposit_sale_enabled, deposit_sale_amount, deposit_return_enabled, deposit_return_amount,
                            sales_tax, discount_ok, avg_cost, case_cost, case_price, disc_pool
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        ) RETURNING item_id
                    """, (
                        barcode, supplier_id, brand, size, price, cost, item_type,
                        description, case_qty, vendor_item, item_notes,
                        par_level, reorder_pt, on_order, order_lot, last_order_date, last_receive_date,
                        deposit_sale_enabled, deposit_sale_amount, deposit_return_enabled, deposit_return_amount,
                        sales_tax, discount_ok, new_avg_cost, case_cost, case_price, disc_pool,
                    ))
                    new_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO inventory (item_id, barcode, quantity) VALUES (%s, %s, %s)",
                        (new_id, barcode, on_hand)
                    )
                    state['item_id'] = new_id
                    state['mode'] = 'edit'
                else:
                    cur.execute("SELECT avg_cost FROM items WHERE item_id = %s", (state['item_id'],))
                    (prev_avg_cost,) = cur.fetchone()
                    cur.execute("SELECT quantity FROM inventory WHERE item_id = %s", (state['item_id'],))
                    inv_row = cur.fetchone()
                    prev_on_hand = inv_row[0] if inv_row else 0

                    # Weighted-average cost recalculation: only moves when you
                    # actually record a receipt (Qty Received > 0) — plain On
                    # Hand corrections (recounts) leave Avg Cost untouched.
                    if qty_received > 0:
                        if prev_on_hand > 0 and prev_avg_cost and prev_avg_cost > 0:
                            new_avg_cost = (
                                (float(prev_avg_cost) * prev_on_hand) + (cost * qty_received)
                            ) / (prev_on_hand + qty_received)
                        else:
                            new_avg_cost = cost
                    else:
                        new_avg_cost = float(prev_avg_cost) if prev_avg_cost is not None else None

                    cur.execute("""
                        UPDATE items SET
                            barcode = %s, supplier_id = %s, brand = %s, size = %s, price = %s, cost = %s, type = %s,
                            description = %s, case_qty = %s, vendor_item = %s, item_notes = %s,
                            par_level = %s, reorder_pt = %s, on_order = %s, order_lot = %s,
                            last_order_date = %s, last_receive_date = %s,
                            deposit_sale_enabled = %s, deposit_sale_amount = %s,
                            deposit_return_enabled = %s, deposit_return_amount = %s,
                            sales_tax = %s, discount_ok = %s,
                            avg_cost = %s, case_cost = %s,
                            case_price = %s, disc_pool = %s
                        WHERE item_id = %s
                    """, (
                        barcode, supplier_id, brand, size, price, cost, item_type,
                        description, case_qty, vendor_item, item_notes,
                        par_level, reorder_pt, on_order, order_lot,
                        last_order_date, last_receive_date,
                        deposit_sale_enabled, deposit_sale_amount,
                        deposit_return_enabled, deposit_return_amount,
                        sales_tax, discount_ok,
                        new_avg_cost, case_cost,
                        case_price, disc_pool,
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
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            messagebox.showerror("Error", f"Failed to save item: {str(e)}", parent=dialog)
            return

        flash_status("Saved ✓")
        if on_saved:
            on_saved()
        load_item(state['item_id'])

    def do_close():
        dialog.destroy()

    btn_frame = ctk.CTkFrame(dialog, fg_color=Theme.BG_DARK, corner_radius=0)
    btn_frame.pack(fill="x", padx=15, pady=(0, 15))
    save_btn = ctk.CTkButton(btn_frame, text="Save", command=do_save, **Theme.ctk_primary_button_style(scale=scale), width=scale_dim(120))
    save_btn.pack(side="left", padx=(0, 10))
    close_btn = ctk.CTkButton(btn_frame, text="Close", command=do_close, **Theme.ctk_button_style(scale=scale), width=scale_dim(120))
    close_btn.pack(side="left")

    def _dialog_mousewheel(event):
        # bind_all is process-wide, so if another dialog/window also has a
        # wheel handler bound, only act when the event actually belongs to
        # this dialog (otherwise, do nothing rather than scroll the wrong canvas).
        try:
            if event.widget.winfo_toplevel() is not dialog:
                return
            active_tab = notebook.nametowidget(notebook.select())
        except Exception:
            return
        canvas = tab_canvases.get(active_tab)
        if canvas is not None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    dialog.bind_all("<MouseWheel>", _dialog_mousewheel)

    def _cleanup_mousewheel(event=None):
        try:
            dialog.unbind_all("<MouseWheel>")
        except Exception:
            pass
    dialog.bind("<Destroy>", _cleanup_mousewheel)

    dialog.grab_set()
    load_item(item_id)


def open_inventory_window():
    scale = get_ui_scale()
    win = ctk.CTkToplevel()
    win.title("Inventory Management")
    win.geometry(scale_geometry(1500, 750))
    win.configure(**Theme.ctk_window_style())
    win.after(60, lambda: position_main_window(win))

    style = ttk.Style()
    style.theme_use('clam')
    # Smaller than Sales/Reports' Treeview font deliberately: this table has
    # 10 fixed-pixel-width columns (Item ID, Barcode, Brand, etc. — set
    # below via tree.column(width=...), which don't scale with UI_SCALE the
    # way fonts do), so a font sized for a 2-3 column cart table was
    # overflowing these narrower columns and clipping the headers.
    style.configure("Treeview",
                    background=Theme.BG_BUTTON,
                    foreground=Theme.TEXT_PRIMARY,
                    fieldbackground=Theme.BG_BUTTON,
                    borderwidth=0,
                    font=(Theme.FONT_FAMILY, 9),
                    rowheight=scale_dim(24))
    style.configure("Treeview.Heading",
                    background=Theme.BG_FRAME,
                    foreground=Theme.ACCENT_GOLD,
                    relief="flat",
                    font=(Theme.FONT_FAMILY, 9, 'bold'))
    style.map('Treeview', background=[('selected', Theme.ACCENT_GOLD)])

    # Header
    header_frame = ctk.CTkFrame(win, fg_color=Theme.BG_DARK, corner_radius=0)
    header_frame.pack(fill='x', pady=(20, 10))

    ctk.CTkLabel(
        header_frame,
        text="Inventory Management",
        fg_color="transparent",
        text_color=Theme.ACCENT_GOLD,
        font=(Theme.FONT_FAMILY, scale_dim(20), "bold")
    ).pack()

    # Main container
    main_container = ctk.CTkFrame(win, fg_color=Theme.BG_DARK, corner_radius=0)
    main_container.pack(fill='both', expand=True, padx=20, pady=10)

    # Search + barcode row. Padding here (and around the action buttons
    # below) is intentionally tight, not just cosmetic: on a 1366x768
    # screen there isn't enough spare vertical room for both loose padding
    # and full-size buttons, and looser padding was squeezing the New/
    # Edit/Delete/Show Low Stock/Back row shorter than its real size.
    search_frame = ctk.CTkFrame(main_container, **Theme.ctk_frame_style())
    search_frame.pack(pady=(0, 8), fill="x")

    search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
    search_inner.pack(padx=20, pady=8, fill="x")

    ctk.CTkLabel(
        search_inner,
        text="Search:",
        fg_color="transparent",
        text_color=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, scale_dim(11), 'bold')
    ).pack(side="left", padx=(0, 10))

    search_field_var = tk.StringVar(value="All Fields")
    search_field_combo = ttk.Combobox(
        search_inner, textvariable=search_field_var, state="readonly", width=12,
        values=["All Fields", "Barcode", "Brand", "Description", "Size", "Vendor", "Type"]
    )
    search_field_combo.pack(side="left", padx=(0, 10))

    search_entry = ctk.CTkEntry(search_inner, width=scale_dim(300), **Theme.ctk_entry_style(scale=scale))
    search_entry.pack(side="left", padx=5)

    def search_items():
        load_inventory(search_entry.get().strip(), search_field_var.get())

    search_btn = ctk.CTkButton(
        search_inner,
        text="Search",
        command=search_items,
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(100)
    )
    search_btn.pack(side="left", padx=5)

    refresh_btn = ctk.CTkButton(
        search_inner,
        text="Refresh",
        command=lambda: load_inventory(),
        **Theme.ctk_button_style(scale=scale),
        width=scale_dim(100)
    )
    refresh_btn.pack(side="left", padx=5)

    # Treeview Frame
    tree_frame = ctk.CTkFrame(main_container, **Theme.ctk_frame_style())
    tree_frame.pack(fill="both", expand=True, pady=(0, 8))

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

    # Maps the Search field dropdown to the SQL column it searches. Barcode
    # is left un-lowered (it's numeric/alphanumeric, not free text); all
    # others are case- and whitespace-insensitive, same as before — strips
    # all spaces (not just trims ends) from both sides before comparing,
    # since the legacy data has inconsistent spacing (e.g. "1800  TEQUILA").
    SEARCH_FIELD_COLUMNS = {
        "Barcode": "REPLACE(i.barcode, ' ', '') LIKE REPLACE(%s, ' ', '')",
        "Brand": "REPLACE(LOWER(i.brand), ' ', '') LIKE REPLACE(LOWER(%s), ' ', '')",
        "Description": "REPLACE(LOWER(i.description), ' ', '') LIKE REPLACE(LOWER(%s), ' ', '')",
        "Size": "REPLACE(LOWER(i.size), ' ', '') LIKE REPLACE(LOWER(%s), ' ', '')",
        "Vendor": "REPLACE(LOWER(s.company_name), ' ', '') LIKE REPLACE(LOWER(%s), ' ', '')",
        "Type": "REPLACE(LOWER(i.type), ' ', '') LIKE REPLACE(LOWER(%s), ' ', '')",
    }

    # Load inventory data
    def load_inventory(search_term="", search_field="All Fields"):
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
                    if search_field in SEARCH_FIELD_COLUMNS:
                        conditions = [SEARCH_FIELD_COLUMNS[search_field]]
                    else:
                        conditions = list(SEARCH_FIELD_COLUMNS.values())
                    query = base_query + " WHERE " + " OR ".join(conditions) + " ORDER BY i.item_id"
                    search_pattern = f"%{search_term}%"
                    cur.execute(query, tuple([search_pattern] * len(conditions)))
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
            on_saved=lambda: load_inventory(search_entry.get().strip(), search_field_var.get())
        )

    def on_row_double_click(event=None):
        item_id = get_selected_item_id()
        if item_id is not None:
            open_item_dialog(mode="edit", item_id=item_id)

    tree.bind('<Double-1>', on_row_double_click)

    # Action buttons frame. side="bottom" reserves this row's full height
    # first, before tree_frame's expand=True above it claims the rest — on
    # a short screen (e.g. 1366x768) without it, Tk squeezes these buttons
    # shorter than their real size instead of just showing fewer tree rows,
    # which is the far less noticeable place to lose the space.
    action_frame = ctk.CTkFrame(main_container, **Theme.ctk_frame_style())
    action_frame.pack(side="bottom", pady=6)

    action_inner = ctk.CTkFrame(action_frame, fg_color="transparent")
    action_inner.pack(padx=20, pady=8)

    def make_toolbar_btn(text, command):
        b = ctk.CTkButton(action_inner, text=text, command=command, **Theme.ctk_button_style(scale=scale), width=scale_dim(140))
        b.pack(side="left", padx=6)
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

        conn = None
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM inventory WHERE item_id = %s", (item_id,))
                cur.execute("DELETE FROM items WHERE item_id = %s", (item_id,))
                conn.commit()
            conn.close()
            messagebox.showinfo("Deleted", "Item deleted.")
            load_inventory(search_entry.get().strip(), search_field_var.get())
        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
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
    back_btn = ctk.CTkButton(
        action_inner,
        text="← Back",
        command=win.destroy,
        fg_color="#DC3545",
        text_color=Theme.TEXT_PRIMARY,
        hover_color="#C82333",
        font=(Theme.FONT_FAMILY, scale_dim(Theme.FONT_SIZE_NORMAL), "bold"),
        corner_radius=8,
        border_width=0,
        width=scale_dim(120),
    )
    back_btn.pack(side="left", padx=6)

    # Load initial data
    load_inventory()

    # Bind Enter key to search
    search_entry.bind('<Return>', lambda e: search_items())

    return win
