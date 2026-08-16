from flask import render_template, request, redirect, url_for, session
from core import app
from config import USERS
from database import get_database_connection, add_history
from auth_helpers import user_logged_in

@app.route("/staff-login")
def staff_login_page():

    if user_logged_in():

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "staff_login.html"
    )

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
