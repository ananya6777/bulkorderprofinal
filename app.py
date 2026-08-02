from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "change-this-to-a-real-secret-key"


# Demo users
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


# ---------------- LOGIN PAGE ----------------

@app.route("/", methods=["GET"])
def login_page():

    if "username" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ---------------- LOGIN ----------------

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
        error="Invalid username, password, or role."
    )


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login_page"))

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"]
    )


# ---------------- ORDERS ----------------

@app.route("/orders")
def orders():

    if "username" not in session:
        return redirect(url_for("login_page"))

    return render_template("orders.html")


# ---------------- CUSTOMERS ----------------

@app.route("/customers")
def customers():

    if "username" not in session:
        return redirect(url_for("login_page"))

    return render_template("customers.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login_page"))


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)