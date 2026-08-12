from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3


app = Flask(__name__)
app.secret_key = "bulkorder-pro-secret-key"

DATABASE = "bulk_orderpro.db"


# =========================================================
# FIXED MANAGER / STAFF ACCOUNTS
# =========================================================

USERS = {

    # MANAGERS

    "bpmanager1@bulkorderpro.com": {
        "password": "M@nager#2026!",
        "role": "manager"
    },

    "bpmanager2@bulkorderpro.com": {
        "password": "BulkPr0#Lead27!",
        "role": "manager"
    },

    "bpmanager3@bulkorderpro.com": {
        "password": "SVS!Manager28$",
        "role": "manager"
    },

    # STAFF

    "bpstaff1@bulkorderpro.com": {
        "password": "St@ff#Ravi26!",
        "role": "staff"
    },

    "bpstaff2@bulkorderpro.com": {
        "password": "Inv3ntory$27!",
        "role": "staff"
    },

    "bpstaff3@bulkorderpro.com": {
        "password": "Ord3rs&Pack26!",
        "role": "staff"
    },

    "bpstaff4@bulkorderpro.com": {
        "password": "Sh3lf$Stock28!",
        "role": "staff"
    }
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_database_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def create_database():

    connection = get_database_connection()
    cursor = connection.cursor()


    # ---------------- CUSTOMERS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date_added TEXT DEFAULT CURRENT_DATE
        )
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
            stock_quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    """)


    # If the existing database was created before
    # is_deleted was added, add it now.

    cursor.execute("PRAGMA table_info(stock)")

    stock_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

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


    # Make sure older orders tables have stock_id.

    cursor.execute("PRAGMA table_info(orders)")

    order_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "stock_id" not in order_columns:

        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN stock_id INTEGER
        """)


    # ---------------- HISTORY ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date_time TEXT
            DEFAULT (datetime('now', 'localtime')),

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
            sunday_hours TEXT,
            theme TEXT NOT NULL DEFAULT 'light'
        )
    """)


    # Create the default settings the first time
    # the program runs.

    # Settings

    cursor.execute("""
        SELECT id
        FROM settings
        WHERE id = 1
    """)

    existing_settings = cursor.fetchone()


    if not existing_settings:

        cursor.execute("""
            INSERT INTO settings (
                id,
                business_name,
                store_phone,
                store_email,
                pickup_address,
                weekday_hours,
                saturday_hours,
                sunday_hours,
                theme
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1,
            "BulkOrder Pro",
            "",
            "",
            "",
            "9:00 AM - 6:00 PM",
            "9:00 AM - 3:00 PM",
            "Closed",
            "light"
        ))

    connection.commit()
    connection.close()


# =========================================================
# HISTORY HELPER
# =========================================================

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

# =========================================================
# GET SETTINGS
# =========================================================

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

# =========================================================
# LOGIN CHECKS
# =========================================================

def user_logged_in():

    return "username" in session


def customer_logged_in():

    return "customer_id" in session


# =========================================================
# PORTAL HOMEPAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "portal.html"
    )


# =========================================================
# CUSTOMER PRODUCT LIST
# =========================================================

def get_customer_products():

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            item_name,
            brand,
            stock_quantity,
            price

        FROM stock

        WHERE is_deleted = 0

        ORDER BY item_name
    """)

    stock_records = cursor.fetchall()

    customer_products = []


    for item in stock_records:

        if item["stock_quantity"] <= 0:

            customer_status = "Out of Stock"
            is_available = False

        else:

            customer_status = "Available"
            is_available = True


        customer_products.append({

            "id": item["id"],

            "item_name": item["item_name"],

            "brand": item["brand"],

            "price": item["price"],

            "customer_status": customer_status,

            "is_available": is_available

        })


    connection.close()

    return customer_products


# =========================================================
# GET LOGGED IN CUSTOMER
# =========================================================

def get_logged_in_customer():

    if not customer_logged_in():

        return None


    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            customer_name,
            phone

        FROM customers

        WHERE id = ?
    """, (
        session["customer_id"],
    ))

    customer = cursor.fetchone()

    connection.close()

    return customer


# =========================================================
# CUSTOMER REGISTER PAGE
# =========================================================

