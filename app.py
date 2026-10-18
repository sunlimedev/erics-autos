# This file contains a Flask application for vehicle fuel data recording.

# Flash messages have three categories: success, notify, error.
# These messages are green, yellow, and red, respectively.

# The SQLite database is assumed to be working and formatted correctly.
# Other data sources like .csv files use a try except pattern for all access.


# ------------------ imports -------------------------------------------------------------------------------------------


import os
import csv
import sqlite3

from pathlib import Path
from random import randint
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import contextmanager

from backup import send_email
from forms import LogInForm, UpdateLoginForm, HyundaiDistanceForm, HyundaiChargeForm, FuelForm


# ------------------ constants -----------------------------------------------------------------------------------------


# load environment variables
load_dotenv()

# load default account credentials
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME", "")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "")

# load obscured account reset string
RESET_LOGIN_ROUTE = os.getenv("RESET_LOGIN_ROUTE", "reset_password")

# server host and port when invoked directly
HOST = "0.0.0.0"
PORT = 5000


# ------------------ flask ---------------------------------------------------------------------------------------------


# name of flask app file
app = Flask(__name__)

# key for generating sessions
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "abcdefghjiklmnopqrstuvwxyz")

# login system for users
login_manager = LoginManager(app)

# page to log in
login_manager.login_view = "log_in"

# custom login manager error
login_manager.login_message = 'Please log in.'
login_manager.login_message_category = 'error'

# class for users
class User(UserMixin):
    def __init__(self, user_id, username, hashed_password):
        self.id = user_id
        self.username = username
        self.hashed_password = hashed_password


# ------------------ authentication routes -----------------------------------------------------------------------------


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


@app.get("/hyundai")
@login_required
def hyundai():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))

    # GET
    hyundai_stats = generate_hyundai_stats()

    return render_template("hyundai.html", car_stats=hyundai_stats)


@app.get("/honda")
@login_required
def honda():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))

    # GET
    stats = generate_gas_stats("honda")

    return render_template("honda.html", car_stats=stats)


@app.get("/porsche")
@login_required
def porsche():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))

    # GET
    stats = generate_gas_stats("porsche")

    return render_template("porsche.html", car_stats=stats)


# ------------------ logging routes ------------------------------------------------------------------------------------


@app.route("/hyundai/log_data", methods=["GET", "POST"])
@login_required
def hyundai_log_data():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))

    # form
    file_path = Path("data/hyundai.csv")

    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            headers = next(reader)

            # rip full table
            date = []
            odometer = []
            miles_per_tank = []
            miles_kwh_per_tank = []
            start_charge_per_tank = []
            kwh_per_tank = []
            dollars_per_tank = []
            notes = []

            for row in reader:
                date.append(row[0])
                odometer.append(row[1])
                miles_per_tank.append(row[2])
                miles_kwh_per_tank.append(row[3])
                start_charge_per_tank.append(row[4])
                kwh_per_tank.append(row[5])
                dollars_per_tank.append(row[6])
                notes.append(row[7])

            # check if last row half-filled
            last = len(date) - 1

            if kwh_per_tank[last] == "" and dollars_per_tank[last] == "":
                form, letter = HyundaiChargeForm(), "c"
            else:
                form, letter = HyundaiDistanceForm(), "d"
    except (OSError, csv.Error):
        flash("Critical data read error.", "error")
        return redirect(url_for("hyundai"))

    # POST
    if form.validate_on_submit():
        file_path = Path("data/hyundai.csv")

        if isinstance(form, HyundaiChargeForm):
            kwh_per_tank[last] = form.energy.data
            dollars_per_tank[last] = form.dollars.data
            notes[last] = form.note.data

            try:
                with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)

                    writer.writerow(headers)

                    for i in range(len(date)):
                        writer.writerow([
                            date[i],
                            odometer[i],
                            miles_per_tank[i],
                            miles_kwh_per_tank[i],
                            start_charge_per_tank[i],
                            kwh_per_tank[i],
                            f"${dollars_per_tank[i]}" if not str(dollars_per_tank[i]).startswith("$") else dollars_per_tank[i],
                            notes[i]
                        ])
            except (OSError, csv.Error):
                flash("Data was not saved!", "error")
                return render_template("hyundai_charge.html", form=form)

            if not send_email(file_path):
                flash("Data was saved but email was not delivered.", "error")
            else:
                flash("Data was saved and backup email was delivered.", "success")
            return redirect(url_for("hyundai"))

        elif isinstance(form, HyundaiDistanceForm):
            print("a")
            try:
                with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)

                    row = [
                        form.date.data,
                        form.odometer.data,
                        form.miles.data,
                        form.efficiency.data,
                        f"{form.level.data}%",
                        "",
                        "",
                        ""
                    ]

                    writer.writerow(row)
                    print("b")
            except (OSError, csv.Error):
                print("c")
                flash("Data was not saved!", "error")
                return render_template("hyundai_distance.html", form=form)

            print("d")
            flash("Data was saved!", "success")
            return redirect(url_for("hyundai"))

    # GET
    if isinstance(form, HyundaiDistanceForm):
        form.date.data = datetime.now().strftime("%m/%d/%Y")
        return render_template("hyundai_distance.html", form=form)
    elif isinstance(form, HyundaiChargeForm):
        return render_template("hyundai_charge.html", form=form)
    else:
        return redirect(url_for("hyundai"))


