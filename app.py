
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
from pathlib import Path
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
import os
import random

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "treequest.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "treequest-development-key"
)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

POINTS_REQUIRED = 100
GAME_REWARD = 20

TREES = [
    "Mango Tree", "Mahogany Tree", "Narra Tree", "Acacia Tree",
    "Molave Tree", "Bamboo", "Banaba Tree", "Ipil-ipil Tree"
]

PLANTING_AREAS = [
    "Angeles City, Pampanga", "Zambales, Philippines",
    "Bataan, Philippines", "Tarlac, Philippines",
    "Nueva Ecija, Philippines", "Quezon, Philippines"
]

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                points INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tree_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                tree_name TEXT NOT NULL,
                location TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                photo_filename TEXT,
                organization_note TEXT
            )
        """)

        conn.execute(
            "INSERT OR IGNORE INTO players (username, points) VALUES (?, ?)",
            ("Player", 0)
        )


# IMPORTANT: Initialize database when Render imports this file.
init_db()


def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("username"):
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                flash("That page is not available for this account type.", "error")
                return redirect(url_for("home"))

            return fn(*args, **kwargs)

        return wrapper
    return decorator


# HOME PAGE
@app.route("/")
def home():
    if not session.get("username"):
        return redirect(url_for("login"))

    if session.get("role") == "organization":
        return redirect(url_for("organization_dashboard"))

    return redirect(url_for("player_welcome"))


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "Player").strip() or "Player"
        role = request.form.get("role", "player")

        if role not in ("player", "organization"):
            role = "player"

        session.clear()

        session["username"] = (
            username if role == "player"
            else "TreeQuest Partner Organization"
        )

        session["role"] = role

        if role == "player":
            with db() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO players (username, points) VALUES (?, 0)",
                    (username,)
                )

        return redirect(url_for("home"))

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# NEW PLAYER WELCOME SCREEN
@app.route("/player/welcome")
@login_required("player")
def player_welcome():
    return render_template("welcome.html")


# START BUTTON DESTINATION
@app.route("/player/start")
@login_required("player")
def player_start():
    return redirect(url_for("player_dashboard"))


# PLAYER DASHBOARD
@app.route("/player")
@login_required("player")
def player_dashboard():
    with db() as conn:
        player = conn.execute(
            "SELECT * FROM players WHERE username=?",
            (session["username"],)
        ).fetchone()

        requests = conn.execute("""
            SELECT * FROM tree_requests WHERE username=?
            ORDER BY id DESC
        """, (session["username"],)).fetchall()

        unread = sum(
            1 for item in requests if item["status"] == "Planted"
        )

    return render_template(
        "player.html",
        player=player,
        requests=requests,
        points_required=POINTS_REQUIRED,
        unread=unread
    )


# MINI-GAME REWARD
@app.route("/play", methods=["POST"])
@login_required("player")
def play():
    with db() as conn:
        conn.execute(
            "UPDATE players SET points = points + ? WHERE username=?",
            (GAME_REWARD, session["username"])
        )

    flash(
        f"Game completed! You earned {GAME_REWARD} points.",
        "success"
    )

    return redirect(url_for("player_dashboard"))


# REDEEM TREE
@app.route("/redeem", methods=["POST"])
@login_required("player")
def redeem():
    with db() as conn:
        player = conn.execute(
            "SELECT points FROM players WHERE username=?",
            (session["username"],)
        ).fetchone()

        if not player or player["points"] < POINTS_REQUIRED:
            flash(
                "You need 100 points before redeeming a tree.",
                "error"
            )
            return redirect(url_for("player_dashboard"))

        tree = random.choice(TREES)
        location = random.choice(PLANTING_AREAS)

        conn.execute(
            "UPDATE players SET points = points - ? WHERE username=?",
            (POINTS_REQUIRED, session["username"])
        )

        conn.execute("""
            INSERT INTO tree_requests
            (username, tree_name, location, created_at, status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (
            session["username"],
            tree,
            location,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

    flash(
        f"Your {tree} request was sent to the partner organization!",
        "success"
    )

    return redirect(url_for("player_dashboard"))


# PLAYER INBOX
@app.route("/inbox")
@login_required("player")
def inbox():
    with db() as conn:
        messages = conn.execute("""
            SELECT * FROM tree_requests
            WHERE username=?
            AND (status='Planted' OR organization_note IS NOT NULL)
            ORDER BY id DESC
        """, (session["username"],)).fetchall()

    return render_template("inbox.html", messages=messages)


# ORGANIZATION DASHBOARD
@app.route("/organization")
@login_required("organization")
def organization_dashboard():
    with db() as conn:
        requests = conn.execute(
            "SELECT * FROM tree_requests ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "organization.html",
        requests=requests
    )


# ACCEPT TREE REQUEST
@app.route("/organization/request/<int:request_id>/accept", methods=["POST"])
@login_required("organization")
def accept_request(request_id):
    with db() as conn:
        conn.execute("""
            UPDATE tree_requests SET status='Accepted'
            WHERE id=? AND status='Pending'
        """, (request_id,))

    flash("Request marked as accepted.", "success")

    return redirect(url_for("organization_dashboard"))


# UPLOAD PLANTING PHOTO
@app.route("/organization/request/<int:request_id>/plant", methods=["POST"])
@login_required("organization")
def mark_planted(request_id):
    photo = request.files.get("photo")
    note = request.form.get("note", "").strip()

    if not photo or not photo.filename:
        flash(
            "Please select a planting photo before submitting.",
            "error"
        )
        return redirect(url_for("organization_dashboard"))

    filename = secure_filename(photo.filename)

    extension = (
        filename.rsplit(".", 1)[-1].lower()
        if "." in filename else ""
    )

    if extension not in ALLOWED_EXTENSIONS:
        flash(
            "Please upload a JPG, PNG, GIF, or WEBP image.",
            "error"
        )
        return redirect(url_for("organization_dashboard"))

    unique_name = (
        f"request_{request_id}_"
        f"{int(datetime.now().timestamp())}.{extension}"
    )

    photo.save(UPLOAD_DIR / unique_name)

    with db() as conn:
        result = conn.execute(
            "SELECT id FROM tree_requests WHERE id=?",
            (request_id,)
        ).fetchone()

        if not result:
            (UPLOAD_DIR / unique_name).unlink(missing_ok=True)
            flash("Request not found.", "error")
            return redirect(url_for("organization_dashboard"))

        conn.execute("""
            UPDATE tree_requests
            SET status='Planted',
                photo_filename=?,
                organization_note=?
            WHERE id=?
        """, (unique_name, note, request_id))

    flash(
        "Planting confirmation and photo sent to the player's inbox.",
        "success"
    )

    return redirect(url_for("organization_dashboard"))


# IMAGE UPLOAD ERROR
@app.errorhandler(413)
def too_large(_error):
    flash(
        "Image is too large. Please use an image under 5 MB.",
        "error"
    )
    return redirect(url_for("organization_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)

