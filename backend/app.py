from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

try:
    from .routes.agent_routes import agent_bp
except ImportError:
    from routes.agent_routes import agent_bp


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app():
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path="",
    )
    CORS(app)

    app.register_blueprint(agent_bp, url_prefix="/api")

    @app.route('/')
    def index():
        return app.send_static_file("index.html")

    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "running",
            "message": "API-Integrated Intelligent Decision Agent",
            "frontend_served": FRONTEND_DIR.exists(),
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
