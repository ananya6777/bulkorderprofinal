import sqlite3
from config import DATABASE


def get_database_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_database_connection()
    cursor = connection.cursor()

    # ---------------- CUSTOMERS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            last_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL,
            date_added TEXT DEFAULT CURRENT_DATE
        )
    """)

    cursor.execute("PRAGMA table_info(customers)")
    customer_columns = [column[1] for column in cursor.fetchall()]

    if "last_name" not in customer_columns:
        cursor.execute("""
            ALTER TABLE customers
            ADD COLUMN last_name TEXT NOT NULL DEFAULT ''
        """)

    # ---------------- CUSTOMER ACCOUNTS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            FOREIGN KEY (customer_id)
            REFERENCES customers(id)
        )
    """)

    # ---------------- STOCK ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Other',
            stock_quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(stock)")
    stock_columns = [column[1] for column in cursor.fetchall()]

    if "category" not in stock_columns:
        cursor.execute("""
            ALTER TABLE stock
            ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'
        """)

    if "is_deleted" not in stock_columns:
        cursor.execute("""
            ALTER TABLE stock
            ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0
        """)

    # ---------------- ORDERS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            stock_id INTEGER,
            pickup_date TEXT NOT NULL,
            items INTEGER NOT NULL DEFAULT 0,
            payment_status TEXT NOT NULL,
            order_status TEXT NOT NULL,
            FOREIGN KEY (customer_id)
            REFERENCES customers(id)
        )
    """)

    cursor.execute("PRAGMA table_info(orders)")
    order_columns = [column[1] for column in cursor.fetchall()]

    if "stock_id" not in order_columns:
        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN stock_id INTEGER
        """)

    # ---------------- ORDER ITEMS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            stock_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id)
            REFERENCES orders(id),
            FOREIGN KEY (stock_id)
            REFERENCES stock(id)
        )
    """)

    # ---------------- HISTORY ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time TEXT DEFAULT (datetime('now','localtime')),
            user TEXT NOT NULL,
            role TEXT NOT NULL,
            category TEXT NOT NULL,
            activity TEXT NOT NULL,
            action_type TEXT,
            stock_id INTEGER,
            order_id INTEGER,
            previous_status TEXT,
            new_status TEXT,
            is_used INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ---------------- SETTINGS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            business_name TEXT NOT NULL,
            store_phone TEXT,
            store_email TEXT,
            pickup_address TEXT,
            weekday_hours TEXT,
            saturday_hours TEXT,
            sunday_hours TEXT
        )
    """)

    cursor.execute("""
        SELECT id
        FROM settings
        WHERE id = 1
    """)

    if not cursor.fetchone():

        cursor.execute("""
            INSERT INTO settings (
                id,
                business_name,
                store_phone,
                store_email,
                pickup_address,
                weekday_hours,
                saturday_hours,
                sunday_hours
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1,
            "BulkOrder Pro",
            "",
            "",
            "",
            "9:00 AM - 6:00 PM",
            "9:00 AM - 3:00 PM",
            "Closed"
        ))

    connection.commit()
    connection.close()


def add_history(
    connection,
    user,
    role,
    category,
    activity,
    action_type=None,
    stock_id=None,
    order_id=None,
    previous_status=None,
    new_status=None
):

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO history (
            user,
            role,
            category,
            activity,
            action_type,
            stock_id,
            order_id,
            previous_status,
            new_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user,
        role,
        category,
        activity,
        action_type,
        stock_id,
        order_id,
        previous_status,
        new_status
    ))


def get_settings():

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM settings
        WHERE id = 1
    """)

    settings = cursor.fetchone()

    connection.close()

    return settings