@app.route("/customer-register")
def customer_register_page():

    if customer_logged_in():

        return redirect(
            url_for("customer_order_page")
        )


    return render_template(
        "customer_register.html"
    )


# =========================================================
# REGISTER CUSTOMER
# =========================================================

@app.route(
    "/customer-register",
    methods=["POST"]
)
def customer_register():

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )


    if not all([
        customer_name,
        phone,
        username,
        password
    ]):

        return render_template(
            "customer_register.html",
            error="Please complete every field."
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    # Check username

    cursor.execute("""
        SELECT id
        FROM customer_accounts
        WHERE username = ?
    """, (
        username,
    ))

    existing_username = cursor.fetchone()


    if existing_username:

        connection.close()

        return render_template(
            "customer_register.html",
            error="That username is already being used."
        )


    # Check phone

    cursor.execute("""
        SELECT id
        FROM customers
        WHERE phone = ?
    """, (
        phone,
    ))

    existing_customer = cursor.fetchone()


    if existing_customer:

        customer_id = existing_customer["id"]

        cursor.execute("""
            SELECT id
            FROM customer_accounts
            WHERE customer_id = ?
        """, (
            customer_id,
        ))

        existing_account = cursor.fetchone()


        if existing_account:

            connection.close()

            return render_template(
                "customer_register.html",
                error=(
                    "An account already exists "
                    "for this phone number."
                )
            )


        cursor.execute("""
            UPDATE customers
            SET customer_name = ?
            WHERE id = ?
        """, (
            customer_name,
            customer_id
        ))


    else:

        cursor.execute("""
            INSERT INTO customers (
                customer_name,
                phone
            )
            VALUES (?, ?)
        """, (
            customer_name,
            phone
        ))

        customer_id = cursor.lastrowid


    password_hash = generate_password_hash(
        password
    )


    cursor.execute("""
        INSERT INTO customer_accounts (
            customer_id,
            username,
            password_hash
        )
        VALUES (?, ?, ?)
    """, (
        customer_id,
        username,
        password_hash
    ))


    # Record customer registration

    add_history(
        connection,
        username,
        "Customer",
        "Customers",
        f'Customer account registered for "{customer_name}".'
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("customer_login_page")
    )


# =========================================================
# CUSTOMER LOGIN PAGE
# =========================================================

@app.route("/customer-login")
def customer_login_page():

    if customer_logged_in():

        return redirect(
            url_for("customer_order_page")
        )


    return render_template(
        "customer_login.html"
    )


# =========================================================
# CUSTOMER LOGIN
# =========================================================

@app.route(
    "/customer-login",
    methods=["POST"]
)
def customer_login():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            customer_accounts.customer_id,
            customer_accounts.username,
            customer_accounts.password_hash,
            customers.customer_name,
            customers.phone

        FROM customer_accounts

        JOIN customers

        ON customer_accounts.customer_id
        = customers.id

        WHERE customer_accounts.username = ?
    """, (
        username,
    ))


    customer = cursor.fetchone()


    if (
        customer
        and check_password_hash(
            customer["password_hash"],
            password
        )
    ):

        session["customer_id"] = (
            customer["customer_id"]
        )

        session["customer_username"] = (
            customer["username"]
        )

        session["customer_name"] = (
            customer["customer_name"]
        )


        add_history(
            connection,
            customer["username"],
            "Customer",
            "Login",
            "Customer logged in."
        )


        connection.commit()
        connection.close()


        return redirect(
            url_for("customer_order_page")
        )


    connection.close()


    return render_template(
        "customer_login.html",
        error="Invalid username or password."
    )


# =========================================================
# CUSTOMER LOGOUT
# =========================================================

@app.route("/customer-logout")
def customer_logout():

    session.pop(
        "customer_id",
        None
    )

    session.pop(
        "customer_username",
        None
    )

    session.pop(
        "customer_name",
        None
    )


    return redirect(
        url_for("customer_login_page")
    )


# =========================================================
# CUSTOMER ORDER PAGE
# =========================================================

@app.route("/customer-order")
def customer_order_page():

    if not customer_logged_in():

        return redirect(
            url_for("customer_login_page")
        )


    products = get_customer_products()

    customer = get_logged_in_customer()


    return render_template(
        "customer_order.html",
        stock_items=products,
        customer=customer
    )


# =========================================================
# CUSTOMER SUBMITS ORDER
# =========================================================

@app.route(
    "/customer-order/submit",
    methods=["POST"]
)
def submit_customer_order():

    if not customer_logged_in():

        return redirect(
            url_for("customer_login_page")
        )


    customer_id = session["customer_id"]

    pickup_date = request.form.get(
        "pickup_date",
        ""
    )


    if not pickup_date:

        return render_template(
            "customer_order.html",
            stock_items=get_customer_products(),
            customer=get_logged_in_customer(),
            error="Please select a pickup date."
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM stock

        WHERE is_deleted = 0

        ORDER BY item_name
    """)


    stock_items = cursor.fetchall()

    selected_items = []


    for item in stock_items:

        if item["stock_quantity"] <= 0:

            continue


        quantity_text = request.form.get(
            f"quantity_{item['id']}",
            "0"
        )


        try:

            quantity = int(quantity_text)

        except ValueError:

            quantity = 0


        if quantity < 0:

            quantity = 0


        if quantity > 0:

            if quantity > item["stock_quantity"]:

                connection.close()

                return render_template(
                    "customer_order.html",
                    stock_items=get_customer_products(),
                    customer=get_logged_in_customer(),
                    error=(
                        f"The requested quantity for "
                        f"{item['item_name']} "
                        f"is unavailable. "
                        f"Please choose a smaller quantity."
                    )
                )


            selected_items.append({
                "stock_id": item["id"],
                "quantity": quantity
            })


    if not selected_items:

        connection.close()

        return render_template(
            "customer_order.html",
            stock_items=get_customer_products(),
            customer=get_logged_in_customer(),
            error=(
                "Please enter a quantity "
                "for at least one available product."
            )
        )


    total_items = sum(
        item["quantity"]
        for item in selected_items
    )


    # Create order

    cursor.execute("""
        INSERT INTO orders (
            customer_id,
            stock_id,
            pickup_date,
            items,
            payment_status,
            order_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        None,
        pickup_date,
        total_items,
        "Unpaid",
        "Pending"
    ))


    order_id = cursor.lastrowid


    # Save products

    for item in selected_items:

        cursor.execute("""
            INSERT INTO order_items (
                order_id,
                stock_id,
                quantity
            )
            VALUES (?, ?, ?)
        """, (
            order_id,
            item["stock_id"],
            item["quantity"]
        ))


        # Reduce stock automatically

        cursor.execute("""
            UPDATE stock
            SET stock_quantity = stock_quantity - ?
            WHERE id = ?
        """, (
            item["quantity"],
            item["stock_id"]
        ))


    # Record order in history

    add_history(
        connection,
        session["customer_username"],
        "Customer",
        "Orders",
        f"Placed Order #{order_id} with {total_items} item(s).",
        order_id=order_id
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("customer_my_orders")
    )


# =========================================================
# CUSTOMER MY ORDERS
# =========================================================

@app.route("/customer-orders")
def customer_my_orders():

    if not customer_logged_in():

        return redirect(
            url_for("customer_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            id,
            pickup_date,
            items,
            payment_status,
            order_status

        FROM orders

        WHERE customer_id = ?

        ORDER BY id DESC
    """, (
        session["customer_id"],
    ))


    order_records = cursor.fetchall()

    customer_orders = []


    for order in order_records:

        cursor.execute("""
            SELECT
                stock.item_name,
                stock.brand,
                stock.price,
                order_items.quantity

            FROM order_items

            JOIN stock

            ON order_items.stock_id
            = stock.id

            WHERE order_items.order_id = ?
        """, (
            order["id"],
        ))


        products = cursor.fetchall()


        customer_orders.append({

            "id": order["id"],

            "pickup_date": order["pickup_date"],

            "items": order["items"],

            "payment_status": order["payment_status"],

            "order_status": order["order_status"],

            "products": products

        })


    connection.close()


    return render_template(
        "customer_orders.html",
        orders=customer_orders
    )


