from flask import render_template, request, redirect, url_for, session
from core import app
from database import get_database_connection, get_settings, add_history
from auth_helpers import user_logged_in

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

@app.route(
    "/settings/update",
    methods=["POST"]
)
def update_settings():
    if not user_logged_in():
        return redirect(url_for("staff_login_page"))

    if session.get("role") != "manager":
        return redirect(url_for("dashboard"))

    business_name = request.form.get("business_name", "").strip()
    store_phone = request.form.get("store_phone", "").strip()
    store_email = request.form.get("store_email", "").strip()
    pickup_address = request.form.get("pickup_address", "").strip()
    weekday_hours = request.form.get("weekday_hours", "").strip()
    saturday_hours = request.form.get("saturday_hours", "").strip()
    sunday_hours = request.form.get("sunday_hours", "").strip()

    if not business_name:
        business_name = "BulkOrder Pro"

    connection = get_database_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE settings
        SET business_name = ?, store_phone = ?, store_email = ?,
            pickup_address = ?, weekday_hours = ?, saturday_hours = ?,
            sunday_hours = ?
        WHERE id = 1
    """, (
        business_name, store_phone, store_email, pickup_address,
        weekday_hours, saturday_hours, sunday_hours
    ))

    add_history(
        connection, session["username"], session["role"].title(),
        "Settings", "Updated business settings."
    )
    connection.commit()
    connection.close()
    return redirect(url_for("settings"))
