from flask import render_template
from core import app

@app.route("/")
def home():

    return render_template(
        "portal.html"
    )
