from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "bulkorder-pro-secret-key"

DATABASE = "bulk_orderpro.db"


USERS = {
    "manager": {
        "password": "manager123",
        "role": "manager"
    },
    "staff": {
        "password": "staff123",
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

    # CUSTOMERS TABLE

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date_added TEXT DEFAULT CURRENT_DATE
        )
    """)

    # STOCK TABLE

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            brand TEXT NOT NULL,
            stock_quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)

    # ORDERS TABLE

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            stock_id INTEGER,
            pickup_date TEXT NOT NULL,
            items INTEGER NOT NULL DEFAULT 0,
            payment_status TEXT NOT NULL,
            order_status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # ORDER ITEMS TABLE

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            stock_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (stock_id) REFERENCES stock(id)
        )
    """)

    # Makes sure older databases have stock_id

    cursor.execute("PRAGMA table_info(orders)")
    order_columns = [column[1] for column in cursor.fetchall()]

    if "stock_id" not in order_columns:
        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN stock_id INTEGER
        """)

    connection.commit()
    connection.close()


# =========================================================
# LOGIN CHECK
# =========================================================

def user_logged_in():
    return "username" in session


# =========================================================
# GET AVAILABLE STOCK
# =========================================================

def get_available_stock():
    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM stock
        WHERE stock_quantity > 0
        ORDER BY item_name
    """)

    stock_items = cursor.fetchall()

    connection.close()

    return stock_items


# =========================================================
# PUBLIC CUSTOMER ORDER PAGE
# =========================================================

@app.route("/customer-order")
def customer_order_page():

    stock_items = get_available_stock()

    return render_template(
        "customer_order.html",
        stock_items=stock_items
    )


# =========================================================
# CUSTOMER SUBMITS ORDER
# =========================================================

@app.route("/customer-order/submit", methods=["POST"])
def submit_customer_order():

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    pickup_date = request.form.get(
        "pickup_date",
        ""
    )

    if not customer_name or not phone or not pickup_date:

        return render_template(
            "customer_order.html",
            stock_items=get_available_stock(),
            error="Please enter your name, phone number and pickup date."
        )

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM stock
        WHERE stock_quantity > 0
        ORDER BY item_name
    """)

    stock_items = cursor.fetchall()

    selected_items = []

    for item in stock_items:

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
                    stock_items=get_available_stock(),
                    error=(
                        f"Not enough stock is available for "
                        f"{item['item_name']}."
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
            stock_items=get_available_stock(),
            error="Please enter a quantity for at least one product."
        )

    # FIND CUSTOMER

    cursor.execute("""
        SELECT id
        FROM customers
        WHERE phone = ?
    """, (phone,))

    customer = cursor.fetchone()

    if customer:

        customer_id = customer["id"]

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

    # TOTAL ITEMS

    total_items = sum(
        item["quantity"]
        for item in selected_items
    )

    # CREATE ORDER

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

    # SAVE EACH PRODUCT

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

        # Automatically reduce stock

        cursor.execute("""
            UPDATE stock
            SET stock_quantity = stock_quantity - ?
            WHERE id = ?
        """, (
            item["quantity"],
            item["stock_id"]
        ))

    connection.commit()
    connection.close()

    return redirect(url_for("customer_order_page"))


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/")
def login_page():

    if user_logged_in():
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["POST"])
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

        return redirect(url_for("dashboard"))

    return render_template(
        "login.html",
        error="Invalid username, password or role."
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not user_logged_in():
        return redirect(url_for("login_page"))

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
    """)
    total_customers = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
    """)
    total_orders = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Pending'
    """)
    pending_orders = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE payment_status = 'Unpaid'
    """)
    unpaid_orders = cursor.fetchone()[0]

    cursor.execute("""
        SELECT
            orders.id,
            customers.customer_name,
            orders.pickup_date,
            orders.items,
            orders.payment_status,
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
        unpaid_orders=unpaid_orders,
        recent_orders=recent_orders
    )


# =========================================================
# CUSTOMERS
# =========================================================

@app.route("/customers")
def customers():

    if not user_logged_in():
        return redirect(url_for("login_page"))

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
        return redirect(url_for("login_page"))

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM orders
        WHERE customer_id = ?
    """, (customer_id,))

    customer_orders = cursor.fetchall()

    for order in customer_orders:

        cursor.execute("""
            DELETE FROM order_items
            WHERE order_id = ?
        """, (order["id"],))

    cursor.execute("""
        DELETE FROM orders
        WHERE customer_id = ?
    """, (customer_id,))

    cursor.execute("""
        DELETE FROM customers
        WHERE id = ?
    """, (customer_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("customers"))


# =========================================================
# ORDERS
# =========================================================

@app.route("/orders")
def orders():

    if not user_logged_in():
        return redirect(url_for("login_page"))

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
        ON orders.customer_id = customers.id

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

        values.append(f"%{search}%")
        values.append(f"%{search}%")

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

    cursor.execute(query, values)

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
            ON order_items.stock_id = stock.id

            WHERE order_items.order_id = ?
        """, (order["id"],))

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
# STOCK PAGE
# =========================================================

@app.route("/stock")
def stock():

    if not user_logged_in():
        return redirect(url_for("login_page"))

    stock_filter = request.args.get(
        "filter",
        "all"
    )

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM stock
        ORDER BY stock_quantity ASC, item_name ASC
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

        all_stock_items.append(stock_item)

        if quantity < 5:
            low_stock_items.append(stock_item)

    # FILTER STOCK LIST

    if stock_filter == "in":

        stock_items = [
            item for item in all_stock_items
            if item["status_key"] == "in"
        ]

    elif stock_filter == "running":

        stock_items = [
            item for item in all_stock_items
            if item["status_key"] == "running"
        ]

    elif stock_filter == "low":

        stock_items = [
            item for item in all_stock_items
            if item["status_key"] == "low"
        ]

    elif stock_filter == "out":

        stock_items = [
            item for item in all_stock_items
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

@app.route("/stock/add", methods=["POST"])
def add_stock():

    if not user_logged_in():
        return redirect(url_for("login_page"))

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

        return redirect(url_for("stock"))

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO stock (
            item_name,
            brand,
            stock_quantity,
            price
        )
        VALUES (?, ?, ?, ?)
    """, (
        item_name,
        brand,
        stock_quantity,
        price
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("stock"))


# =========================================================
# REFILL STOCK
# =========================================================

@app.route(
    "/stock/refill/<int:stock_id>",
    methods=["POST"]
)
def refill_stock(stock_id):

    if not user_logged_in():
        return redirect(url_for("login_page"))

    refill_quantity = request.form.get(
        "refill_quantity",
        ""
    )

    try:
        refill_quantity = int(refill_quantity)

    except ValueError:
        return redirect(url_for("stock"))

    if refill_quantity <= 0:
        return redirect(url_for("stock"))

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE stock
        SET stock_quantity = stock_quantity + ?
        WHERE id = ?
    """, (
        refill_quantity,
        stock_id
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("stock"))


# =========================================================
# DELETE STOCK
# =========================================================

@app.route(
    "/stock/delete/<int:stock_id>",
    methods=["POST"]
)
def delete_stock(stock_id):

    if not user_logged_in():
        return redirect(url_for("login_page"))

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM stock
        WHERE id = ?
    """, (stock_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("stock"))


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login_page"))


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)