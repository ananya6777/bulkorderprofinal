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


def get_database_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date_added TEXT DEFAULT CURRENT_DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            pickup_date TEXT NOT NULL,
            items INTEGER NOT NULL,
            payment_status TEXT NOT NULL,
            order_status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    connection.commit()
    connection.close()


def user_logged_in():
    return "username" in session


@app.route("/")
def login_page():
    if user_logged_in():
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

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


@app.route("/dashboard")
def dashboard():
    if not user_logged_in():
        return redirect(url_for("login_page"))

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders")
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


@app.route("/customers")
def customers():
    if not user_logged_in():
        return redirect(url_for("login_page"))

    search = request.args.get("search", "").strip()

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

    cursor.execute("SELECT COUNT(*) FROM customers")
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


@app.route("/customers/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    if not user_logged_in():
        return redirect(url_for("login_page"))

    connection = get_database_connection()
    cursor = connection.cursor()

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


@app.route("/orders")
def orders():
    if not user_logged_in():
        return redirect(url_for("login_page"))

    search = request.args.get("search", "").strip()

    connection = get_database_connection()
    cursor = connection.cursor()

    if search:
        cursor.execute("""
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
            WHERE customers.customer_name LIKE ?
               OR customers.phone LIKE ?
            ORDER BY orders.id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        ))

    else:
        cursor.execute("""
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
            ORDER BY orders.id DESC
        """)

    order_records = cursor.fetchall()

    connection.close()

    return render_template(
        "orders.html",
        orders=order_records,
        search=search
    )


@app.route("/orders/add", methods=["POST"])
def add_order():
    if not user_logged_in():
        return redirect(url_for("login_page"))

    customer_name = request.form.get("customer_name", "").strip()
    phone = request.form.get("phone", "").strip()
    pickup_date = request.form.get("pickup_date", "")
    items = request.form.get("items", "")
    payment_status = request.form.get("payment_status", "")
    order_status = request.form.get("order_status", "")

    if not all([
        customer_name,
        phone,
        pickup_date,
        items,
        payment_status,
        order_status
    ]):
        return redirect(url_for("orders"))

    connection = get_database_connection()
    cursor = connection.cursor()

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

    cursor.execute("""
        INSERT INTO orders (
            customer_id,
            pickup_date,
            items,
            payment_status,
            order_status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        customer_id,
        pickup_date,
        items,
        payment_status,
        order_status
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("orders"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


if __name__ == "__main__":
    create_database()
    app.run(debug=True)