from flask import render_template, request, redirect, url_for, session
from core import app
from database import get_database_connection, add_history
from auth_helpers import user_logged_in

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
