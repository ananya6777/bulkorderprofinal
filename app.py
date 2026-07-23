from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "change-this-to-a-real-secret-key"

# Demo user store — swap this for a real database lookup
USERS = {
    "manager": {"password": "manager123", "role": "manager"},
    "staff":   {"password": "staff123",   "role": "staff"},
}

@app.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role     = request.form.get("role", "")

    user = USERS.get(username)

    if user and user["password"] == password and user["role"] == role:
        session["username"] = username
        session["role"] = role
        return redirect(url_for("dashboard"))

    return render_template("login.html", error="Invalid username, password, or role.")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login_page"))
    return f"Welcome, {session['username']} ({session['role']})!"

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

if __name__ == "__main__":
    app.run(debug=True)