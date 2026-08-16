BulkOrder Pro - split Python structure

HOW TO USE
1. Back up your current app.py.
2. Copy every .py file in this folder into the SAME project folder that contains templates/, static/, and bulk_orderpro.db.
3. Do NOT move templates, static, or bulk_orderpro.db.
4. Run: python app.py

Files:
- app.py: starts Flask and loads routes
- core.py: creates the Flask app
- config.py: database filename and fixed staff/manager accounts
- database.py: database tables and shared database helpers
- auth_helpers.py: login checks
- customer_routes.py: customer registration/login/orders
- staff_auth_routes.py: staff/manager login/logout
- dashboard_routes.py: dashboard
- customer_management_routes.py: staff customer list/delete
- order_routes.py: staff orders and status updates
- stock_routes.py: stock management
- history_routes.py: history, restore, revert
- settings_routes.py: manager settings

The existing endpoint names are preserved, so your current HTML url_for(...) calls should continue working.
