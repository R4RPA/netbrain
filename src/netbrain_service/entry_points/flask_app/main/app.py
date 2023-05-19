from flask import Flask, Blueprint
from src.netbrain_service.entry_points.flask_app.main.api import incoming_payload  # Import the routes

bp = Blueprint('main', __name__)
bp.add_url_rule("/api/v1/request", view_func=incoming_payload, methods=["POST"])  # Add the route to the blueprint

app = Flask(__name__)
app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(debug=True, port=5050)