# =========================================================
# STAFF / MANAGER LOGIN PAGE
# =========================================================

@app.route("/staff-login")
def staff_login_page():

    if user_logged_in():

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "staff_login.html"
    )


# =========================================================
# STAFF / MANAGER LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["POST"]
)
def login():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    role = request.form.get(
        "role",
        ""
    )


    user = USERS.get(username)


    if (
        user
        and user["password"] == password
        and user["role"] == role
    ):

        session["username"] = username
        session["role"] = role


        connection = get_database_connection()


        add_history(
            connection,
            username,
            role.title(),
            "Login",
            f"{role.title()} logged in."
        )


        connection.commit()
        connection.close()


        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "staff_login.html",
        error=(
            "Invalid username, "
            "password or role."
        )
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    # ---------------- TOTAL CUSTOMERS ----------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
    """)

    total_customers = cursor.fetchone()[0]


    # ---------------- TOTAL ORDERS ----------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
    """)

    total_orders = cursor.fetchone()[0]


    # ---------------- PENDING ORDERS ----------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Pending'
    """)

    pending_orders = cursor.fetchone()[0]


    # ---------------- TODAY'S PICKUPS ----------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE pickup_date = date('now', 'localtime')
          AND order_status != 'Cancelled'
    """)

    todays_pickups = cursor.fetchone()[0]


    # ---------------- LOW STOCK COUNT ----------------
    #
    # Low stock means fewer than 5 items.
    # Deleted products are ignored.

    cursor.execute("""
        SELECT COUNT(*)
        FROM stock
        WHERE stock_quantity < 5
          AND is_deleted = 0
    """)

    low_stock_count = cursor.fetchone()[0]


    # ---------------- STOCK ALERTS ----------------
    #
    # Show the 5 products that need attention most.

    cursor.execute("""
        SELECT
            id,
            item_name,
            brand,
            stock_quantity

        FROM stock

        WHERE stock_quantity < 5
          AND is_deleted = 0

        ORDER BY
            stock_quantity ASC,
            item_name ASC

        LIMIT 5
    """)

    stock_alerts = cursor.fetchall()


    # ---------------- RECENT ORDERS ----------------

    cursor.execute("""
        SELECT
            orders.id,
            customers.customer_name,
            orders.pickup_date,
            orders.items,
            orders.order_status

        FROM orders

        JOIN customers
        ON orders.customer_id = customers.id

        ORDER BY orders.id DESC

        LIMIT 5
    """)

    recent_orders = cursor.fetchall()


    connection.close()


    return render_template(
        "dashboard.html",

        username=session["username"],
        role=session["role"],

        total_customers=total_customers,
        total_orders=total_orders,
        pending_orders=pending_orders,

        todays_pickups=todays_pickups,

        low_stock_count=low_stock_count,
        stock_alerts=stock_alerts,

        recent_orders=recent_orders
    )

