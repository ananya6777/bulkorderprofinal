from flask import render_template, redirect, url_for, session
from core import app
from database import get_database_connection
from auth_helpers import user_logged_in

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
