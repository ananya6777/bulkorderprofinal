from flask import render_template, request, redirect, url_for, session
from core import app
from database import get_database_connection, add_history
from auth_helpers import user_logged_in


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
            category ASC,
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

            "category": item["category"],

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

    category = request.form.get(
        "category",
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
        category,
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

            category,

            stock_quantity,

            price,

            is_deleted

        )
        VALUES (?, ?, ?, ?, ?, 0)
    """, (
        item_name,
        brand,
        category,
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
            f'Added "{item_name}" '
            f'({category}) '
            f'with {stock_quantity} units.'
        ),
        stock_id=stock_id
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("stock")
    )

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
            category,
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
            f'({stock_item["category"]}) '
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
            category,
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
            f'({stock_item["category"]}).'
        ),
        action_type="restore_stock",
        stock_id=stock_id
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("stock")
    )