# list_printers.py — one-time discovery script, safe to delete after use.
# Run this to get the exact printer name Windows uses, needed for receipt printing.
import win32print

printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
print("Installed printers:")
for flags, description, name, comment in printers:
    print(f"  - {name}")

print(f"\nDefault printer: {win32print.GetDefaultPrinter()}")
