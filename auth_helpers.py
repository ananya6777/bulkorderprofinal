from flask import session


def user_logged_in():
    return "username" in session


def customer_logged_in():
    return "customer_id" in session
