# ------------------ info ----------------------------------------------------------------------------------------------


# 1C398E  tailwind blue-900
# web application for managing car fuel efficiency and more
# flash messages are success, notify, error


# ------------------ imports -------------------------------------------------------------------------------------------


import os
import csv
import sqlite3

from random import randint
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


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


# ------------------ forms ---------------------------------------------------------------------------------------------


class LogInForm(FlaskForm):
    username = StringField(label="Username", validators=[DataRequired()])
    password = PasswordField(label="Password", validators=[DataRequired()])
    submit = SubmitField(label="Log In")


class UpdateLoginForm(FlaskForm):
    username = StringField(label="Username", validators=[DataRequired(), Length(min=4, max=32)])
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=8, max=32)])
    confirm = PasswordField(label="Confirm Password", validators=[DataRequired(), EqualTo(fieldname="password", message="Passwords must match.")])
    submit = SubmitField(label="Log In")


# ------------------ log in/out routes ---------------------------------------------------------------------------------


# log in
@app.route("/log_in", methods=["GET", "POST"])
def log_in():
    # checks
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    # form
    form = LogInForm()

    # POST
    if form.validate_on_submit():
        # get data if validated
        username = form.username.data
        password = form.password.data

        db_username, db_password = get_user()

        if username != db_username or not check_password_hash(db_password, password):
            flash("Incorrect username or password.", "error")
            return render_template("log_in.html", form=form)

        login_user(User(user_id=1, username=db_username, hashed_password=db_password))
        return redirect(url_for("home"))
    # GET
    return render_template("log_in.html", form=form)


# update login from default
@app.route("/update_login", methods=["GET", "POST"])
@login_required
def update_login():
    # checks
    if not using_default_login():
        return redirect(url_for("home"))

    # form
    form = UpdateLoginForm()

    # POST
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        confirm_password = form.confirm.data

        if password != confirm_password:
            flash("Passwords must match.", "error")
            return render_template("update_login.html", form=form)

        overwrite_user(username, password)

        flash("Login information has been updated.", "success")
        return redirect(url_for("home"))
    # GET
    flash("You are currently using the default login. Please choose a new username and password.", "notify")
    return render_template("update_login.html", form=form)


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
    hyundai_stats = generate_hyundai_stats()

    return render_template("hyundai.html", car_stats=hyundai_stats)


@app.route("/honda")
@login_required
def honda():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))
    # GET
    honda_stats = generate_honda_stats()

    return render_template("honda.html", car_stats=honda_stats)


@app.route("/porsche")
@login_required
def porsche():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))
    # GET
    porsche_stats = generate_porsche_stats()

    return render_template("porsche.html", car_stats=porsche_stats)


# ------------------ data functions ------------------------------------------------------------------------------------







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


