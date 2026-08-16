import re
from datetime import date, timedelta
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from core import app
from database import get_database_connection, add_history
from auth_helpers import customer_logged_in

def get_customer_products():

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            item_name,
            brand,
            stock_quantity,
            price

        FROM stock

        WHERE is_deleted = 0

        ORDER BY item_name
    """)

    stock_records = cursor.fetchall()

    customer_products = []


    for item in stock_records:

        if item["stock_quantity"] <= 0:

            customer_status = "Out of Stock"
            is_available = False

        else:

            customer_status = "Available"
            is_available = True


        customer_products.append({

            "id": item["id"],

            "item_name": item["item_name"],

            "brand": item["brand"],

            "price": item["price"],

            "customer_status": customer_status,

            "is_available": is_available,

            "max_quantity": item["stock_quantity"]

        })


    connection.close()

    return customer_products

def get_logged_in_customer():

    if not customer_logged_in():

        return None


    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            customer_name,
            phone

        FROM customers

        WHERE id = ?
    """, (
        session["customer_id"],
    ))

    customer = cursor.fetchone()

    connection.close()

    return customer

@app.route("/customer-register")
def customer_register_page():

    if customer_logged_in():

        return redirect(
            url_for("customer_order_page")
        )


    return render_template(
        "customer_register.html"
    )

