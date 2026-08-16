from flask import render_template, request, redirect, url_for, session
from core import app
from database import get_database_connection, add_history
from auth_helpers import user_logged_in

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
