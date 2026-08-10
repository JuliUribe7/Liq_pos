
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
                    total_amount DECIMAL(10,2) NOT NULL,
                    cashier VARCHAR(100) NOT NULL,
                    payment_method VARCHAR(50) DEFAULT 'cash'
                )
            """)
            
            # Create sale_items table
            print("Creating sale_items table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (
                    sale_item_id SERIAL PRIMARY KEY,
                    sale_id INTEGER REFERENCES sales(sale_id) ON DELETE CASCADE,
                    item_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL
                )
            """)
            
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