# =========================================================
# CUSTOMERS
# =========================================================

@app.route("/customers")
def customers():

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    search = request.args.get(
        "search",
        ""
    ).strip()


    connection = get_database_connection()
    cursor = connection.cursor()


    if search:

        cursor.execute("""
            SELECT
                customers.id,
                customers.customer_name,
                customers.phone,
                customers.date_added,
                COUNT(orders.id) AS total_orders,
                MAX(orders.pickup_date) AS last_order

            FROM customers

            LEFT JOIN orders

            ON customers.id = orders.customer_id

            WHERE customers.customer_name LIKE ?
               OR customers.phone LIKE ?

            GROUP BY customers.id

            ORDER BY customers.customer_name
        """, (
            f"%{search}%",
            f"%{search}%"
        ))


    else:

        cursor.execute("""
            SELECT
                customers.id,
                customers.customer_name,
                customers.phone,
                customers.date_added,
                COUNT(orders.id) AS total_orders,
                MAX(orders.pickup_date) AS last_order

            FROM customers

            LEFT JOIN orders

            ON customers.id = orders.customer_id

            GROUP BY customers.id

            ORDER BY customers.customer_name
        """)


    customer_records = cursor.fetchall()


    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
    """)

    total_customers = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(DISTINCT customer_id)
        FROM orders
        WHERE order_status = 'Pending'
    """)

    active_customers = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)

        FROM customers

        WHERE strftime('%Y-%m', date_added)
        = strftime('%Y-%m', 'now')
    """)

    new_customers = cursor.fetchone()[0]


    connection.close()


    return render_template(
        "customers.html",
        customers=customer_records,
        total_customers=total_customers,
        active_customers=active_customers,
        new_customers=new_customers,
        search=search
    )


# =========================================================
# DELETE CUSTOMER
# =========================================================

@app.route(
    "/customers/delete/<int:customer_id>",
    methods=["POST"]
)
def delete_customer(customer_id):

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT customer_name
        FROM customers
        WHERE id = ?
    """, (
        customer_id,
    ))


    customer_record = cursor.fetchone()


    cursor.execute("""
        SELECT id
        FROM orders
        WHERE customer_id = ?
    """, (
        customer_id,
    ))


    customer_orders = cursor.fetchall()


    for order in customer_orders:

        cursor.execute("""
            DELETE FROM order_items
            WHERE order_id = ?
        """, (
            order["id"],
        ))


    cursor.execute("""
        DELETE FROM customer_accounts
        WHERE customer_id = ?
    """, (
        customer_id,
    ))


    cursor.execute("""
        DELETE FROM orders
        WHERE customer_id = ?
    """, (
        customer_id,
    ))


    cursor.execute("""
        DELETE FROM customers
        WHERE id = ?
    """, (
        customer_id,
    ))


    if customer_record:

        add_history(
            connection,
            session["username"],
            session["role"].title(),
            "Customers",
            (
                f'Deleted customer '
                f'"{customer_record["customer_name"]}".'
            )
        )


    connection.commit()
    connection.close()


    return redirect(
        url_for("customers")
    )


