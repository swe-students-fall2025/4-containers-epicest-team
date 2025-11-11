"""Flask web app for Codebreaker"""

# pylint: disable=import-error

from flask import Flask, render_template


def create_app():
    """Application factory for password guess web app"""
    app_instance = Flask(__name__)

    @app_instance.route("/")
    def index():
        """Render the main game page"""
        return render_template("index.html")

    @app_instance.route("/dashboard")
    def dashboard():
        """Render the dashboard page"""
        return render_template("dashboard.html")

    return app_instance


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=5000, debug=True)
