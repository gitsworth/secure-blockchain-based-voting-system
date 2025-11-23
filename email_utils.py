# email_utils.py
import streamlit as st
import smtplib
from email.message import EmailMessage

# Access secrets from Streamlit Cloud
secrets = st.secrets["brevo"]
SMTP_USER = secrets["smtp_user"]
SMTP_KEY = secrets["smtp_key"]

def send_email(to_email, subject, content):
    """
    Sends an email via Brevo SMTP.
    """
    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP('smtp-relay.brevo.com', 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_KEY)
            server.send_message(msg)
        return True, "Email sent successfully."
    except Exception as e:
        return False, f"Failed to send email: {e}"