@app.route(
    "/customer-register",
    methods=["POST"]
)
def customer_register():

    first_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    last_name = request.form.get(
        "last_name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    # ---------------- REQUIRED FIELDS ----------------

    if not all([
        first_name,
        last_name,
        phone,
        username,
        password,
        confirm_password
    ]):

        return render_template(
            "customer_register.html",
            error="Please complete every field."
        )


    # ---------------- FIRST NAME ----------------

    if not re.fullmatch(
        r"[A-Za-z]+",
        first_name
    ):

        return render_template(
            "customer_register.html",
            error="First name can only contain letters."
        )


    # ---------------- LAST NAME / INITIAL ----------------
    #
    # Allows:
    # D
    # D.
    # Doe
    # Smith

    if not re.fullmatch(
        r"[A-Za-z]+\.?",
        last_name
    ):

        return render_template(
            "customer_register.html",
            error=(
                "Last name or initial can only "
                "contain letters."
            )
        )


    # ---------------- PHONE NUMBER ----------------
    #
    # Remove spaces first:
    # 0412 345 678 becomes 0412345678

    phone = re.sub(
        r"\s+",
        "",
        phone
    )


    # Australian mobile:
    # Starts with 04
    # Exactly 10 digits

    if not re.fullmatch(
        r"04\d{8}",
        phone
    ):

        return render_template(
            "customer_register.html",
            error=(
                "Please enter a valid Australian "
                "mobile number starting with 04."
            )
        )


    # ---------------- USERNAME ----------------

    if len(username) < 5:

        return render_template(
            "customer_register.html",
            error=(
                "Username must contain "
                "at least 5 characters."
            )
        )


    if " " in username:

        return render_template(
            "customer_register.html",
            error="Username cannot contain spaces."
        )


    # ---------------- PASSWORD ----------------
    #
    # AT LEAST 8 characters
    # Uppercase
    # Lowercase
    # Number
    # Special character

    if len(password) < 8:

        return render_template(
            "customer_register.html",
            error="Password must be at least 8 characters long."
        )


    if not re.search(
        r"[A-Z]",
        password
    ):

        return render_template(
            "customer_register.html",
            error=(
                "Password must contain "
                "an uppercase letter."
            )
        )


    if not re.search(
        r"[a-z]",
        password
    ):

        return render_template(
            "customer_register.html",
            error=(
                "Password must contain "
                "a lowercase letter."
            )
        )


    if not re.search(
        r"\d",
        password
    ):

        return render_template(
            "customer_register.html",
            error=(
                "Password must contain "
                "a number."
            )
        )


    if not re.search(
        r"[^A-Za-z0-9]",
        password
    ):

        return render_template(
            "customer_register.html",
            error=(
                "Password must contain "
                "a special character."
            )
        )


    # ---------------- CONFIRM PASSWORD ----------------

    if password != confirm_password:

        return render_template(
            "customer_register.html",
            error="Passwords do not match."
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    # ---------------- USERNAME ALREADY EXISTS ----------------

    cursor.execute("""
        SELECT id
        FROM customer_accounts
        WHERE username = ?
    """, (
        username,
    ))

    existing_username = cursor.fetchone()


    if existing_username:

        connection.close()

        return render_template(
            "customer_register.html",
            error="That username is already being used."
        )


    # ---------------- PHONE ALREADY EXISTS ----------------

    cursor.execute("""
        SELECT id
        FROM customers
        WHERE phone = ?
    """, (
        phone,
    ))

    existing_customer = cursor.fetchone()


    if existing_customer:

        customer_id = existing_customer["id"]


        cursor.execute("""
            SELECT id
            FROM customer_accounts
            WHERE customer_id = ?
        """, (
            customer_id,
        ))

        existing_account = cursor.fetchone()


        if existing_account:

            connection.close()

            return render_template(
                "customer_register.html",
                error=(
                    "An account already exists "
                    "for this phone number."
                )
            )


        cursor.execute("""
            UPDATE customers

            SET
                customer_name = ?,
                last_name = ?

            WHERE id = ?
        """, (
            first_name,
            last_name,
            customer_id
        ))


    else:

        cursor.execute("""
            INSERT INTO customers (
                customer_name,
                last_name,
                phone
            )

            VALUES (?, ?, ?)
        """, (
            first_name,
            last_name,
            phone
        ))

        customer_id = cursor.lastrowid


    password_hash = generate_password_hash(
        password
    )


    cursor.execute("""
        INSERT INTO customer_accounts (
            customer_id,
            username,
            password_hash
        )

        VALUES (?, ?, ?)
    """, (
        customer_id,
        username,
        password_hash
    ))


    display_name = (
        f"{first_name} {last_name}"
    )


    add_history(
        connection,
        username,
        "Customer",
        "Customers",
        (
            f'Customer account registered '
            f'for "{display_name}".'
        )
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("customer_login_page")
    )

@app.route("/customer-login")
def customer_login_page():

    if customer_logged_in():

        return redirect(
            url_for("customer_order_page")
        )


    return render_template(
        "customer_login.html"
    )

@app.route(
    "/customer-login",
    methods=["POST"]
)
def customer_login():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    connection = get_database_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            customer_accounts.customer_id,
            customer_accounts.username,
            customer_accounts.password_hash,
            customers.customer_name,
            customers.last_name,
            customers.phone
        FROM customer_accounts
        JOIN customers
            ON customer_accounts.customer_id = customers.id
        WHERE customer_accounts.username = ?
    """, (username,))

    customer = cursor.fetchone()

    if customer and check_password_hash(customer["password_hash"], password):
        session["customer_id"] = customer["customer_id"]
        session["customer_username"] = customer["username"]

        display_name = customer["customer_name"]
        if customer["last_name"]:
            display_name += f" {customer['last_name']}"

        session["customer_name"] = display_name

        add_history(
            connection,
            customer["username"],
            "Customer",
            "Login",
            "Customer logged in."
        )

        connection.commit()
        connection.close()

        return redirect(url_for("customer_order_page"))

    connection.close()

    return render_template(
        "customer_login.html",
        error="Invalid username or password."
    )

@app.route("/customer-logout")
def customer_logout():

    session.pop(
        "customer_id",
        None
    )

    session.pop(
        "customer_username",
        None
    )

    session.pop(
        "customer_name",
        None
    )


    return redirect(
        url_for("customer_login_page")
    )

@app.route("/customer-order")
def customer_order_page():

    if not customer_logged_in():

        return redirect(
            url_for("customer_login_page")
        )

    products = get_customer_products()

    customer = get_logged_in_customer()

    minimum_pickup_date = (
        date.today() + timedelta(days=3)
    ).isoformat()

    return render_template(
        "customer_order.html",
        stock_items=products,
        customer=customer,
        minimum_pickup_date=minimum_pickup_date
    )

@app.route(
    "/customer-order/submit",
    methods=["POST"]
)
def submit_customer_order():

    if not customer_logged_in():

        return redirect(
            url_for("customer_login_page")
        )


    customer_id = session["customer_id"]

    pickup_date = request.form.get(
        "pickup_date",
        ""
    )


    if not pickup_date:

        return render_template(
            "customer_order.html",
            stock_items=get_customer_products(),
            customer=get_logged_in_customer(),
            minimum_pickup_date=(
                date.today() + timedelta(days=3)
            ).isoformat(),
            error="Please select a pickup date."
        )


    minimum_pickup_date = (
        date.today() + timedelta(days=3)
    )


    try:

        selected_pickup_date = (
            date.fromisoformat(pickup_date)
        )

    except ValueError:

        return render_template(
            "customer_order.html",
            stock_items=get_customer_products(),
            customer=get_logged_in_customer(),
            minimum_pickup_date=minimum_pickup_date.isoformat(),
            error="Please select a valid pickup date."
        )


    if selected_pickup_date < minimum_pickup_date:

        return render_template(
            "customer_order.html",
            stock_items=get_customer_products(),
            customer=get_logged_in_customer(),
            minimum_pickup_date=minimum_pickup_date.isoformat(),
            error=(
                "Pickup must be at least "
                "3 days after the order is placed."
            )
        )



    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM stock

        WHERE is_deleted = 0

        ORDER BY item_name
    """)


    stock_items = cursor.fetchall()

    selected_items = []


    for item in stock_items:

        if item["stock_quantity"] <= 0:

            continue


        quantity_text = request.form.get(
            f"quantity_{item['id']}",
            "0"
        )


        try:

            quantity = int(quantity_text)

        except ValueError:

            quantity = 0


        if quantity < 0:

            quantity = 0


        if quantity > 0:

            if quantity > item["stock_quantity"]:

                connection.close()

                return render_template(
                    "customer_order.html",
                    stock_items=get_customer_products(),
                    customer=get_logged_in_customer(),
                    minimum_pickup_date=minimum_pickup_date.isoformat(),
                    error=(
                        f"The requested quantity for "
                        f"{item['item_name']} "
                        f"is unavailable. "
                        f"Please choose a smaller quantity."
                    )
                )


            selected_items.append({
                "stock_id": item["id"],
                "quantity": quantity
            })


    if not selected_items:

        connection.close()

        return render_template(
            "customer_order.html",
            stock_items=get_customer_products(),
            customer=get_logged_in_customer(),
            minimum_pickup_date=minimum_pickup_date.isoformat(),
            error=(
                "Please enter a quantity "
                "for at least one available product."
            )
        )


    total_items = sum(
        item["quantity"]
        for item in selected_items
    )


    # Create order

    cursor.execute("""
        INSERT INTO orders (
            customer_id,
            stock_id,
            pickup_date,
            items,
            payment_status,
            order_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        None,
        pickup_date,
        total_items,
        "Unpaid",
        "Pending"
    ))


    order_id = cursor.lastrowid


    # Save products

    for item in selected_items:

        cursor.execute("""
            INSERT INTO order_items (
                order_id,
                stock_id,
                quantity
            )
            VALUES (?, ?, ?)
        """, (
            order_id,
            item["stock_id"],
            item["quantity"]
        ))


        # Reduce stock automatically

        cursor.execute("""
            UPDATE stock
            SET stock_quantity = stock_quantity - ?
            WHERE id = ?
        """, (
            item["quantity"],
            item["stock_id"]
        ))


    # Record order in history

    add_history(
        connection,
        session["customer_username"],
        "Customer",
        "Orders",
        f"Placed Order #{order_id} with {total_items} item(s).",
        order_id=order_id
    )


    connection.commit()
    connection.close()


    return redirect(
        url_for("customer_my_orders")
    )

@app.route("/customer-orders")
def customer_my_orders():

    if not customer_logged_in():

        return redirect(
            url_for("customer_login_page")
        )


    connection = get_database_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            id,
            pickup_date,
            items,
            payment_status,
            order_status

        FROM orders

        WHERE customer_id = ?

        ORDER BY id DESC
    """, (
        session["customer_id"],
    ))


    order_records = cursor.fetchall()

    customer_orders = []


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


        customer_orders.append({

            "id": order["id"],

            "pickup_date": order["pickup_date"],

            "items": order["items"],

            "payment_status": order["payment_status"],

            "order_status": order["order_status"],

            "products": products

        })


    connection.close()


    return render_template(
        "customer_orders.html",
        orders=customer_orders
    )
