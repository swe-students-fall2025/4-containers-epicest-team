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

import io
import uuid
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
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

import pymongo

PARENT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = PARENT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")
SECRET_KEY = os.getenv("SECRET_KEY")
ML_CLIENT_URL = os.getenv("ML_CLIENT_URL")

mongo_client = None
db = None

DEFAULT_SECRET_PHRASE = "Open Sesame"
DEFAULT_SECRET_HINT = "A classic phrase to unlock a secret"


def init_mongo():
    """Initialize MongoDB connection"""
    if MONGO_URI and MONGO_DB and MONGO_USER and MONGO_PASS:
        try:
            mongo_client = pymongo.MongoClient(
                MONGO_URI, username=MONGO_USER, password=MONGO_PASS
            )
            db = mongo_client[MONGO_DB]
            print(f"Connected to MongoDB: {MONGO_DB}")
            return mongo_client, db
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            return None, None
    else:
        print("Missing MongoDB connection parameters")
        return None, None


def get_active_secret(db_connection):
    """Get the current active secret."""
    if db_connection is None:
        return None

    try:
        # Find a secret that hasn't been solved yet
        active_secret = db_connection.secrets.find_one(
            {"solved_at": None}, sort=[("created_at", pymongo.ASCENDING)]
        )
        return active_secret
    except Exception as e:
        print(f"Error getting active secret: {e}")
        return None


def create_default_secret(db_connection):
    """Create a default secret if no active secret exists."""
    if db_connection is None:
        return None

    try:
        # Check if any active secrets exist
        active_secret = db_connection.secrets.find_one({"solved_at": None})
        if active_secret is None:
            # No active secret found, create default one
            default_secret = {
                "secret_id": str(uuid.uuid4()),
                "secret_phrase": DEFAULT_SECRET_PHRASE,
                "hint": DEFAULT_SECRET_HINT,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "wrong_guesses": 0,
                "solved_at": None,
            }
            db_connection.secrets.insert_one(default_secret)
            print("Created default secret")
            return default_secret
        return active_secret
    except Exception as e:
        print(f"Error creating default secret: {e}")
        return None


def mark_secret_solved(db_connection, secret_id):
    """Mark a secret as solved."""
    if db_connection is None:
        return False

    try:
        db_connection.secrets.update_one(
            {"secret_id": secret_id},
            {"$set": {"solved_at": datetime.now(timezone.utc).isoformat()}},
        )
        return True
    except Exception as e:
        print(f"Error marking secret as solved: {e}")
        return False


def increment_wrong_guesses(db_connection, secret_id):
    """Increment the wrong guess count for a secret."""
    if db_connection is None:
        return False

    try:
        db_connection.secrets.update_one(
            {"secret_id": secret_id}, {"$inc": {"wrong_guesses": 1}}
        )
        return True
    except Exception as e:
        print(f"Error incrementing wrong guesses: {e}")
        return False


def create_new_secret(db_connection, secret_phrase, hint, creator_uuid):
    """Create a new secret."""
    if db_connection is None:
        return None

    try:
        new_secret = {
            "secret_id": str(uuid.uuid4()),
            "secret_phrase": secret_phrase,
            "hint": hint,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": creator_uuid,
            "wrong_guesses": 0,
            "solved_at": None,
        }
        db_connection.secrets.insert_one(new_secret)
        return new_secret
    except Exception as e:
        print(f"Error creating new secret: {e}")
        return None


