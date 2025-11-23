import streamlit as st
import sqlite3
from datetime import datetime, date
import hashlib
from blockchain import Blockchain
from email_utils import send_email
import random, string

# ------------------------
# CONFIG
# ------------------------
DB = "voters.db"
MAX_VOTERS = 100
MAX_CANDIDATES = 5
THEME_BLUE = "#1e63d6"

st.set_page_config(page_title="Secure Voting System", layout="wide")

st.markdown(f"""
<style>
.stApp {{ background: #f8fbff; }}
.card {{ background: white; padding: 18px; border-radius: 10px; box-shadow: 0 4px 12px rgba(30,99,214,0.08); margin-bottom:10px; }}
.sidebar-blue {{ background-color: {THEME_BLUE}; color:white; padding: 10px; border-radius:0px; }}
.grey-box {{ background-color:#e0e0e0; padding:12px; border-radius:8px; margin-bottom:10px; }}
.green-box {{ background-color:#a8e6a1; padding:12px; border-radius:8px; margin-bottom:10px; }}
.blue-btn {{ background: {THEME_BLUE}; color: white; padding: 8px 16px; border-radius: 8px; border: none; font-weight:600; }}
</style>
""", unsafe_allow_html=True)

# ------------------------
# DATABASE
# ------------------------
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS voters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                dob TEXT,
                email TEXT UNIQUE,
                password TEXT,
                verified INTEGER DEFAULT 0,
                has_voted INTEGER DEFAULT 0
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_hash TEXT,
                candidate TEXT,
                timestamp TEXT
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS election_state (
                id INTEGER PRIMARY KEY CHECK(id=1),
                voting_started INTEGER DEFAULT 0,
                voting_ended INTEGER DEFAULT 0
                )""")
    c.execute("INSERT OR IGNORE INTO election_state (id,voting_started,voting_ended) VALUES (1,0,0)")
    c.execute("""CREATE TABLE IF NOT EXISTS verification_tokens (
                email TEXT UNIQUE,
                token TEXT,
                timestamp TEXT
                )""")
    conn.commit()
    conn.close()

init_db()
blockchain = Blockchain()

# ------------------------
# UTILITIES
# ------------------------
def hash_value(s: str):
    return hashlib.sha256(s.encode()).hexdigest()

def voter_hash(email):
    return hash_value(email.strip().lower()+"|securevoting")

def generate_token(email):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return hash_value(email + salt)

# ------------------------
# QUERY PARAMS
# ------------------------
query_params = st.experimental_get_query_params()
mode = query_params.get("mode", ["host"])[0]
verify_token = query_params.get("verify", [None])[0]

# ------------------------
# DATABASE HELPERS
# ------------------------
def add_voter(full_name, dob, email, password):
    conn = get_conn(); c = conn.cursor()
    normalized = ' '.join(full_name.strip().split()).lower()
    try:
        c.execute("INSERT INTO voters (full_name,dob,email,password) VALUES (?,?,?,?,?)", (normalized,dob,email.strip().lower(),password))
        conn.commit(); conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_voter_by_email(email):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM voters WHERE email=?", (email.strip().lower(),))
    row = c.fetchone(); conn.close()
    return row

def mark_voter_verified(email):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE voters SET verified=1 WHERE email=?", (email.strip().lower(),))
    conn.commit(); conn.close()

def mark_voted(email, candidate):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE voters SET has_voted=1 WHERE email=?", (email.strip().lower(),))
    v_hash = voter_hash(email)
    c.execute("INSERT INTO votes (voter_hash,candidate,timestamp) VALUES (?,?,?)", (v_hash,candidate,str(datetime.utcnow())))
    conn.commit(); conn.close()
    blockchain.add_block(f"{v_hash}|{candidate}")

def add_candidate(name):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("INSERT INTO candidates (name) VALUES (?)", (name.strip(),))
        conn.commit(); conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def remove_candidate(name):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM candidates WHERE name=?", (name.strip(),))
    conn.commit(); conn.close()

def list_candidates():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id,name FROM candidates ORDER BY id"); rows=c.fetchall(); conn.close()
    return rows

def list_voters():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT full_name,dob,email,has_voted FROM voters ORDER BY id"); rows=c.fetchall(); conn.close()
    return rows

def get_state():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT voting_started,voting_ended FROM election_state WHERE id=1"); row=c.fetchone(); conn.close()
    return {'voting_started':bool(row[0]),'voting_ended':bool(row[1])}

def set_voting(start=False,end=False):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET voting_started=?,voting_ended=? WHERE id=1", (1 if start else 0,1 if end else 0))
    conn.commit(); conn.close()

# ------------------------
# HOST DASHBOARD
# ------------------------
if mode=="host":
    st.markdown(f"<div class='card'><h1 style='color:{THEME_BLUE};'>Secure<br>Blockchain<br>Voting System</h1></div>", unsafe_allow_html=True)
    tabs = ["Home","Voters","Candidates","Blockchain"]
    selected_tab = st.sidebar.radio("Navigation", tabs)

    if selected_tab=="Home":
        st.write("Host dashboard controls")
        state = get_state()
        if st.button("Start Voting"):
            if len(list_candidates())<2:
                st.warning("Not sufficient candidates")
            else:
                set_voting(start=True,end=False); st.success("Voting started")
        if st.button("End Voting"):
            set_voting(start=False,end=True); st.success("Voting ended")

    elif selected_tab=="Voters":
        st.header("Registered Voters")
        for v in list_voters():
            name,dob,email,has_voted=v
            with st.container():
                st.markdown(f"<div class='grey-box'>Name: {name.title()}<br>DOB: {dob}<br>Email: {email}</div>", unsafe_allow_html=True)
                if st.button(f"Remove {name}",key=email):
                    if st.confirm(f"Remove voter {name}?"):
                        conn=get_conn();c=conn.cursor();c.execute("DELETE FROM voters WHERE email=?",(email,));conn.commit();conn.close()
                        st.success(f"{name} removed")

    elif selected_tab=="Candidates":
        st.header("Candidates")
        if st.button("Add Candidate"):
            if len(list_candidates())>=MAX_CANDIDATES: st.warning("Maximum 5 candidates")
            else: st.text_input("Candidate Name","",key="new_cand")
            # implement adding logic with a submit button
        for c in list_candidates():
            name=c[1]
            with st.container():
                st.markdown(f"<div class='grey-box'>{name}</div>", unsafe_allow_html=True)
                if st.button(f"Remove {name}",key=name):
                    remove_candidate(name)
                    st.success(f"{name} removed")

    elif selected_tab=="Blockchain":
        st.header("Blockchain")
        for blk in blockchain.chain:
            st.markdown(f"**Block #{blk.index}**<br>Timestamp: {blk.timestamp}<br>Hash: {blk.hash}<br>Previous: {blk.previous_hash}",unsafe_allow_html=True)

# ------------------------
# VOTER PORTAL
# ------------------------
elif mode=="voter":
    tabs=["Home","Register","Vote","Blockchain"]
    selected_tab = st.sidebar.radio("Navigation", tabs)

    state = get_state()

    if selected_tab=="Home":
        st.header("Welcome")
        if st.button("Results"):
            # generate bar chart + table
            st.write("Results will be here")

    elif selected_tab=="Register":
        st.header("Register to Vote")
        name = st.text_input("Full Name",max_chars=50)
        dob = st.date_input("Date of Birth")
        email = st.text_input("Email",max_chars=50)
        password = st.text_input("Password",type="password",max_chars=50)
        if st.button("Register"):
            today=date.today()
            age=today.year-dob.year-((today.month,today.day)<(dob.month,dob.day))
            if age<18: st.error("Not eligible to vote")
            else:
                existing=get_voter_by_email(email)
                if existing and existing[1]==name.lower() and existing[2]==dob.strftime("%Y-%m-%d"): st.warning("Already registered")
                else:
                    token = generate_token(email)
                    add_voter(name,dob.strftime("%Y-%m-%d"),email,password)
                    # save token in DB
                    conn=get_conn();c=conn.cursor();c.execute("INSERT OR REPLACE INTO verification_tokens(email,token,timestamp) VALUES (?,?,?)",(email,token,str(datetime.utcnow())));conn.commit();conn.close()
                    link=f"https://your-app-link.streamlit.app/?mode=voter&verify={token}"
                    send_email(email,"Confirm Registration",f"Click this link to confirm your registration: {link}")
                    st.success("Verification email sent. Please check your inbox")

    elif selected_tab=="Vote":
        if not state['voting_started']: st.info("Voting not started yet")
        else:
            st.header("Vote for your Candidate")
            candidates=list_candidates()
            choice=st.radio("Select candidate",[c[1] for c in candidates])
            if st.button("Confirm Choice"):
                st.text_input("Enter Name for confirmation")
                st.text_input("Enter Email")
                st.text_input("Enter Password",type="password")
                # add logic to validate credentials & record vote

    elif selected_tab=="Blockchain":
        st.header("Blockchain")
        for blk in blockchain.chain:
            st.markdown(f"**Block #{blk.index}**<br>Timestamp: {blk.timestamp}<br>Hash: {blk.hash}<br>Previous: {blk.previous_hash}",unsafe_allow_html=True)

# ------------------------
# VERIFY TOKEN
# ------------------------
if verify_token:
    conn=get_conn();c=conn.cursor();c.execute("SELECT email FROM verification_tokens WHERE token=?",(verify_token,));row=c.fetchone()
    if row:
        mark_voter_verified(row[0])
        st.success("✅ Registration confirmed!")
    else:
        st.error("Invalid or expired verification link")