# =========================================================
# ORDERS
# =========================================================

@app.route("/orders")
def orders():

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    search = request.args.get(
        "search",
        ""
    ).strip()

    payment = request.args.get(
        "payment",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()


    connection = get_database_connection()
    cursor = connection.cursor()


    query = """
        SELECT
            orders.id,
            customers.customer_name,
            customers.phone,
            orders.pickup_date,
            orders.items,
            orders.payment_status,
            orders.order_status

        FROM orders

        JOIN customers

        ON orders.customer_id
        = customers.id

        WHERE 1 = 1
    """


    values = []


    if search:

        query += """
            AND (
                customers.customer_name LIKE ?
                OR customers.phone LIKE ?
            )
        """

        values.append(
            f"%{search}%"
        )

        values.append(
            f"%{search}%"
        )


    if payment:

        query += """
            AND orders.payment_status = ?
        """

        values.append(payment)


    if status:

        query += """
            AND orders.order_status = ?
        """

        values.append(status)


    query += """
        ORDER BY orders.id DESC
    """


    cursor.execute(
        query,
        values
    )


    order_records = cursor.fetchall()

    orders_with_items = []


    for order in order_records:

        cursor.execute("""
            SELECT
                stock.item_name,
                stock.brand,
                stock.price,
                order_items.quantity

            FROM order_items

            JOIN stock

            ON order_items.stock_id
            = stock.id

            WHERE order_items.order_id = ?
        """, (
            order["id"],
        ))


        products = cursor.fetchall()


        if products:

            total_items = sum(
                product["quantity"]
                for product in products
            )

        else:

            total_items = order["items"]


        orders_with_items.append({

            "id": order["id"],

            "customer_name": order["customer_name"],

            "phone": order["phone"],

            "pickup_date": order["pickup_date"],

            "payment_status": order["payment_status"],

            "order_status": order["order_status"],

            "products": products,

            "total_items": total_items

        })


    connection.close()


    return render_template(
        "orders.html",
        orders=orders_with_items,
        search=search,
        payment=payment,
        status=status
    )



# =========================================================
# UPDATE ORDER STATUS
# =========================================================

@app.route(
    "/orders/status/<int:order_id>",
    methods=["POST"]
)
def update_order_status(order_id):

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    new_status = request.form.get(
        "order_status",
        ""
    ).strip()


    allowed_statuses = [
        "Pending",
        "Preparing",
        "Ready for Pickup",
        "Collected",
        "Cancelled"
    ]


    if new_status not in allowed_statuses:

        return redirect(
            url_for("orders")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT order_status
        FROM orders
        WHERE id = ?
    """, (
        order_id,
    ))


    order = cursor.fetchone()


    if not order:

        connection.close()

        return redirect(
            url_for("orders")
        )


    previous_status = order["order_status"]


    if previous_status == new_status:

        connection.close()

        return redirect(
            url_for("orders")
        )


    cursor.execute("""
        UPDATE orders
        SET order_status = ?
        WHERE id = ?
    """, (
        new_status,
        order_id
    ))


    add_history(
        connection,
        session["username"],
        session["role"].title(),
        "Orders",
        (
            f'Changed Order #{order_id} '
            f'from "{previous_status}" '
            f'to "{new_status}".'
        ),
        action_type="revert_order",
        order_id=order_id,
        previous_status=previous_status,
        new_status=new_status
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("orders")
    )


# =========================================================
# STOCK PAGE
# =========================================================

@app.route("/stock")
def stock():

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    stock_filter = request.args.get(
        "filter",
        "all"
    )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM stock

        WHERE is_deleted = 0

        ORDER BY
            stock_quantity ASC,
            item_name ASC
    """)


    stock_records = cursor.fetchall()


    all_stock_items = []
    low_stock_items = []


    total_products = 0
    in_stock_count = 0
    running_low_count = 0
    low_stock_count = 0
    out_of_stock_count = 0


    for item in stock_records:

        quantity = item["stock_quantity"]

        total_products += 1


        if quantity == 0:

            status = "Out of Stock"
            status_key = "out"

            out_of_stock_count += 1


        elif quantity < 5:

            status = "Low Stock Alert"
            status_key = "low"

            low_stock_count += 1


        elif quantity <= 10:

            status = "Running Low"
            status_key = "running"

            running_low_count += 1


        else:

            status = "In Stock"
            status_key = "in"

            in_stock_count += 1


        stock_item = {

            "id": item["id"],

            "item_name": item["item_name"],

            "brand": item["brand"],

            "stock_quantity": quantity,

            "price": item["price"],

            "status": status,

            "status_key": status_key

        }


        all_stock_items.append(
            stock_item
        )


        if quantity < 5:

            low_stock_items.append(
                stock_item
            )


    if stock_filter == "in":

        stock_items = [
            item
            for item in all_stock_items
            if item["status_key"] == "in"
        ]


    elif stock_filter == "running":

        stock_items = [
            item
            for item in all_stock_items
            if item["status_key"] == "running"
        ]


    elif stock_filter == "low":

        stock_items = [
            item
            for item in all_stock_items
            if item["status_key"] == "low"
        ]


    elif stock_filter == "out":

        stock_items = [
            item
            for item in all_stock_items
            if item["status_key"] == "out"
        ]


    else:

        stock_filter = "all"
        stock_items = all_stock_items


    connection.close()


    return render_template(
        "stock.html",
        stock_items=stock_items,
        low_stock_items=low_stock_items,
        stock_filter=stock_filter,
        total_products=total_products,
        in_stock_count=in_stock_count,
        running_low_count=running_low_count,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count
    )


# =========================================================
# ADD STOCK ITEM
# =========================================================

@app.route(
    "/stock/add",
    methods=["POST"]
)
def add_stock():

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    brand = request.form.get(
        "brand",
        ""
    ).strip()

    stock_quantity = request.form.get(
        "stock_quantity",
        ""
    )

    price = request.form.get(
        "price",
        ""
    )


    if not all([
        item_name,
        brand,
        stock_quantity,
        price
    ]):

        return redirect(
            url_for("stock")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        INSERT INTO stock (
            item_name,
            brand,
            stock_quantity,
            price,
            is_deleted
        )
        VALUES (?, ?, ?, ?, 0)
    """, (
        item_name,
        brand,
        stock_quantity,
        price
    ))


    stock_id = cursor.lastrowid


    add_history(
        connection,
        session["username"],
        session["role"].title(),
        "Stock",
        (
            f'Added stock item "{item_name}" '
            f'({brand}) with {stock_quantity} units.'
        ),
        stock_id=stock_id
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("stock")
    )


# =========================================================
# REFILL STOCK
# =========================================================

@app.route(
    "/stock/refill/<int:stock_id>",
    methods=["POST"]
)
def refill_stock(stock_id):

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    refill_quantity = request.form.get(
        "refill_quantity",
        ""
    )


    try:

        refill_quantity = int(
            refill_quantity
        )

    except ValueError:

        return redirect(
            url_for("stock")
        )


    if refill_quantity <= 0:

        return redirect(
            url_for("stock")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            item_name,
            brand,
            stock_quantity

        FROM stock

        WHERE id = ?
          AND is_deleted = 0
    """, (
        stock_id,
    ))


    stock_item = cursor.fetchone()


    if not stock_item:

        connection.close()

        return redirect(
            url_for("stock")
        )


    old_quantity = stock_item["stock_quantity"]


    cursor.execute("""
        UPDATE stock

        SET stock_quantity
        = stock_quantity + ?

        WHERE id = ?
    """, (
        refill_quantity,
        stock_id
    ))


    new_quantity = (
        old_quantity + refill_quantity
    )


    add_history(
        connection,
        session["username"],
        session["role"].title(),
        "Stock",
        (
            f'Refilled "{stock_item["item_name"]}" '
            f'by {refill_quantity} units '
            f'({old_quantity} → {new_quantity}).'
        ),
        stock_id=stock_id
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("stock")
    )


# =========================================================
# DELETE STOCK
# =========================================================

@app.route(
    "/stock/delete/<int:stock_id>",
    methods=["POST"]
)
def delete_stock(stock_id):

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            item_name,
            brand,
            stock_quantity,
            price

        FROM stock

        WHERE id = ?
          AND is_deleted = 0
    """, (
        stock_id,
    ))


    stock_item = cursor.fetchone()


    if not stock_item:

        connection.close()

        return redirect(
            url_for("stock")
        )


    # Soft delete the item instead of permanently
    # deleting it. This allows History to restore it.

    cursor.execute("""
        UPDATE stock

        SET is_deleted = 1

        WHERE id = ?
    """, (
        stock_id,
    ))


    add_history(
        connection,
        session["username"],
        session["role"].title(),
        "Stock",
        (
            f'Deleted stock item '
            f'"{stock_item["item_name"]}" '
            f'({stock_item["brand"]}).'
        ),
        action_type="restore_stock",
        stock_id=stock_id
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("stock")
    )


# =========================================================
# HISTORY PAGE
# =========================================================

@app.route("/history")
def history():

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    search = request.args.get(
        "search",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()


    connection = get_database_connection()
    cursor = connection.cursor()


    query = """
        SELECT *
        FROM history

        WHERE 1 = 1
    """


    values = []


    if search:

        query += """
            AND (
                user LIKE ?
                OR role LIKE ?
                OR category LIKE ?
                OR activity LIKE ?
            )
        """

        search_value = f"%{search}%"

        values.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])


    if category:

        query += """
            AND category = ?
        """

        values.append(category)


    query += """
        ORDER BY id DESC
    """


    cursor.execute(
        query,
        values
    )


    history_rows = cursor.fetchall()


    history_records = []


    for record in history_rows:

        # Once Restore/Revert has been used,
        # no button should appear again.

        action_type = record["action_type"]

        if record["is_used"] == 1:

            action_type = None


        history_records.append({

            "id": record["id"],

            "date_time": record["date_time"],

            "user": record["user"],

            "role": record["role"],

            "category": record["category"],

            "activity": record["activity"],

            "action_type": action_type

        })


    connection.close()


    return render_template(
        "history.html",
        history_records=history_records,
        search=search,
        category=category
    )


# =========================================================
# RESTORE DELETED STOCK
# =========================================================

@app.route(
    "/history/restore-stock/<int:history_id>",
    methods=["POST"]
)
def restore_history_item(history_id):

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM history

        WHERE id = ?
          AND action_type = 'restore_stock'
          AND is_used = 0
    """, (
        history_id,
    ))


    history_record = cursor.fetchone()


    if not history_record:

        connection.close()

        return redirect(
            url_for("history")
        )


    stock_id = history_record["stock_id"]


    cursor.execute("""
        SELECT
            item_name,
            brand

        FROM stock

        WHERE id = ?
    """, (
        stock_id,
    ))


    stock_item = cursor.fetchone()


    if stock_item:

        cursor.execute("""
            UPDATE stock

            SET is_deleted = 0

            WHERE id = ?
        """, (
            stock_id,
        ))


        cursor.execute("""
            UPDATE history

            SET is_used = 1

            WHERE id = ?
        """, (
            history_id,
        ))


        add_history(
            connection,
            session["username"],
            session["role"].title(),
            "Stock",
            (
                f'Restored stock item '
                f'"{stock_item["item_name"]}" '
                f'({stock_item["brand"]}).'
            ),
            stock_id=stock_id
        )


    connection.commit()
    connection.close()


    return redirect(
        url_for("history")
    )


