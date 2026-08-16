from flask import render_template, request, redirect, url_for, session
from core import app
from database import get_database_connection, add_history
from auth_helpers import user_logged_in

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