@app.route("/honda/log_data", methods=["GET", "POST"])
@login_required
def honda_log_data():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))

    # form
    form = FuelForm()

    # POST
    if form.validate_on_submit():
        file_path = Path("data/honda.csv")

        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                row = [
                    form.date.data,
                    form.odometer.data,
                    form.miles.data,
                    form.gallons.data,
                    form.efficiency.data,
                    f"${form.tank_cost.data}",
                    f"${form.gallon_cost.data}",
                    form.note.data
                ]

                writer.writerow(row)
        except (OSError, csv.Error):
            flash("Data was not saved!", "error")
            return render_template("gas_log.html", form=form, car="Honda")

        if not send_email(file_path):
            flash("Data was saved but email was not delivered.", "error")
        else:
            flash("Data was saved and backup email was delivered.", "success")
        return redirect(url_for("honda"))

    # GET
    form.date.data = datetime.now().strftime("%m/%d/%Y")

    return render_template("gas_log.html", form=form, car="Honda")


@app.route("/porsche/log_data", methods=["GET", "POST"])
@login_required
def porsche_log_data():
    # checks
    if using_default_login():
        return redirect(url_for("update_login"))

    # form
    form = FuelForm()

    # POST
    if form.validate_on_submit():
        file_path = Path("data/porsche.csv")

        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                row = [
                    form.date.data,
                    form.odometer.data,
                    form.miles.data,
                    form.gallons.data,
                    form.efficiency.data,
                    f"${form.tank_cost.data}",
                    f"${form.gallon_cost.data}",
                    form.note.data
                ]

                writer.writerow(row)
        except (OSError, csv.Error):
            flash("Data was not saved!", "error")
            return render_template("gas_log.html", form=form, car="Porsche")

        if not send_email(file_path):
            flash("Data was saved but email was not delivered.", "error")
        else:
            flash("Data was saved and backup email was delivered.", "success")
        return redirect(url_for("porsche"))

    # GET
    form.date.data = datetime.now().strftime("%m/%d/%Y")

    return render_template("gas_log.html", form=form, car="Porsche")


# ------------------ table functions -----------------------------------------------------------------------------------


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

    file_path = Path("data/hyundai.csv")

    # pull data from csv
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
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
    except ValueError:
        return {"Waiting on charge data": "..."}
    except (OSError, csv.Error):
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


# load gas car data
def generate_gas_stats(car: str):
    # mm/dd/yy
    date = []
    # .0
    miles_per_tank = []
    # .000
    gallons_per_tank = []
    # .00
    dollars_per_tank = []

    file_path = Path(f"data/{car}.csv")

    # pull data from csv
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)

            stats = {}

            for row in reader:
                date.append(row[0])
                miles_per_tank.append(float(row[2]))
                gallons_per_tank.append(float(row[3]))
                dollars_per_tank.append(float(row[5][1:]))
    except (OSError, csv.Error):
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

    stats["Lifetime efficiency"] = f"{sum(miles_per_tank) / sum(gallons_per_tank, 2):.1f} mpg"
    stats["Most efficient tank"] = f"{max(mpg_per_tank):.1f} mpg"
    stats["Least efficient tank"] = f"{min(mpg_per_tank):.1f} mpg"

    stats["Lifetime fuel cost"] = f"${sum(dollars_per_tank):.2f}"
    stats["Lifetime gallon cost"] = f"${(sum(dollars_per_tank) / sum(gallons_per_tank)):.3f}"
    stats["Most expensive gallon"] = f"${max(gallon_cost_per_tank):.3f}"
    stats["Least expensive gallon"] = f"${min(gallon_cost_per_tank):.3f}"

    stats["Odometer"] = f"{sum(miles_per_tank):.0f} miles"
    stats["Average tank distance"] = f"{sum(miles_per_tank) / len(miles_per_tank):.1f} miles"
    stats["Longest tank distance"] = f"{max(miles_per_tank):.1f} miles"
    stats["Shortest tank distance"] = f"{min(miles_per_tank):.1f} miles"

    return stats


# ------------------ helper functions ----------------------------------------------------------------------------------


# load user from database
@login_manager.user_loader
def load_user(user_id):
    with get_database() as (conn, cur):
        query = "SELECT * FROM users WHERE user_id = ?"
        cur.execute(query, (user_id,))
        user_data = cur.fetchone()

    if user_data:
        return User(user_data["user_id"], user_data["username"], user_data["password"])
    return None


# yield connection to database
@contextmanager
def get_database():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        yield conn, cur
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
    finally:
        cur.close()
        conn.close()

    return


# check if user has not created account
def using_default_login():
    with get_database() as (conn, cur):
        query = "SELECT password FROM users WHERE user_id = 1"
        cur.execute(query)
        credentials = cur.fetchone()

    if credentials["password"] is not None and DEFAULT_PASSWORD is not None:
        if not check_password_hash(credentials["password"], DEFAULT_PASSWORD):
            return False

    return True


# get user from database in tuple (user, pass)
def get_user():
    with get_database() as (conn, cur):
        query = "SELECT username, password FROM users WHERE user_id = 1"
        cur.execute(query)
        credentials = cur.fetchone()

    return credentials


# overwrite existing data with new user
def overwrite_user(username, password):
    hashed_password = generate_password_hash(password)

    with get_database() as (conn, cur):
        query = "INSERT OR REPLACE INTO users (user_id, username, password) VALUES (?, ?, ?)"
        parameters = (1, username, hashed_password)
        cur.execute(query, parameters)

    return


# ------------------ app start -----------------------------------------------------------------------------------------


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)