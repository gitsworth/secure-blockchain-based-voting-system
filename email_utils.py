# email_utils.py
import streamlit as st
import smtplib
from email.message import EmailMessage
from typing import Tuple

def send_verification_email(to_email: str, verification_link: str) -> Tuple[bool, str]:
    """
    Sends a verification email using SMTP credentials stored in Streamlit secrets.
    You will add your Brevo (or other SMTP) credentials manually under st.secrets["brevo"]:
      st.secrets["brevo"]["smtp_user"]
      st.secrets["brevo"]["smtp_key"]
    The function returns (success: bool, message: str).
    """
    try:
        secrets = st.secrets.get("brevo", None)
        if not secrets:
            return False, "Email not configured in Streamlit secrets (st.secrets['brevo'])."

        smtp_user = secrets.get("smtp_user")
        smtp_key = secrets.get("smtp_key")
        if not smtp_user or not smtp_key:
            return False, "Incomplete SMTP credentials in secrets."

        msg = EmailMessage()
        msg['Subject'] = "Confirm your registration"
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg.set_content(f"Hello,\n\nClick the link to verify your registration:\n\n{verification_link}\n\nIf you didn't request this, ignore.")

        with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_key)
            server.send_message(msg)

        return True, "Verification email sent."
    except Exception as e:
        return False, f"Sending failed: {e}"
