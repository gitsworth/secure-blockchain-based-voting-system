import smtplib
from email.mime.text import MIMEText
import streamlit as st

def send_email(to_email, subject, body):
    secrets = st.secrets["brevo"]
    smtp_user = secrets["smtp_user"]
    smtp_key = secrets["smtp_key"]
    smtp_server = "smtp-relay.brevo.com"
    smtp_port = 587

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_key)
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"Email could not be sent: {e}")
        return False
