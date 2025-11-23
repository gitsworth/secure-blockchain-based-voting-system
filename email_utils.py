import yagmail

def send_email(smtp_host_email, smtp_api_key, recipient_email, subject, body, private_key, public_key):
    """
    Sends an email containing the voter's credentials using yagmail (which simplifies SMTP).
    """
    
    # Custom email body format for credentials
    content = [
        f"Hello,",
        f"Here are your confidential credentials for the Secure Blockchain Voting System:",
        f"\n--- CREDENTIALS ---\n",
        f"VOTER ID (Public Key): {public_key}",
        f"SECRET WALLET KEY (Private Key): {private_key}",
        f"\n-------------------\n",
        body,
        f"\nKeep your secret key safe. You will need it to cast your vote."
    ]
    
    try:
        # Initialize yagmail with the host's email and API key (which acts as a password/app token)
        yag = yagmail.SMTP(user=smtp_host_email, password=smtp_api_key)
        
        # Send the email
        yag.send(
            to=recipient_email,
            subject=subject,
            contents=content
        )
        print(f"Successfully sent email to {recipient_email}")
        return True
    
    except Exception as e:
        print(f"EMAIL SEND ERROR to {recipient_email}: {e}")
        return False
