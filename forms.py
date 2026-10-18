# This file contains forms for app authentication and data submission.


# ------------------ imports -------------------------------------------------------------------------------------------


from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo, Optional


# ------------------ form classes --------------------------------------------------------------------------------------


# app log in form
class LogInForm(FlaskForm):
    username = StringField(
        label="Username",
        validators=[InputRequired()]
    )
    password = PasswordField(
        label="Password",
        validators=[InputRequired()]
    )
    submit = SubmitField(
        label="Log In"
    )


# first time account creation form
class UpdateLoginForm(FlaskForm):
    username = StringField(
        label="Username",
        validators=[InputRequired(), Length(min=4, max=32)]
    )
    password = PasswordField(
        label="Password",
        validators=[InputRequired(), Length(min=8, max=32)]
    )
    confirm = PasswordField(
        label="Confirm Password",
        validators=[InputRequired(), EqualTo(fieldname="password", message="Passwords must match.")]
    )
    submit = SubmitField(
        label="Log In"
    )


# hyundai distance data submission form
class HyundaiDistanceForm(FlaskForm):
    date = StringField(
        label="Date (mm/dd/yyyy)",
        validators=[InputRequired()]
    )
    odometer = IntegerField(
        label="Odometer",
        validators=[InputRequired()]
    )
    miles = FloatField(
        label="Miles",
        validators=[InputRequired()]
    )
    efficiency = FloatField(
        label="mi/kWh",
        validators=[InputRequired()]
    )
    level = IntegerField(
        label="% Level at charge (omit %)",
        validators=[InputRequired()]
    )
    submit = SubmitField(
        label="Submit"
    )


# hyundai charge data submission form
class HyundaiChargeForm(FlaskForm):
    energy = FloatField(
        label="kWh",
        validators=[InputRequired()]
    )
    dollars = FloatField(
        label="Dollars spent (omit $)",
        validators=[InputRequired()]
    )
    note = StringField(
        label="Note",
        validators=[Optional()]
    )
    submit = SubmitField(
        label="Submit"
    )


# honda and porsche data submission form
class FuelForm(FlaskForm):
    date = StringField(
        label="Date (mm/dd/yyyy)",
        validators=[InputRequired()]
    )
    odometer = IntegerField(
        label="Odometer",
        validators=[InputRequired()]
    )
    miles = FloatField(
        label="Miles",
        validators=[InputRequired()]
    )
    gallons = FloatField(
        label="Gallons",
        validators=[InputRequired()]
    )
    efficiency = FloatField(
        label="MPG",
        validators=[InputRequired()]
    )
    tank_cost = FloatField(
        label="Tank cost (omit $)",
        validators=[InputRequired()]
    )
    gallon_cost = FloatField(
        label="Gallon cost (omit $)",
        validators=[InputRequired()]
    )
    note = StringField(
        label="Note",
        validators=[Optional()]
    )
    submit = SubmitField(
        label="Submit"
    )