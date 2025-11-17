"""
Flask web app for Codebreaker
Full version with:
- Per-user sessions via cookies
- 3-attempt logic
- Passphrase checking
- New-passphrase setting
- Basic login/registration via Flask-Login (in-memory users)
"""

# pylint: disable=import-error

import uuid

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    g,
    redirect,
    url_for,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

# per-user in-memory state just for now (will be replaced by Mongo later)
# {
#   player_id: {
#       "attempts_left": int,
#       "last_result": None/"correct"/"incorrect",
#       "last_guess": str|None,
#       "secret_phrase": str
#   }
# }
PLAYER_STATES = {}

DEFAULT_SECRET_PHRASE = "open sesame"

# very simple in-memory users store for login
# USERS = {
#   "username": {
#       "password_hash": "...",
#   }
# }
USERS = {}


def get_or_create_state(player_id: str):
    """Fetch or initialize the player's game state."""
    if player_id not in PLAYER_STATES:
        PLAYER_STATES[player_id] = {
            "attempts_left": 3,
            "last_result": None,
            "last_guess": None,
            "secret_phrase": DEFAULT_SECRET_PHRASE,
        }
    return PLAYER_STATES[player_id]


class User(UserMixin):
    """Minimal user wrapper for Flask-Login, using username as ID."""

    def __init__(self, username: str):
        self.id = username  # Flask-Login expects .id

    @property
    def username(self):
        return self.id


def create_app():
    """Application factory for password guess web app"""
    app_instance = Flask(__name__)

    # REQUIRED for sessions / Flask-Login / flash()
    app_instance.config["SECRET_KEY"] = "dev-secret-change-me"
    # -------------------------
    # FLASK-LOGIN SETUP
    # -------------------------
    login_manager = LoginManager()
    login_manager.init_app(app_instance)
    login_manager.login_view = "login"  # endpoint name for @login_required redirects

    @login_manager.user_loader
    def load_user(username):
        """Return a User object for a given username, or None."""
        if username in USERS:
            return User(username)
        return None

    # -------------------------
    # PLAYER ID COOKIE HANDLING
    # -------------------------
    @app_instance.before_request
    def ensure_player_id():
        """Ensure each user has a persistent anonymous UUID in a cookie."""
        player_id = request.cookies.get("player_id")

        if not player_id:
            # First time this browser is seen
            player_id = str(uuid.uuid4())
            g.new_player_id = player_id  # Mark to set cookie in after_request

        g.player_id = player_id  # Store for use in routes

    @app_instance.after_request
    def set_player_cookie(response):
        """Attach player_id cookie if newly created."""
        if getattr(g, "new_player_id", None):
            response.set_cookie(
                "player_id",
                g.new_player_id,
                max_age=60 * 60 * 24 * 30,  # 30 days
                httponly=True,
                samesite="Lax",
            )
        return response

    # -------------------------
    # AUTH ROUTES
    # -------------------------
    @app_instance.route("/register", methods=["GET", "POST"])
    def register():
        """User registration: simple username + password."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Username and password are required.", "error")
                return redirect(url_for("register"))

            if username in USERS:
                flash("Username already taken.", "error")
                return redirect(url_for("register"))

            USERS[username] = {
                "password_hash": generate_password_hash(password),
            }

            user = User(username)
            login_user(user)
            flash("Account created and logged in!", "success")
            return redirect(url_for("index"))

        return render_template("register.html")

    @app_instance.route("/login", methods=["GET", "POST"])
    def login():
        """Login form."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user_record = USERS.get(username)
            if not user_record or not check_password_hash(
                user_record["password_hash"], password
            ):
                flash("Invalid username or password.", "error")
                return redirect(url_for("login"))

            user = User(username)
            login_user(user)
            flash("Logged in successfully.", "success")

            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        return render_template("login.html")

    @app_instance.route("/logout")
    @login_required
    def logout():
        """Log the current user out."""
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    # -------------------------
    # HTML ROUTES
    # -------------------------
    @app_instance.route("/")
    @login_required
    def index():
        """Render the main game page"""
        return render_template("index.html")

    @app_instance.route("/dashboard")
    @login_required
    def dashboard():
        """Render the dashboard page"""
        return render_template("dashboard.html")

    # -------------------------
    # API ROUTES (PLACEHOLDERS)
    # -------------------------
    @app_instance.route("/api/game-state", methods=["GET"])
    @login_required
    def game_state():
        """Return this player's current game state."""
        state = get_or_create_state(g.player_id)
        return jsonify(state), 200

    @app_instance.route("/api/submit-guess", methods=["POST"])
    @login_required
    def submit_guess():
        """
        Receive a guess from the frontend and apply game logic.

        Currently:
        - compares the text guess to the secret_phrase
        - tracks attempts_left per player_id
        - returns whether the guess was correct and if the user may set a new passphrase

        Later:
        - we can plug in the ML transcription so the guess comes from audio
        """
        data = request.get_json() or {}
        guess = (data.get("guess", "")).strip()

        state = get_or_create_state(g.player_id)

        # No attempts left
        if state["attempts_left"] <= 0:
            return (
                jsonify(
                    {
                        "message": "No attempts left for this passphrase.",
                        "guess": guess,
                        "attempts_left": state["attempts_left"],
                        "result": "no_attempts",
                        "match": False,
                        "can_change_passphrase": False,
                    }
                ),
                200,
            )

        # Consume one attempt
        state["attempts_left"] -= 1
        state["last_guess"] = guess

        # Check correct guess
        if guess.lower() == state["secret_phrase"].lower():
            state["last_result"] = "correct"
            return (
                jsonify(
                    {
                        "message": "You guessed it! You can now set a new passphrase.",
                        "guess": guess,
                        "attempts_left": state["attempts_left"],
                        "result": "correct",
                        "match": True,
                        "can_change_passphrase": True,
                    }
                ),
                200,
            )

        # Incorrect guess
        state["last_result"] = "incorrect"
        if state["attempts_left"] > 0:
            msg = "Incorrect guess. Try again!"
        else:
            msg = "Incorrect guess. No attempts left."

        return (
            jsonify(
                {
                    "message": msg,
                    "guess": guess,
                    "attempts_left": state["attempts_left"],
                    "result": "incorrect",
                    "match": False,
                    "can_change_passphrase": False,
                }
            ),
            200,
        )

    @app_instance.route("/api/set-passphrase", methods=["POST"])
    @login_required
    def set_passphrase():
        """Allow player to set a new secret passphrase (after a correct guess)."""
        data = request.get_json() or {}
        new_phrase = (data.get("passphrase", "")).strip()

        if not new_phrase:
            return jsonify({"error": "Passphrase cannot be empty."}), 400

        state = get_or_create_state(g.player_id)

        # Reset with new passphrase
        state["secret_phrase"] = new_phrase
        state["attempts_left"] = 3
        state["last_result"] = None
        state["last_guess"] = None

        return (
            jsonify(
                {
                    "message": "New passphrase set. You have 3 attempts.",
                    "attempts_left": state["attempts_left"],
                }
            ),
            200,
        )

    @app_instance.route("/api/reset", methods=["POST"])
    @login_required
    def reset_game():
        """Reset game state for this player."""
        PLAYER_STATES[g.player_id] = {
            "attempts_left": 3,
            "last_result": None,
            "last_guess": None,
            "secret_phrase": DEFAULT_SECRET_PHRASE,
        }
        return (
            jsonify(
                {
                    "message": "Game reset.",
                    **PLAYER_STATES[g.player_id],
                }
            ),
            200,
        )

    return app_instance


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=3000, debug=True)
