"""Flask web app for Codebreaker"""

# pylint: disable=import-error

from flask import Flask, render_template, request, jsonify

# simple in-memory state just for now (will be replaced by Mongo later)
GAME_STATE = {
    "attempts_left": 3,
    "last_result": None,   # e.g. "pending", "correct", "incorrect"
    "last_guess": None,
}

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


# API ROUTES (PLACEHOLDERS)

    @app_instance.route("/api/submit-guess", methods=["POST"])
    def submit_guess():
        """
        Receive a guess from the frontend.
        For now, this is just a placeholder that echoes the guess
        and pretends everything is 'pending'.

        Later:
        - store guess + metadata in MongoDB
        - ML client will read/process and update the result
        """
        data = request.get_json() or {}
        guess = data.get("guess", "")

        GAME_STATE["last_guess"] = guess
        GAME_STATE["last_result"] = "pending"
        # (optional) decrement attempts here just for testing
        if GAME_STATE["attempts_left"] > 0:
            GAME_STATE["attempts_left"] -= 1

        return jsonify(
            {
                "message": "guess received (placeholder)",
                "guess": guess,
                "attempts_left": GAME_STATE["attempts_left"],
                "result": GAME_STATE["last_result"],
            }
        ), 200

    @app_instance.route("/api/game-state", methods=["GET"])
    def game_state():
        """
        Return current game info for the frontend.

        Later:
        - this can read from MongoDB instead of in-memory GAME_STATE
        """
        return jsonify(GAME_STATE), 200

    @app_instance.route("/api/reset", methods=["POST"])
    def reset_game():
        """
        Reset the game state. Useful for testing the UI.

        Later:
        - might clear or reset documents in Mongo instead.
        """
        GAME_STATE["attempts_left"] = 3
        GAME_STATE["last_result"] = None
        GAME_STATE["last_guess"] = None

        return jsonify({"message": "game reset", **GAME_STATE}), 200


    return app_instance


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=3000, debug=True)
