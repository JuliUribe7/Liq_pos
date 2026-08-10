import psycopg2
from dotenv import load_dotenv
from utils import hash_password
import os

# Loads Environment Details
load_dotenv()

# DB Credentials layout in .env.example

def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
    )

def get_user_by_username_pg(username: str):
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                SELECT username, password_hash, role, is_active
                FROM users
                WHERE username = %s
            """, (username,))
            return cur.fetchone()
    finally:
        conn.close()


def create_user_pg(username: str, raw_password: str, role: str = "cashier"):
    conn = get_conn()
    try:
        pw_hash = hash_password(raw_password)
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (%s, %s, %s, TRUE)
            """, (username, pw_hash, role))
    finally:
        conn.close()


def get_user_by_username(username: str):
    return get_user_by_username_pg(username)


def create_user(username: str, password: str, role: str = "cashier"):
    return create_user_pg(username, password, role)
