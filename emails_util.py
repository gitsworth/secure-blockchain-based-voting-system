import smtplib
from email.mime.text import MIMEText
import os
import streamlit as st

# SMTP Configuration for Brevo
SMTP_SERVER = "smtp-relay.sendinblue.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_USER")  # From Streamlit Secrets
SMTP_PASS = os.environ.get("SMTP_PASS")  # From Streamlit Secrets

def send_email(to_email, subject, body):
    """
    Sends an email using Brevo SMTP.
    Handles exceptions so the app does not crash if email fails.
    """
    try:
        # Create the email message
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email

        # Connect to Brevo SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()

        # Optional: Streamlit feedback
        st.success(f"Email sent to {to_email} successfully!")

    except Exception as e:
        # Log the error to console
        print(f"Email could not be sent to {to_email}: {e}")
        # Show warning in Streamlit UI
        st.warning(f"Email could not be sent to {to_email}. It may have reached the daily free limit.")