# load hyundai data
def generate_hyundai_stats():
    # mm/dd/yy
    date = []
    # .0
    miles_per_tank = []
    # .0
    miles_kwh_per_tank = []
    # 00
    start_charge_per_tank = []
    # .00
    kwh_per_tank = []
    # .00
    dollars_per_tank = []
    # 00
    end_charge_per_tank = []

    # pull data from csv
    try:
        with open("data/hyundai.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            hyundai_stats = {}

            for row in reader:
                date.append(row[0])
                miles_per_tank.append(float(row[2]))
                miles_kwh_per_tank.append(float(row[3]))
                start_charge_per_tank.append(float(row[4][:-1]))
                kwh_per_tank.append(float(row[5]))
                dollars_per_tank.append(float(row[6][1:]))
                end_charge_per_tank.append(float(row[7][:-1]))
    except OSError:
        return {"error": "data failure"}

    # do data science
    kwh_cost_per_tank = []
    for i in range(len(date)):
        cost = dollars_per_tank[i] / kwh_per_tank[i]
        kwh_cost_per_tank.append(cost)

    # real value
    hyundai_stats["Lifetime efficiency"] = f"{sum(miles_per_tank) / sum(kwh_per_tank, 2):.1f} mi/kWh"
    # car estimate
    hyundai_stats["Most efficient tank"] = f"{max(miles_kwh_per_tank):.1f} mi/kWh"
    hyundai_stats["Least efficient tank"] = f"{min(miles_kwh_per_tank):.1f} mi/kWh"

    hyundai_stats["Lifetime energy cost"] = f"${sum(dollars_per_tank):.2f}"
    hyundai_stats["Lifetime kWh cost"] = f"${(sum(dollars_per_tank) / sum(kwh_per_tank)):.3f}"
    hyundai_stats["Most expensive kWh"] = f"${max(kwh_cost_per_tank):.3f}"
    hyundai_stats["Least expensive kWh"] = f"${min(kwh_cost_per_tank):.3f}"

    hyundai_stats["Odometer"] = f"{(sum(miles_per_tank) + 17):.0f} miles"
    hyundai_stats["Average tank distance"] = f"{sum(miles_per_tank) / len(miles_per_tank):.1f} miles"
    hyundai_stats["Longest tank distance"] = f"{max(miles_per_tank):.1f} miles"
    hyundai_stats["Shortest tank distance"] = f"{min(miles_per_tank):.1f} miles"

    return hyundai_stats


# load honda data
def generate_honda_stats():
    # mm/dd/yy
    date = []
    # .0
    miles_per_tank = []
    # .000
    gallons_per_tank = []
    # .00
    dollars_per_tank = []

    # pull data from csv
    try:
        with open("data/honda.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            honda_stats = {}

            for row in reader:
                date.append(row[0])
                miles_per_tank.append(float(row[2]))
                gallons_per_tank.append(float(row[3]))
                dollars_per_tank.append(float(row[5][1:]))
    except OSError:
        return {"error": "data failure"}

    # do data science
    mpg_per_tank = []
    for i in range(len(date)):
        mpg = miles_per_tank[i] / gallons_per_tank[i]
        mpg_per_tank.append(mpg)

    gallon_cost_per_tank = []
    for i in range(len(date)):
        cost = dollars_per_tank[i] / gallons_per_tank[i]
        gallon_cost_per_tank.append(cost)

    honda_stats["Lifetime efficiency"] = f"{sum(miles_per_tank) / sum(gallons_per_tank, 2):.1f} mpg"
    honda_stats["Most efficient tank"] = f"{max(mpg_per_tank):.1f} mpg"
    honda_stats["Least efficient tank"] = f"{min(mpg_per_tank):.1f} mpg"

    honda_stats["Lifetime fuel cost"] = f"${sum(dollars_per_tank):.2f}"
    honda_stats["Lifetime gallon cost"] = f"${(sum(dollars_per_tank) / sum(gallons_per_tank)):.3f}"
    honda_stats["Most expensive gallon"] = f"${max(gallon_cost_per_tank):.3f}"
    honda_stats["Least expensive gallon"] = f"${min(gallon_cost_per_tank):.3f}"

    honda_stats["Odometer"] = f"{sum(miles_per_tank):.0f} miles"
    honda_stats["Average tank distance"] = f"{sum(miles_per_tank) / len(miles_per_tank):.1f} miles"
    honda_stats["Longest tank distance"] = f"{max(miles_per_tank):.1f} miles"
    honda_stats["Shortest tank distance"] = f"{min(miles_per_tank):.1f} miles"

    return honda_stats


# load porsche data
def generate_porsche_stats():
    # mm/dd/yy
    date = []
    # .0
    miles_per_tank = []
    # .000
    gallons_per_tank = []
    # .00
    dollars_per_tank = []

    # pull data from csv
    try:
        with open("data/porsche.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            porsche_stats = {}

            for row in reader:
                date.append(row[0])
                miles_per_tank.append(float(row[2]))
                gallons_per_tank.append(float(row[3]))
                dollars_per_tank.append(float(row[5][1:]))
    except OSError:
        return {"error": "data failure"}

    # do data science
    mpg_per_tank = []
    for i in range(len(date)):
        mpg = miles_per_tank[i] / gallons_per_tank[i]
        mpg_per_tank.append(mpg)

    gallon_cost_per_tank = []
    for i in range(len(date)):
        cost = dollars_per_tank[i] / gallons_per_tank[i]
        gallon_cost_per_tank.append(cost)

    porsche_stats["Lifetime efficiency"] = f"{sum(miles_per_tank) / sum(gallons_per_tank, 2):.1f} mpg"
    porsche_stats["Most efficient tank"] = f"{max(mpg_per_tank):.1f} mpg"
    porsche_stats["Least efficient tank"] = f"{min(mpg_per_tank):.1f} mpg"

    porsche_stats["Lifetime fuel cost"] = f"${sum(dollars_per_tank):.2f}"
    porsche_stats["Lifetime gallon cost"] = f"${(sum(dollars_per_tank) / sum(gallons_per_tank)):.3f}"
    porsche_stats["Most expensive gallon"] = f"${max(gallon_cost_per_tank):.3f}"
    porsche_stats["Least expensive gallon"] = f"${min(gallon_cost_per_tank):.3f}"

    porsche_stats["Odometer"] = f"{(sum(miles_per_tank) + 18):.0f} miles"
    porsche_stats["Average tank distance"] = f"{sum(miles_per_tank) / len(miles_per_tank):.1f} miles"
    porsche_stats["Longest tank distance"] = f"{max(miles_per_tank):.1f} miles"
    porsche_stats["Shortest tank distance"] = f"{min(miles_per_tank):.1f} miles"

    return porsche_stats


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