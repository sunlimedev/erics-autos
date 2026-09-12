# ------------------ info ----------------------------------------------------------------------------------------------

# 1C398E  tailwind blue-900

# web application for managing car fuel efficiency and more

# flash messages are success, notify, error


# ------------------ imports -------------------------------------------------------------------------------------------


import os
import sqlite3

from random import randint
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash


# ------------------ constants -----------------------------------------------------------------------------------------


load_dotenv()

DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")

RESET_LOGIN_ROUTE = os.getenv("RESET_LOGIN_ROUTE")


# ------------------ flask ---------------------------------------------------------------------------------------------


# name of flask app file
app = Flask(__name__)

# key for generating sessions
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# login system for users
login_manager = LoginManager(app)

# page to log in
login_manager.login_view = "log_in"

# adjust default login manager error
login_manager.login_message = 'Please log in.'
login_manager.login_message_category = 'error'

# class for users
class User(UserMixin):
    def __init__(self, user_id, username, hashed_password):
        self.id = user_id
        self.username = username
        self.hashed_password = hashed_password


# ------------------ log in/out routes -------------------------------------------------------------------------------------


# log in
@app.route("/log_in", methods=["GET", "POST"])
def log_in():
    # checks
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    # POST
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username is None:
            flash("Please enter a username.", "error")
            return render_template("log_in.html")
        if password is None:
            flash("Please enter a password.", "error")
            return render_template("log_in.html")

        db_username, db_password = get_user()

        if username != db_username or not check_password_hash(db_password, password):
            flash("Incorrect username or password.", "error")
            return render_template("log_in.html")

        login_user(User(user_id=1, username=db_username, hashed_password=db_password))
        return redirect(url_for("home"))
    # GET
    else:
        return render_template("log_in.html")


# update login from default
@app.route("/update_login", methods=["GET", "POST"])
@login_required
def update_login():
    # checks
    if not using_default_login():
        return redirect(url_for("home"))
    # POST
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm"]

        if username is None:
            flash("Please enter a username.", "error")
            return render_template("update_login.html")
        if password is None:
            flash("Please enter a password.", "error")
            return render_template("update_login.html")
        if len(username) < 4:
            flash("Username must be at least 4 characters.", "error")
            return render_template("update_login.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("update_login.html")
        if password != confirm_password:
            flash("Passwords must match.", "error")
            return render_template("update_login.html")

        overwrite_user(username, password)

        flash("Login information has been updated.", "success")
        return redirect(url_for("home"))
    # GET
    else:
        flash("You are currently using the default login. Please choose a new username and password.", "notify")
        return render_template("update_login.html")


# reset login to default
@app.get(f"/{RESET_LOGIN_ROUTE}")
def reset_login():
    logout_user()

    overwrite_user(DEFAULT_USERNAME, DEFAULT_PASSWORD)

    flash("Login information has been reset.", "success")
    return redirect(url_for("log_in"))


# log out
@app.get("/log_out")
@login_required
def log_out():
    logout_user()

    flash("You have been logged out.", "success")
    return redirect(url_for("log_in"))


# ------------------ content routes ------------------------------------------------------------------------------------


@app.get("/")
@login_required
def home():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))
    # GET
    hyundai_url = url_for("static", filename=f"pretty/hyundai_pretty{randint(1, 4)}.png")
    honda_url = url_for("static", filename=f"pretty/honda_pretty{randint(1, 4)}.png")
    porsche_url = url_for("static", filename=f"pretty/porsche_pretty{randint(1, 5)}.png")

    return render_template("home.html", hyundai_url=hyundai_url, honda_url=honda_url, porsche_url=porsche_url)


@app.route("/hyundai")
@login_required
def hyundai():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))
    # GET
    return render_template("home.html")


@app.route("/honda")
@login_required
def honda():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))
    # GET
    image_url = url_for("static", filename=f"turntable/civic{randint(1, 4)}.png")

    return render_template("honda.html", image_url=image_url)


@app.route("/porsche")
@login_required
def porsche():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))
    # GET
    return render_template("home.html")


# ------------------ helper functions ----------------------------------------------------------------------------------


# load user from database
@login_manager.user_loader
def load_user(user_id):
    conn, cur = get_database()

    query = "SELECT * FROM users WHERE user_id = ?"
    cur.execute(query, (user_id,))

    user_data = cur.fetchone()

    conn.close()

    if user_data:
        return User(user_data["user_id"], user_data["username"], user_data["password"])
    return None


# return connection to database
def get_database():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    return conn, cur


# check if user has not created account
def using_default_login():
    conn, cur = get_database()

    query = "SELECT password FROM users WHERE user_id = 1"
    cur.execute(query)

    row = cur.fetchone()

    conn.close()

    if row["password"] is not None and DEFAULT_PASSWORD is not None:
        if not check_password_hash(row["password"], DEFAULT_PASSWORD):
            return False

    return True


# get user from database in tuple (user, pass)
def get_user():
    conn, cur = get_database()

    query = "SELECT username, password FROM users WHERE user_id = 1"
    cur.execute(query)

    row = cur.fetchone()

    conn.close()

    return row


# overwrite existing data with new user
def overwrite_user(username, password):
    conn, cur = get_database()

    hashed_password = generate_password_hash(password)
    query = "INSERT OR REPLACE INTO users (user_id, username, password) VALUES (?, ?, ?)"
    parameters = (1, username, hashed_password)

    with conn:
        cur.execute(query, parameters)

    conn.close()


# ------------------ app start -----------------------------------------------------------------------------------------


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)