def get_or_create_state(user_uuid: str, db_connection, active_secret):
    """Fetch or initialize the player's game state from MongoDB."""
    if db_connection is None or active_secret is None:
        # Fallback to default state if DB is unavailable
        return {
            "attempts_left": 3,
            "last_result": None,
            "last_guess": None,
            "current_secret_id": None,
            "can_create_secret": False,
            "locked_until": None,
        }

    current_secret_id = active_secret.get("secret_id")
    now = datetime.now(timezone.utc)

    try:
        game_state = db_connection.game_states.find_one({"user_uuid": user_uuid})

        if game_state:
            # Check if the secret has changed since user last played
            stored_secret_id = game_state.get("current_secret_id")

            if stored_secret_id != current_secret_id:
                reset_state = {
                    "current_secret_id": current_secret_id,
                    "attempts_left": 3,
                    "last_result": None,
                    "last_guess": None,
                    "can_create_secret": False,
                    "locked_until": None,
                    "updated_at": now.isoformat(),
                }
                db_connection.game_states.update_one(
                    {"user_uuid": user_uuid}, {"$set": reset_state}
                )
                return {
                    "attempts_left": 3,
                    "last_result": None,
                    "last_guess": None,
                    "current_secret_id": current_secret_id,
                    "can_create_secret": False,
                    "locked_until": None,
                }

            # Same secret - check if user is locked out (< 24 hours since guesses ran out)
            locked_until_str = game_state.get("locked_until")
            attempts_left = game_state.get("attempts_left", 3)

            if attempts_left == 0 and locked_until_str:
                # User was locked out, check if 24 hours have passed since then
                try:
                    locked_until = datetime.fromisoformat(locked_until_str)
                    if now >= locked_until:
                        # 24 hours have passed, restore attempts
                        restore_state = {
                            "attempts_left": 3,
                            "locked_until": None,
                            "last_result": None,
                            "last_guess": None,
                            "updated_at": now.isoformat(),
                        }
                        db_connection.game_states.update_one(
                            {"user_uuid": user_uuid}, {"$set": restore_state}
                        )
                        return {
                            "attempts_left": 3,
                            "last_result": None,
                            "last_guess": None,
                            "current_secret_id": current_secret_id,
                            "can_create_secret": game_state.get(
                                "can_create_secret", False
                            ),
                            "locked_until": None,
                        }
                except (ValueError, TypeError):
                    # Invalid timestamp, ignore and continue
                    pass

            # Return existing state
            return {
                "attempts_left": attempts_left,
                "last_result": game_state.get("last_result"),
                "last_guess": game_state.get("last_guess"),
                "current_secret_id": current_secret_id,
                "can_create_secret": game_state.get("can_create_secret", False),
                "locked_until": locked_until_str,
            }
        else:
            # Create new game state
            new_state = {
                "user_uuid": user_uuid,
                "current_secret_id": current_secret_id,
                "attempts_left": 3,
                "last_result": None,
                "last_guess": None,
                "can_create_secret": False,
                "locked_until": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            db_connection.game_states.insert_one(new_state)

            # Create index on user_uuid for faster lookups
            db_connection.game_states.create_index("user_uuid", unique=True)

            return {
                "attempts_left": 3,
                "last_result": None,
                "last_guess": None,
                "current_secret_id": current_secret_id,
                "can_create_secret": False,
                "locked_until": None,
            }
    except Exception as e:
        print(f"Error accessing game state: {e}")
        # Return default state on error
        return {
            "attempts_left": 3,
            "last_result": None,
            "last_guess": None,
            "current_secret_id": current_secret_id,
            "can_create_secret": False,
            "locked_until": None,
        }


def update_game_state(user_uuid: str, db_connection, state_updates: dict):
    """Update game state in MongoDB."""
    if db_connection is None:
        return False

    try:
        state_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        db_connection.game_states.update_one(
            {"user_uuid": user_uuid}, {"$set": state_updates}, upsert=True
        )
        return True
    except Exception as e:
        print(f"Error updating game state: {e}")
        return False


class User(UserMixin):
    """Minimal user wrapper for Flask-Login, using username as ID."""

    def __init__(self, username: str, user_uuid: str = None):
        self.id = username
        self.user_uuid = user_uuid

    @property
    def username(self):
        return self.id


def create_app():
    """Application factory for password guess web app"""
    app_instance = Flask(__name__)

    # Add cache-busting version (automatic)
    import time

    @app_instance.context_processor
    def inject_version():
        return {"version": int(time.time())}

    # Flask login setup
    app_instance.config["SECRET_KEY"] = SECRET_KEY
    login_manager = LoginManager()
    login_manager.init_app(app_instance)
    login_manager.login_view = "login"

    # initialize mongo
    _mongo_client, db = init_mongo()

    # Ensure there's an active secret
    if db is not None:
        create_default_secret(db)

    @login_manager.user_loader
    def load_user(username):
        """Return a User object for a given username, or None."""
        if db is not None:
            try:
                user_doc = db.users.find_one({"username": username})
                if user_doc:
                    user_uuid = user_doc.get("user_uuid")
                    return User(username, user_uuid=user_uuid)
            except Exception as e:
                print(f"Error loading user from database: {e}")

        return None

    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access."""
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for("login", next=request.url))

    # -------------------------
    # AUTH ROUTES
    # -------------------------

    @app_instance.route("/api/upload-audio", methods=["POST"])
    @login_required
    def upload_audio():
        """
        Accept an audio file from the browser, run speech-to-text,
        and return the recognized text.

        Expected form field name: 'audio_file'
        """
        try:
            if "audio_file" not in request.files:
                return jsonify({"error": "No audio file uploaded."}), 400

            file_storage = request.files["audio_file"]

            if not file_storage or file_storage.filename == "":
                return jsonify({"error": "Empty audio file."}), 400

            # Reject non-audio files
            if not file_storage.mimetype.startswith("audio/"):
                return jsonify({"error": "Invalid file type"}), 400

            # Call the transcription helper
            recognized_text = transcribe_audio(file_storage)

            # Optional: basic sanity check
            if not recognized_text:
                return jsonify({"error": "Transcription failed."}), 500

            return jsonify({"recognized_text": recognized_text}), 200
        except Exception as e:
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    @app_instance.route("/register", methods=["GET", "POST"])
    def register():
        """User registration: simple username + password."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Username and password are required.", "error")
                return redirect(url_for("register"))

            if not username.replace("_", "").isalnum():
                flash(
                    "Username can only contain letters, numbers, and underscores.",
                    "error",
                )
                return redirect(url_for("register"))

            # Minimum password length for security
            if len(password) < 6:
                flash("Password must be at least 6 characters long.", "error")
                return redirect(url_for("register"))

            if db is not None:
                try:
                    existing_user = db.users.find_one({"username": username})
                    if existing_user:
                        flash("Username already taken.", "error")
                        return redirect(url_for("register"))

                    # Create new user in MongoDB with hashed password and UUID
                    user_uuid = str(uuid.uuid4())
                    user_doc = {
                        "username": username,
                        "password_hash": generate_password_hash(
                            password, method="pbkdf2:sha256"
                        ),
                        "user_uuid": user_uuid,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    db.users.insert_one(user_doc)

                    # Create unique index on username to prevent duplicates
                    db.users.create_index("username", unique=True)

                    user = User(username, user_uuid=user_uuid)
                    login_user(user)
                    flash("Account created and logged in!", "success")
                    return redirect(url_for("index"))

                except pymongo.errors.DuplicateKeyError:
                    flash("Username already taken.", "error")
                    return redirect(url_for("register"))
                except Exception as e:
                    print(f"Error creating user: {e}")
                    flash("An error occurred. Please try again.", "error")
                    return redirect(url_for("register"))
            else:
                flash("Database not available. Please try again later.", "error")
                return redirect(url_for("register"))

        return render_template("register.html")

    @app_instance.route("/login", methods=["GET", "POST"])
    def login():
        """Login form."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Username and password are required.", "error")
                return redirect(url_for("login"))

            if db is not None:
                try:
                    user_doc = db.users.find_one({"username": username})
                    if user_doc and check_password_hash(
                        user_doc["password_hash"], password
                    ):
                        user_uuid = user_doc.get("user_uuid")
                        user = User(username, user_uuid=user_uuid)
                        login_user(user)
                        flash("Logged in successfully.", "success")
                        next_page = request.args.get("next")
                        return redirect(next_page or url_for("index"))
                except Exception as e:
                    print(f"Error during login: {e}")
                    flash("An error occurred. Please try again.", "error")
                    return redirect(url_for("login"))

            # Authentication failed
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

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
    # API ROUTES
    # -------------------------
    @app_instance.route("/api/game-state", methods=["GET"])
    @login_required
    def game_state():
        """Return this player's current game state."""
        active_secret = get_active_secret(db)

        # If no active secret exists, create the default one
        if active_secret is None:
            active_secret = create_default_secret(db)

        if active_secret is None:
            return jsonify({"error": "No active secret available"}), 503

        state = get_or_create_state(current_user.user_uuid, db, active_secret)

        response = {
            **state,
            "hint": active_secret.get("hint", "No hint available"),
            "secret_id": active_secret.get("secret_id"),
        }

        return jsonify(response), 200

    @app_instance.route("/api/submit-guess", methods=["POST"])
    @login_required
    def submit_guess():
        """
        Receive a guess from the frontend and apply game logic.

        When correct:
        - Mark secret as solved
        - Give winner permission to create new secret
        """
        data = request.get_json() or {}
        guess = (data.get("guess", "")).strip()

        active_secret = get_active_secret(db)

        if active_secret is None:
            return jsonify({"error": "No active secret available"}), 503

        secret_id = active_secret.get("secret_id")
        secret_phrase = active_secret.get("secret_phrase")

        state = get_or_create_state(current_user.user_uuid, db, active_secret)

        # No attempts left
        if state["attempts_left"] <= 0:
            return (
                jsonify(
                    {
                        "message": "No attempts left for this secret.",
                        "guess": guess,
                        "attempts_left": state["attempts_left"],
                        "result": "no_attempts",
                        "match": False,
                        "can_create_secret": False,
                    }
                ),
                200,
            )

        # Consume one attempt
        state["attempts_left"] -= 1
        state["last_guess"] = guess

        # Check correct guess
        if guess.lower() == secret_phrase.lower():
            state["last_result"] = "correct"
            state["can_create_secret"] = True

            # Mark secret as solved in the secrets collection
            mark_secret_solved(db, secret_id)

            # Update state in database
            update_game_state(
                current_user.user_uuid,
                db,
                {
                    "attempts_left": state["attempts_left"],
                    "last_result": state["last_result"],
                    "last_guess": state["last_guess"],
                    "can_create_secret": True,
                },
            )

            return (
                jsonify(
                    {
                        "message": "You guessed it! You can now create a new secret.",
                        "guess": guess,
                        "attempts_left": state["attempts_left"],
                        "result": "correct",
                        "match": True,
                        "can_create_secret": True,
                    }
                ),
                200,
            )

        # Incorrect guess
        state["last_result"] = "incorrect"

        # Increment wrong guesses for this secret
        increment_wrong_guesses(db, secret_id)

        # If attempts reach zero, lock user out for 24 hours
        state_update = {
            "attempts_left": state["attempts_left"],
            "last_result": state["last_result"],
            "last_guess": state["last_guess"],
        }

        locked_until = None
        if state["attempts_left"] == 0:
            locked_until = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            state_update["locked_until"] = locked_until
            msg = "Incorrect guess. No attempts left."
        else:
            msg = "Incorrect guess. Try again!"

        # Update state in database
        update_game_state(current_user.user_uuid, db, state_update)

        return (
            jsonify(
                {
                    "message": msg,
                    "guess": guess,
                    "attempts_left": state["attempts_left"],
                    "result": "incorrect",
                    "match": False,
                    "can_create_secret": False,
                    "locked_until": locked_until,
                }
            ),
            200,
        )

    @app_instance.route("/api/create-secret", methods=["POST"])
    @login_required
    def create_secret():
        """Allow winning player to create a new secret with a hint."""
        user_state = (
            db.game_states.find_one({"user_uuid": current_user.user_uuid})
            if db is not None
            else None
        )

        if not user_state or not user_state.get("can_create_secret", False):
            return (
                jsonify({"error": "You don't have permission to create a secret."}),
                403,
            )

        data = request.get_json() or {}
        new_phrase = (data.get("secret_phrase", "")).strip()
        hint = (data.get("hint", "")).strip()

        if not new_phrase:
            return jsonify({"error": "Secret phrase cannot be empty."}), 400

        if not hint:
            return jsonify({"error": "Hint cannot be empty."}), 400

        if len(new_phrase) < 3:
            return (
                jsonify({"error": "Secret phrase must be at least 3 characters."}),
                400,
            )

        if len(hint) < 5:
            return jsonify({"error": "Hint must be at least 5 characters."}), 400

        # Create the new secret
        new_secret = create_new_secret(db, new_phrase, hint, current_user.user_uuid)

        if new_secret is None:
            return jsonify({"error": "Failed to create secret."}), 500

        # Reset this user's can_create_secret flag
        update_game_state(
            current_user.user_uuid,
            db,
            {
                "can_create_secret": False,
            },
        )

        return (
            jsonify(
                {
                    "message": "New secret created.",
                    "secret_id": new_secret.get("secret_id"),
                }
            ),
            200,
        )

    @app_instance.route("/api/send-metadata", methods=["POST"])
    @login_required
    def send_metadata():
        """Sends guess metadata to database."""
        metadata = request.get_json() or {}

        if not metadata:
            return jsonify({"error": "Metadata cannot be empty"}), 400

        if db is not None:
            try:
                db.metadata.insert_one(
                    {
                        "user_uuid": current_user.user_uuid,
                        "username": current_user.username,
                        "metadata": metadata,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                return jsonify({"message": "Metadata saved successfully"}), 200
            except Exception as e:
                return jsonify({"error": f"Database error: {str(e)}"}), 500
        else:
            return jsonify({"error": "Database not configured"}), 503

    @app_instance.route("/api/metadata-summary", methods=["GET"])
    @login_required
    def metadata_summary():
        """Return aggregated metadata for the dashboard."""
        try:
            if db is None:
                return jsonify({"error": "Database not configured"}), 503

            # Count total metadata entries
            total_entries = db.metadata.count_documents({})

            # Count how many entries belong to this user (optional)
            user_entries = db.metadata.count_documents(
                {"user_uuid": current_user.user_uuid}
            )

            # Most recent metadata timestamp
            latest = db.metadata.find_one({}, sort=[("timestamp", -1)])

            latest_timestamp = latest["timestamp"] if latest else None

            # Example: count submissions by page type
            page_counts = db.metadata.aggregate(
                [
                    {"$group": {"_id": "$metadata.page", "count": {"$sum": 1}}},
                ]
            )
            page_counts = list(page_counts)

            return (
                jsonify(
                    {
                        "total_entries": total_entries,
                        "user_entries": user_entries,
                        "latest_timestamp": latest_timestamp,
                        "page_counts": page_counts,  # e.g. how many times dashboard was visited
                    }
                ),
                200,
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app_instance.route("/api/reset", methods=["POST"])
    @login_required
    def reset_game():
        """Reset game state for this player for the current secret."""
        # Get active secret
        active_secret = get_active_secret(db)

        if active_secret is None:
            return jsonify({"error": "No active secret available"}), 503

        reset_state = {
            "current_secret_id": active_secret.get("secret_id"),
            "attempts_left": 3,
            "last_result": None,
            "last_guess": None,
            "can_create_secret": False,
            "locked_until": None,
        }
        update_game_state(current_user.user_uuid, db, reset_state)

        return (
            jsonify(
                {
                    "message": "Game reset. You have 3 new attempts.",
                    **reset_state,
                }
            ),
            200,
        )

    return app_instance


# ML integration

def transcribe_audio(file_storage) -> str:
    """
    Placeholder transcription function.

    - `file_storage` is a Werkzeug FileStorage object.
    - In the real project, this should call your ML client or an external STT service.
    """
    user_id = current_user.user_uuid
    if not ML_CLIENT_URL:
        raise RuntimeError("Environment variable ML_CLIENT_URL is not set")

    # Read the file content once and reset pointer
    file_storage.seek(0)
    audio_bytes = file_storage.read()
    
    payload = {"user_id": user_id}
    
    # Try up to 2 times
    for attempt in range(2):
        # Create a fresh BytesIO object for each attempt
        file_obj = io.BytesIO(audio_bytes)
        files = {"audio": (file_storage.filename, file_obj, file_storage.content_type)}
        
        try:
            resp = requests.post(
                f"{ML_CLIENT_URL}/transcribe", files=files, data=payload, timeout=120
            )
            resp.raise_for_status()
            ml_result = resp.json()
            
            success = ml_result.get("transcription_success", False)
            guess = ml_result.get("transcription", "")
            
            if success:
                return guess
                
        except requests.RequestException as e:
            if attempt == 1:
                return "Transcription Failed"
            continue
    
    # Fallback
    return "Transcription Failed"


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=3000, debug=True)
