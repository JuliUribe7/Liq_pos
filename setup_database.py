
# setup_database.py
"""
Run this script once to set up the required database tables for the POS system.
This will create the users, sales, and sale_items tables.
"""

import os
import secrets

from db import get_conn, create_user


def _env_or_default(key: str, default: str) -> str:
    return os.getenv(key) or default


def _env_or_random_password(key: str) -> str:
    return os.getenv(key) or secrets.token_urlsafe()

def setup_database():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Create users table
            print("Creating users table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'cashier',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create sales table
            print("Creating sales table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id SERIAL PRIMARY KEY,
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
                    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                    total_amount DECIMAL(10,2) NOT NULL,
                    cashier VARCHAR(100) NOT NULL,
                    payment_method VARCHAR(50) DEFAULT 'cash',
                    cash_tendered DECIMAL(10,2),
                    change_due DECIMAL(10,2)
                )
            """)

            # Create sale_items table
            print("Creating sale_items table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (
                    sale_item_id SERIAL PRIMARY KEY,
                    sale_id INTEGER REFERENCES sales(sale_id) ON DELETE CASCADE,
                    item_id INTEGER,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    item_name VARCHAR(255),
                    is_custom BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)

            # Create suppliers table (matches live schema — items.supplier_id references it)
            print("Creating suppliers table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    supplier_id SERIAL PRIMARY KEY,
                    company_name TEXT,
                    contact TEXT,
                    address TEXT,
                    city_st_zip TEXT,
                    phone TEXT,
                    email TEXT
                )
            """)

            # Create items table (matches live schema, seeded historically via Excel import)
            print("Creating items table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id SERIAL PRIMARY KEY,
                    barcode TEXT,
                    supplier_id INTEGER REFERENCES suppliers(supplier_id),
                    brand TEXT,
                    size TEXT,
                    price DOUBLE PRECISION,
                    cost DOUBLE PRECISION,
                    type TEXT
                )
            """)

            # Create inventory table
            print("Creating inventory table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    inv_id SERIAL PRIMARY KEY,
                    item_id INTEGER REFERENCES items(item_id),
                    barcode VARCHAR(100),
                    quantity INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Reconcile columns/constraints on tables that already existed
            # before this schema was updated (safe to re-run any number of times).
            print("Reconciling existing table columns...")
            cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS subtotal DECIMAL(10,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'cash'")
            cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS cash_tendered DECIMAL(10,2)")
            cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS change_due DECIMAL(10,2)")
            cur.execute("ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS item_name VARCHAR(255)")
            cur.execute("ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS is_custom BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE sale_items ALTER COLUMN item_id DROP NOT NULL")

            # New item fields for the Inventory screen (legacy-parity build)
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS description TEXT")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS class VARCHAR(50)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS case_qty INTEGER")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS bin_number VARCHAR(50)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS vendor_item VARCHAR(100)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS item_notes TEXT")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS par_level INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS reorder_pt INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS on_order INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS order_lot VARCHAR(10) NOT NULL DEFAULT 'case'")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS last_order_date DATE")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS last_receive_date DATE")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS deposit_sale_enabled BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS deposit_sale_amount DECIMAL(10,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS deposit_return_enabled BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS deposit_return_amount DECIMAL(10,2) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS sales_tax BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS discount_ok BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS last_cost DECIMAL(10,2)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS case_cost DECIMAL(10,2)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS last_case_cost DECIMAL(10,2)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS case_price DECIMAL(10,2)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS twofer_price DECIMAL(10,2)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS threefer_price DECIMAL(10,2)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS disc_pool VARCHAR(50)")
            cur.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS image_path VARCHAR(500)")

            # items.item_id predates this script (seeded via Excel import) and was
            # created without an auto-increment sequence, so CREATE TABLE IF NOT
            # EXISTS above never gave it one. Attach one now so new rows get an
            # item_id without the app specifying it. (inventory.inv_id is already
            # a GENERATED ALWAYS AS IDENTITY column — no fix needed there.)
            print("Ensuring auto-increment sequence on items.item_id...")
            cur.execute("CREATE SEQUENCE IF NOT EXISTS items_item_id_seq OWNED BY items.item_id")
            cur.execute("SELECT setval('items_item_id_seq', COALESCE((SELECT MAX(item_id) FROM items), 0) + 1, false)")
            cur.execute("ALTER TABLE items ALTER COLUMN item_id SET DEFAULT nextval('items_item_id_seq')")

            # Create indexes for better performance
            print("Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sales_date 
                ON sales(sale_date)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id 
                ON sale_items(sale_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sale_items_item_id 
                ON sale_items(item_id)
            """)
            
            conn.commit()
            print("\n✓ Database tables created successfully!")
            
        # Create default admin user if not exists
        print("\nSetting up default users...")
        admin_user = _env_or_default("DEFAULT_ADMIN_USER", "admin")
        admin_pass = _env_or_random_password("DEFAULT_ADMIN_PASSWORD")
        cashier_user = _env_or_default("DEFAULT_CASHIER_USER", "cashier")
        cashier_pass = _env_or_random_password("DEFAULT_CASHIER_PASSWORD")

        try:
            create_user(admin_user, admin_pass, "admin")
            print(f"✓ Admin user created (username: {admin_user}, password: {admin_pass})")
        except Exception as e:
            print(f"Admin user may already exist: {e}")
            
        try:
            create_user(cashier_user, cashier_pass, "cashier")
            print(f"✓ Cashier user created (username: {cashier_user}, password: {cashier_pass})")
        except Exception as e:
            print(f"Cashier user may already exist: {e}")
            
        print("\n" + "="*50)
        print("Database setup complete!")
        print("="*50)
        print("\nYou can now run login_gui.py to start the application.")
        print("\nDefault login credentials:")
        print(f"  Admin: username='{admin_user}', password='{admin_pass}'")
        print(f"  Cashier: username='{cashier_user}', password='{cashier_pass}'")
        print("\nIMPORTANT: Change these passwords after first login!")
        
    except Exception as e:
        print(f"\n✗ Error setting up database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("="*50)
    print("LiquorPOS Database Setup")
    print("="*50)
    print("\nThis will create the necessary tables for the POS system.")
    input("Press Enter to continue...")
    
    setup_database()