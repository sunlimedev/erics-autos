# This file contains a function to send an email with a csv attachment.


# ------------------ imports -------------------------------------------------------------------------------------------


import os
import smtplib
from pathlib import Path

from dotenv import load_dotenv
from email.message import EmailMessage


# ------------------ constants -----------------------------------------------------------------------------------------


load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

SENDER = os.getenv("SENDER", "")
RECIPIENT = os.getenv("RECIPIENT", "")


# ------------------ function ------------------------------------------------------------------------------------------


def send_email(file_path: Path):
    # get vehicle name
    car = file_path.stem.capitalize()

    # create email object
    msg = EmailMessage()
    msg["Subject"] = f"{car} Data Backup"
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg.set_content(f"Hi Dad, here is a backup of your {car} fuel data.")

    # read the file and attach it to message
    try:
        with open(file_path, "rb") as file:
            file_data = file.read()
            msg.add_attachment(file_data, maintype="text", subtype="csv", filename=file_path.name)
    except OSError:
        return False

    # send the email with attachment
    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SENDER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        return False

    return True