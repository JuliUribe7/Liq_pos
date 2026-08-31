# receipt.py
"""ESC/POS receipt printing for the Epson thermal printer + attached cash
drawer, connected via USB and already installed as a Windows printer — so
we send raw ESC/POS bytes through the Windows print spooler (Win32Raw),
no libusb/Zadig driver needed.
"""
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

STORE_NAME = "Junior's Liquors"
STORE_ADDRESS = "67-19 Fresh Pond Rd, Ridgewood, NY 11385"
STORE_PHONE = "(718)-418-3418"

RECEIPT_WIDTH = 42  # standard for 80mm thermal paper; use 32 for 58mm paper
DRAWER_PIN = 2  # most cash drawers wired to the printer's RJ11 port use pin 2


def _line(left, right, width=RECEIPT_WIDTH):
    """Left-align `left`, right-align `right`, padded to `width`."""
    left = str(left)
    right = str(right)
    space = max(1, width - len(left) - len(right))
    return f"{left}{' ' * space}{right}"


def _build_body_lines(sale_id, cashier, cart_items, totals, payment_method, cash_tendered, change_due):
    """Plain left-aligned body content — sale info, items, totals, payment.
    Shared by print_receipt() and preview_receipt() so there's one source
    of truth for what a receipt actually says, regardless of how it's output.

    Item format is two lines each (name + total on line 1, barcode + qty@price
    on line 2), matching the store's existing LiquorPOS receipt layout.
    """
    lines = []
    date_str = datetime.now().strftime('%#m/%#d/%Y %#I:%M %p')
    lines.append(_line(date_str, f"INV: {sale_id}"))
    lines.append(f"Cashier: {cashier}")
    lines.append(f"Nbr of Items: {totals['total_items']}")
    lines.append("-" * RECEIPT_WIDTH)
    lines.append(_line("Description", "Amount"))

    for item in cart_items:
        name = item['brand']
        if item.get('is_custom'):
            name += " (Custom)"
        qty = item['quantity']
        price = item['price']
        line_total = qty * price
        if len(name) > RECEIPT_WIDTH:
            name = name[:RECEIPT_WIDTH]
        lines.append(_line(name, f"${line_total:.2f}"))
        lines.append(_line(item.get('barcode') or "", f"{qty} @ {price:.2f}"))

    lines.append("-" * RECEIPT_WIDTH)
    lines.append(_line("Sub-Total:", f"${totals['subtotal']:.2f}"))
    if totals['discount_amount'] > 0:
        lines.append(_line("Discount:", f"-${totals['discount_amount']:.2f}"))
    lines.append(_line("Sales Tax:", f"${totals['tax_amount']:.2f}"))
    if totals['deposit_amount'] > 0:
        lines.append(_line("Deposit:", f"${totals['deposit_amount']:.2f}"))
    lines.append(_line("Total:", f"${totals['total']:.2f}"))
    lines.append("-" * RECEIPT_WIDTH)

    if payment_method == 'cash':
        lines.append(_line("Paid by Cash:", f"${cash_tendered:.2f}"))
        lines.append(_line("Change Due:", f"${change_due:.2f}"))
    else:
        lines.append("Payment: Card")

    return lines


def preview_receipt(sale_id, cashier, cart_items, totals, payment_method, cash_tendered, change_due):
    """Returns the receipt as a plain-text string — no printer or hardware
    needed. Use this to check content/layout before real hardware is set up.
    """
    lines = [STORE_NAME, STORE_ADDRESS, STORE_PHONE, "-" * RECEIPT_WIDTH]
    lines.extend(_build_body_lines(sale_id, cashier, cart_items, totals, payment_method, cash_tendered, change_due))
    lines.append("")
    lines.append("Thank you for shopping with us!")

    border = "=" * RECEIPT_WIDTH
    return border + "\n" + "\n".join(lines) + "\n" + border


def print_receipt(sale_id, cashier, cart_items, totals, payment_method, cash_tendered, change_due):
    """Prints a receipt and, for cash sales, kicks the cash drawer.

    Raises on any failure — callers should catch this and show a warning
    rather than treat it as a checkout failure, since the sale is already
    committed to the database by the time this is called.
    """
    printer_name = os.getenv('PRINTER_NAME')
    if not printer_name:
        raise RuntimeError(
            "PRINTER_NAME is not set in .env — run list_printers.py on the "
            "register PC to find the exact printer name, then add it to .env."
        )

    from escpos.printer import Win32Raw  # imported lazily so preview_receipt() works with no printer drivers at all

    p = Win32Raw(printer_name)
    try:
        p.set(align='center', bold=True, width=2, height=2)
        p.text(STORE_NAME + "\n")
        p.set(align='center', bold=False, width=1, height=1)
        p.text(STORE_ADDRESS + "\n")
        p.text(STORE_PHONE + "\n")
        p.text("-" * RECEIPT_WIDTH + "\n")

        p.set(align='left')
        for line in _build_body_lines(sale_id, cashier, cart_items, totals, payment_method, cash_tendered, change_due):
            p.text(line + "\n")

        p.text("\n")
        p.set(align='center')
        p.text("Thank you for shopping with us!\n")
        p.text("\n\n")
        p.cut()

        if payment_method == 'cash':
            p.cashdraw(DRAWER_PIN)
    finally:
        p.close()
