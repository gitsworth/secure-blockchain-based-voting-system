# email_utils.py
import streamlit as st
import smtplib
from email.mime.text import MIMEText

# ------------------------
# Load Brevo SMTP credentials from Streamlit Secrets
# ------------------------
try:
    BREVO_USER = st.secrets["brevo"]["smtp_user"]
    BREVO_PASS = st.secrets["brevo"]["smtp_key"]
except KeyError:
    BREVO_USER = ""
    BREVO_PASS = ""
    print("Warning: Brevo SMTP credentials not found in Streamlit secrets.")

BREVO_SMTP = "smtp-relay.brevo.com"
BREVO_PORT = 587

# ------------------------
# Email sending function
# ------------------------
def send_email(to_email, subject, body):
    """
    Sends an email using Brevo SMTP.
    If sending fails (e.g., quota exceeded), exception is caught.
    """
    if not BREVO_USER or not BREVO_PASS:
        print("Email not sent: SMTP credentials missing.")
        return False

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = BREVO_USER
        msg['To'] = to_email

        server = smtplib.SMTP(BREVO_SMTP, BREVO_PORT)
        server.starttls()
        server.login(BREVO_USER, BREVO_PASS)
        server.sendmail(BREVO_USER, [to_email], msg.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"Email failed to {to_email}: {e}")
        return False
