import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from email_utils import send_email
from blockchain import Blockchain

DB_NAME = "voters.db"

# Initialize blockchain
blockchain = Blockchain()

# -----------------------
# DATABASE HELPERS
# -----------------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def validate_voter(name, dob, email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM voters WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    if result:
        return False  # Email already registered
    return True

def register_voter(name, dob, email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO voters (name, dob, email) VALUES (?, ?, ?)", (name, dob, email))
    conn.commit()
    conn.close()
    # Send confirmation email
    subject = "Registration Successful"
    body = f"Hello {name},\nYou have been registered successfully as a voter."
    try:
        send_email(email, subject, body)
    except:
        pass

def voter_login(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM voters WHERE email=?", (email,))
    voter = c.fetchone()
    conn.close()
    return voter

def mark_voted(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE voters SET has_voted=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()

def get_candidates():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM candidates")
    candidates = c.fetchall()
    conn.close()
    return candidates

def add_candidate(name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO candidates (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_voters():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, dob, email, has_voted FROM voters")
    voters = c.fetchall()
    conn.close()
    return voters

def remove_voter(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM voters WHERE email=?", (email,))
    conn.commit()
    conn.close()
    # Notify voter
    subject = "Voter Removal Notification"
    body = f"Hello, your voter registration has been removed."
    try:
        send_email(email, subject, body)
    except:
        pass

# -----------------------
# HOST LOGIN
# -----------------------
def host_login(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM hosts WHERE username=? AND password=?", (username, hashed_password))
    result = c.fetchone()
    conn.close()
    return result is not None

# -----------------------
# STREAMLIT UI
# -----------------------
st.title("Secure Blockchain Voting System")

menu = ["Voter Registration", "Voter Login", "Host Login"]
choice = st.sidebar.selectbox("Select Option", menu)

# -----------------------
# VOTER REGISTRATION
# -----------------------
if choice == "Voter Registration":
    st.header("Register as a Voter")
    name = st.text_input("Full Name")
    dob = st.date_input("Date of Birth")
    email = st.text_input("Email")

    if st.button("Register"):
        # Validate age
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            st.error("You must be at least 18 years old to register.")
        elif not validate_voter(name, dob.strftime("%Y-%m-%d"), email):
            st.error("Email already registered.")
        else:
            register_voter(name, dob.strftime("%Y-%m-%d"), email)
            st.success("Registration successful! Check your email for confirmation.")

# -----------------------
# VOTER LOGIN & VOTING
# -----------------------
elif choice == "Voter Login":
    st.header("Voter Login")
    email = st.text_input("Email")

    if st.button("Login"):
        voter = voter_login(email)
        if voter:
            name, dob_str, email, has_voted = voter[1], voter[2], voter[3], voter[4]
            # Age check
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            age = datetime.today().year - dob.year - ((datetime.today().month, datetime.today().day) < (dob.month, dob.day))
            if age < 18:
                st.error("You must be at least 18 years old to vote.")
            elif has_voted:
                st.warning("You have already voted.")
            else:
                st.subheader("Candidates")
                candidates = get_candidates()
                candidate_names = [c[1] for c in candidates]
                vote_choice = st.radio("Select Candidate", candidate_names)
                if st.button("Submit Vote"):
                    # Add to blockchain
                    blockchain.add_block({
                        "voter_email": email,
                        "vote": vote_choice
                    })
                    mark_voted(email)
                    st.success(f"Vote submitted for {vote_choice}!")
                    # Send confirmation email
                    subject = "Vote Confirmation"
                    body = f"Hello {name},\nYour vote for {vote_choice} has been recorded successfully."
                    try:
                        send_email(email, subject, body)
                    except:
                        st.warning("Email could not be sent. Possibly reached daily free limit.")
        else:
            st.error("Email not registered.")

# -----------------------
# HOST LOGIN & DASHBOARD
# -----------------------
elif choice == "Host Login":
    st.header("Host Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if host_login(username, password):
            st.success("Login successful! Welcome, host.")
            host_menu = st.selectbox("Host Menu", ["View Voters", "Add Candidate", "Remove Voter", "View Blockchain"])
            
            if host_menu == "View Voters":
                st.subheader("Voter List")
                voters = get_voters()
                st.table(voters)
            
            elif host_menu == "Add Candidate":
                st.subheader("Add Candidate")
                new_candidate = st.text_input("Candidate Name")
                if st.button("Add"):
                    if new_candidate.strip() != "":
                        add_candidate(new_candidate.strip())
                        st.success(f"Candidate {new_candidate} added.")
                    else:
                        st.error("Enter a valid candidate name.")
            
            elif host_menu == "Remove Voter":
                st.subheader("Remove Voter")
                email_to_remove = st.text_input("Voter Email")
                if st.button("Remove"):
                    remove_voter(email_to_remove)
                    st.success(f"Voter {email_to_remove} removed.")
            
            elif host_menu == "View Blockchain":
                st.subheader("Blockchain (Hashes only)")
                for block in blockchain.chain:
                    st.write(f"Index: {block['index']}, Hash: {block['hash']}, Timestamp: {block['timestamp']}")
        else:
            st.error("Invalid host credentials.")
