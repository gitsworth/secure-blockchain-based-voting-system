# app.py
import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date
from blockchain import Blockchain
from email_utils import send_email

# ------------------------ CONFIG ------------------------
DB = "voters.db"
MAX_VOTERS = 100
MAX_CANDIDATES = 5
THEME_BLUE = "#1e63d6"

st.set_page_config(page_title="Secure Voting System", layout="wide")

st.markdown(f"""
<style>
.stApp {{ background: #f8fbff; }}
.card {{ background: white; padding: 18px; border-radius: 10px; box-shadow: 0 4px 12px rgba(30,99,214,0.08); }}
.blue-btn {{ background: {THEME_BLUE}; color: white; padding: 8px 16px; border-radius: 8px; border: none; font-weight:600; }}
.grey-box {{ background: #e0e0e0; padding:12px; border-radius:10px; margin-bottom:10px; }}
.small-muted {{ color: #6b7280; font-size: 13px; }}
</style>
""", unsafe_allow_html=True)

# ------------------------ DATABASE ------------------------
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
                    registration_open INTEGER DEFAULT 0,
                    voting_open INTEGER DEFAULT 0,
                    ended INTEGER DEFAULT 0
                )""")
    c.execute("INSERT OR IGNORE INTO election_state (id, registration_open, voting_open, ended) VALUES (1,0,0,0)")
    conn.commit(); conn.close()

init_db()
blockchain = Blockchain()

# ------------------------ HELPERS ------------------------
def hash_value(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def voter_hash(email):
    return hash_value(email.strip().lower() + "|securevoting")

def get_state():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT registration_open, voting_open, ended FROM election_state WHERE id=1")
    row = c.fetchone(); conn.close()
    return {'registration_open': bool(row[0]), 'voting_open': bool(row[1]), 'ended': bool(row[2])}

def set_registration(open_bool: bool):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET registration_open=?, voting_open=0, ended=0 WHERE id=1", (1 if open_bool else 0,))
    conn.commit(); conn.close()

def start_voting():
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET registration_open=0, voting_open=1, ended=0 WHERE id=1")
    conn.commit(); conn.close()

def end_voting():
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET registration_open=0, voting_open=0, ended=1 WHERE id=1")
    conn.commit(); conn.close()

# ------------------------ VOTER/CANDIDATE ------------------------
def count_voters():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM voters"); n=c.fetchone()[0]; conn.close()
    return n

def add_voter(full_name, dob, email, password):
    if count_voters() >= MAX_VOTERS:
        return False, "Voter limit reached (100)."
    normalized = ' '.join(part.strip() for part in full_name.split()).lower()
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("INSERT INTO voters (full_name, dob, email, password) VALUES (?, ?, ?, ?)",
                  (normalized, dob, email.strip().lower(), password))
        conn.commit(); conn.close()
        # Send email notification
        subject = "Registration Successful - Secure Voting"
        content = f"Hello {full_name},\n\nYou have successfully registered to vote."
        send_email(email, subject, content)
        return True, "Registered successfully."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already registered."

def get_voter(email):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id, full_name, dob, email, password, has_voted FROM voters WHERE email=?", (email.strip().lower(),))
    row=c.fetchone(); conn.close()
    return row

def mark_voted(email, voter_hash_val, candidate):
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE voters SET has_voted=1 WHERE email=?", (email.strip().lower(),))
    c.execute("INSERT INTO votes (voter_hash, candidate, timestamp) VALUES (?, ?, ?)",
              (voter_hash_val, candidate, str(datetime.utcnow())))
    conn.commit(); conn.close()

def add_candidate(name):
    conn=get_conn(); c=conn.cursor()
    try: c.execute("INSERT INTO candidates (name) VALUES (?)", (name.strip(),)); conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError: conn.close(); return False

def list_candidates():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id, name FROM candidates ORDER BY id"); rows=c.fetchall(); conn.close(); return rows

def tally_results():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT candidate, COUNT(*) FROM votes GROUP BY candidate")
    rows=c.fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

# ------------------------ UI ------------------------
query = st.experimental_get_query_params()
mode = query.get("mode", ["host"])[0]  # default goes to host

st.sidebar.title("Navigation")
if mode=="host":
    st.sidebar.markdown("Host Dashboard")
else:
    st.sidebar.markdown("Voter Portal")

view_chain = st.sidebar.button("View Blockchain")
show_results = st.sidebar.button("Results")

# ------------------------ HOST ------------------------
if mode=="host":
    st.header("Secure Blockchain Voting System (Host)")
    state = get_state()
    st.write(f"Registration open: {state['registration_open']} | Voting open: {state['voting_open']} | Ended: {state['ended']}")

    col1,col2=st.columns(2)
    with col1:
        if state['registration_open']:
            if st.button("Close Registration"): set_registration(False); st.success("Registration closed.")
        else:
            if st.button("Enable Registration"): set_registration(True); st.success("Registration enabled.")
    with col2:
        if state['voting_open']:
            if st.button("End Voting"): end_voting(); st.success("Voting ended.")
        else:
            if st.button("Start Voting"):
                cands=list_candidates()
                if len(cands)<2: st.warning("Not sufficient candidates"); 
                else: start_voting(); st.success("Voting started.")

    st.markdown("---")
    st.subheader("Candidates")
    with st.form("add_candidate"):
        cname=st.text_input("Candidate Name"); submitted=st.form_submit_button("Add Candidate")
        if submitted:
            if cname.strip()=="": st.error("Enter a valid name.")
            elif len(list_candidates())>=MAX_CANDIDATES: st.warning("Candidate limit reached (5).")
            else:
                ok=add_candidate(cname)
                if ok: st.success(f"Candidate '{cname}' added.")
                else: st.warning("Candidate exists.")
    candidates=list_candidates()
    if candidates: st.write("Current candidates:", [c[1] for c in candidates])

    st.markdown("---")
    st.subheader("Registered Voters")
    conn=get_conn(); c=conn.cursor(); c.execute("SELECT id, full_name, dob, email, has_voted FROM voters ORDER BY id"); rows=c.fetchall(); conn.close()
    if rows: st.table([{"Name": r[1].title(),"DOB":r[2],"Email":r[3],"Has Voted":bool(r[4])} for r in rows])
    else: st.info("No voters registered yet.")

# ------------------------ VOTER ------------------------
else:
    st.header("Welcome to Secure Voting")
    state = get_state()

    st.markdown("---")
    if state['registration_open']:
        st.subheader("Register to Vote")
        name=st.text_input("Full Name", key="reg_name")
        dob=st.date_input("Date of Birth", key="reg_dob")
        email=st.text_input("Email", key="reg_email")
        password=st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            today=date.today()
            age=today.year-dob.year-((today.month,today.day)<(dob.month,dob.day))
            if age<18: st.error("You must be at least 18.")
            else:
                ok,msg=add_voter(name,dob.strftime("%Y-%m-%d"),email,password)
                if ok: st.success(msg)
                else: st.error(msg)

    elif state['voting_open']:
        st.subheader("Voting")
        email=st.text_input("Enter registered email", key="vote_email")
        password=st.text_input("Enter password", type="password", key="vote_pass")
        if st.button("Login to vote"):
            voter=get_voter(email)
            if not voter: st.error("Email not found.")
            else:
                vid, full_name, dob_str, em, pwd, has_voted=voter
                if pwd!=password: st.error("Wrong credentials")
                elif has_voted: st.warning("Already voted")
                else:
                    cands=list_candidates()
                    choice=st.radio("Select candidate",[c[1] for c in cands])
                    if st.button("Submit Vote"):
                        v_hash=voter_hash(email)
                        blockchain.add_block(hash_value(email.strip().lower()+"|"+choice+"|"+str(datetime.utcnow())))
                        mark_voted(email,v_hash,choice)
                        st.success(f"Vote for {choice} recorded!")

    elif state['ended']:
        st.subheader("Election Results")
        counts=tally_results()
        if counts:
            total=sum(counts.values())
            for cand,cnt in counts.items():
                pct=(cnt/total)*100 if total>0 else 0
                st.write(f"**{cand}** — {cnt} votes ({pct:.1f}%)")
        else: st.info("No votes yet.")

# ------------------------ BLOCKCHAIN VIEWER ------------------------
if view_chain:
    st.subheader("Blockchain Explorer (Real-Time)")
    for blk in blockchain.chain:
        try:
            idx=blk.index; ts=blk.timestamp; h=blk.hash; prev=blk.previous_hash
        except:
            idx=blk['index']; ts=blk['timestamp']; h=blk['hash']; prev=blk['previous_hash']
        st.markdown(f"**Block #{idx}**")
        st.write(f"Timestamp: {ts}")
        st.write(f"Previous Hash: `{prev}`")
        st.write(f"Current Hash: `{h}`")
        st.markdown("---")