# =========================================================
# REVERT ORDER STATUS
# =========================================================

@app.route(
    "/history/revert-order/<int:history_id>",
    methods=["POST"]
)
def revert_history_order(history_id):

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM history

        WHERE id = ?
          AND action_type = 'revert_order'
          AND is_used = 0
    """, (
        history_id,
    ))


    history_record = cursor.fetchone()


    if not history_record:

        connection.close()

        return redirect(
            url_for("history")
        )


    order_id = history_record["order_id"]

    previous_status = (
        history_record["previous_status"]
    )


    if order_id and previous_status:

        cursor.execute("""
            UPDATE orders

            SET order_status = ?

            WHERE id = ?
        """, (
            previous_status,
            order_id
        ))


        cursor.execute("""
            UPDATE history

            SET is_used = 1

            WHERE id = ?
        """, (
            history_id,
        ))


        add_history(
            connection,
            session["username"],
            session["role"].title(),
            "Orders",
            (
                f'Reverted Order #{order_id} '
                f'to "{previous_status}".'
            ),
            order_id=order_id
        )


    connection.commit()
    connection.close()


    return redirect(
        url_for("history")
    )

# =========================================================
# SETTINGS PAGE - MANAGER ONLY
# =========================================================

@app.route("/settings")
def settings():

    # User must be logged in.

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    # Only managers can access Settings.

    if session.get("role") != "manager":

        return redirect(
            url_for("dashboard")
        )


    current_settings = get_settings()


    return render_template(
        "settings.html",
        settings=current_settings,
        username=session["username"],
        role=session["role"]
    )


# =========================================================
# UPDATE SETTINGS - MANAGER ONLY
# =========================================================

@app.route(
    "/settings/update",
    methods=["POST"]
)
def update_settings():

    # User must be logged in.

    if not user_logged_in():

        return redirect(
            url_for("staff_login_page")
        )


    # Only managers can change settings.

    if session.get("role") != "manager":

        return redirect(
            url_for("dashboard")
        )


    business_name = request.form.get(
        "business_name",
        ""
    ).strip()


    store_phone = request.form.get(
        "store_phone",
        ""
    ).strip()


    store_email = request.form.get(
        "store_email",
        ""
    ).strip()


    pickup_address = request.form.get(
        "pickup_address",
        ""
    ).strip()


    weekday_hours = request.form.get(
        "weekday_hours",
        ""
    ).strip()


    saturday_hours = request.form.get(
        "saturday_hours",
        ""
    ).strip()


    sunday_hours = request.form.get(
        "sunday_hours",
        ""
    ).strip()


    

    # Business name cannot be empty.

    if not business_name:

        business_name = "BulkOrder Pro"




    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        UPDATE settings

        SET
            business_name = ?,
            store_phone = ?,
            store_email = ?,
            pickup_address = ?,
            weekday_hours = ?,
            saturday_hours = ?,
            sunday_hours = ?
            

        WHERE id = 1
    """, (
        business_name,
        store_phone,
        store_email,
        pickup_address,
        weekday_hours,
        saturday_hours,
        sunday_hours
        
    ))


    # Add the change to History.

    add_history(
        connection,
        session["username"],
        session["role"].title(),
        "Settings",
        "Updated business settings."
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("settings")
    )

# =========================================================
# STAFF / MANAGER LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop(
        "username",
        None
    )

    session.pop(
        "role",
        None
    )


    return redirect(
        url_for("staff_login_page")
    )


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)