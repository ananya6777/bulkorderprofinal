from core import app
from database import create_database

# Import route modules so Flask registers every @app.route.
import portal_routes
import customer_routes
import staff_auth_routes
import dashboard_routes
import customer_management_routes
import order_routes
import stock_routes
import history_routes
import settings_routes


if __name__ == "__main__":
    create_database()
    app.run(debug=True)
