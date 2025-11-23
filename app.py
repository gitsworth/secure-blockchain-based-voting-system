# app.py
import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime, date
from urllib.parse import urlencode
from blockchain import Blockchain          # use your blockchain.py
from email_utils import send_email         # use the email_utils.py with exception handling

DB = "voters.db"
MAX_VOTERS = 100
THEME_BLUE = "#1e63d6"

st.set_page_config(page_title="Secure Voting (Blue/White)", layout="centered")

# --- small CSS for blue-white card look ---
st.markdown(
    f"""
    <style>
    .main > div {{background: #ffffff;}}
    .stApp {{ background: #f8fbff; }}
    .card {{ background: white; padding: 18px; border-radius: 10px;
             box-shadow: 0 4px 12px rgba(30,99,214,0.08); }}
    .blue-btn {{ background: {THEME_BLUE}; color: white; padding: 8px 16px;
                border-radius: 8px; border: none; font-weight:600; }}
    .small-muted {{ color: #6b7280; font-size: 13px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Helper: DB / initialization
# -------------------------
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # voters table
    c.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            dob TEXT,
            email TEXT UNIQUE,
            has_voted INTEGER DEFAULT 0
        )
    """)
    # candidates table
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    # votes aggregate table (for counting results)
    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_hash TEXT,
            candidate TEXT,
            timestamp TEXT
        )
    """)
    # election state: single-row table with registration/voting/ended flags
    c.execute("""
        CREATE TABLE IF NOT EXISTS election_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            registration_open INTEGER DEFAULT 0,
            voting_open INTEGER DEFAULT 0,
            ended INTEGER DEFAULT 0
        )
    """)
    # ensure a single row exists
    c.execute("INSERT OR IGNORE INTO election_state (id, registration_open, voting_open, ended) VALUES (1,0,0,0)")
    conn.commit()
    conn.close()

# Ensure DB and blockchain exist
init_db()
blockchain = Blockchain()   # uses your blockchain.py implementation

# -------------------------
# Election state helpers
# -------------------------
def set_registration(open_bool: bool):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET registration_open=?, voting_open=?, ended=? WHERE id=1",
              (1 if open_bool else 0, 0, 0))
    conn.commit(); conn.close()

def start_voting():
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET registration_open=0, voting_open=1, ended=0 WHERE id=1")
    conn.commit(); conn.close()

def end_voting():
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE election_state SET registration_open=0, voting_open=0, ended=1 WHERE id=1")
    conn.commit(); conn.close()

def get_state():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT registration_open, voting_open, ended FROM election_state WHERE id=1")
    row = c.fetchone(); conn.close()
    return {'registration_open': bool(row[0]), 'voting_open': bool(row[1]), 'ended': bool(row[2])}

# -------------------------
# Voter / Candidate helpers
# -------------------------
def count_voters():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM voters")
    n = c.fetchone()[0]; conn.close()
    return n

def add_voter(full_name, dob, email):
    if count_voters() >= MAX_VOTERS:
        return False, "Voter limit reached (100)."
    # normalize name
    normalized = ' '.join(part.strip() for part in full_name.split()).lower()
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("INSERT INTO voters (full_name, dob, email) VALUES (?, ?, ?)", (normalized, dob, email.strip().lower()))
        conn.commit()
        conn.close()
        return True, "Registered"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already registered."

def get_voter(email):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id, full_name, dob, email, has_voted FROM voters WHERE email=?", (email.strip().lower(),))
    row = c.fetchone(); conn.close()
    return row

def mark_voted(email, voter_hash, candidate):
    conn = get_conn(); c = conn.cursor()
    # mark flag
    c.execute("UPDATE voters SET has_voted=1 WHERE email=?", (email.strip().lower(),))
    # store aggregate vote record (candidate)
    c.execute("INSERT INTO votes (voter_hash, candidate, timestamp) VALUES (?, ?, ?)", (voter_hash, candidate, str(datetime.utcnow())))
    conn.commit(); conn.close()

def add_candidate(name):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("INSERT INTO candidates (name) VALUES (?)", (name.strip(),))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def list_candidates():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id, name FROM candidates ORDER BY id")
    rows = c.fetchall(); conn.close()
    return rows

def tally_results():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT candidate, COUNT(*) FROM votes GROUP BY candidate")
    rows = c.fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

# -------------------------
# Utility functions
# -------------------------
def hash_value(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def voter_hash(email):
    # hash with salt-like constant for privacy (not reversible easily)
    return hash_value(email.strip().lower() + "|securevoting")

# -------------------------
# Determine mode: host (no login) vs voter
# Host opens URL: ?mode=host  OR click "Host Dashboard" in UI
# -------------------------
query = st.experimental_get_query_params()
mode = query.get("mode", ["voter"])[0]  # default voter view

# top header
st.markdown(f"<h1 style='color:{THEME_BLUE};'>Secure Voting — Blue & White</h1>", unsafe_allow_html=True)
st.markdown("<div class='small-muted'>Controlled election flow: host enables registration → starts voting → ends election</div>", unsafe_allow_html=True)
st.write("")  # spacing

# If host mode: show dashboard immediately (no login)
if mode == "host":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("Host Dashboard")
    state = get_state()
    st.write(f"**Registration open:** {state['registration_open']}   |   **Voting open:** {state['voting_open']}   |   **Ended:** {state['ended']}")

    col1, col2 = st.columns(2)
    with col1:
        if state['registration_open']:
            if st.button("Close Registration"):
                set_registration(False)
                st.success("Registration closed.")
        else:
            if st.button("Enable Registration"):
                set_registration(True)
                st.success("Registration enabled. Voters can now register.")
    with col2:
        if state['voting_open']:
            if st.button("End Voting"):
                end_voting()
                st.success("Voting ended.")
        else:
            if st.button("Start Voting"):
                # ensure registration is closed before starting
                start_voting()
                st.success("Voting started. Registration closed automatically.")

    st.markdown("---")
    # Candidate management
    st.subheader("Candidates")
    with st.form("add_candidate"):
        cname = st.text_input("Candidate name")
        submitted = st.form_submit_button("Add Candidate")
        if submitted:
            if cname.strip() == "":
                st.error("Enter a valid name.")
            else:
                ok = add_candidate(cname)
                if ok:
                    st.success(f"Candidate '{cname}' added.")
                else:
                    st.warning("Candidate already exists.")
    candidates = list_candidates()
    if candidates:
        st.write("Current candidates:")
        for cid, name in candidates:
            st.write(f"- {name}")

    st.markdown("---")
    # Voter management
    st.subheader("Voters (registered)")
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id, full_name, dob, email, has_voted FROM voters ORDER BY id")
    rows = c.fetchall(); conn.close()
    if rows:
        st.table([{"Name": r[1].title(), "DOB": r[2], "Email": r[3], "Has Voted": bool(r[4])} for r in rows])
    else:
        st.info("No voters registered yet.")

    # Remove voter
    st.markdown("---")
    st.subheader("Remove Voter")
    rem_email = st.text_input("Email to remove", key="rem_email")
    if st.button("Remove Voter"):
        if rem_email.strip() == "":
            st.error("Enter an email to remove.")
        else:
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT email FROM voters WHERE email=?", (rem_email.strip().lower(),))
            found = c.fetchone(); conn.close()
            if not found:
                st.warning("Email not found.")
            else:
                # remove and notify
                conn = get_conn(); c = conn.cursor()
                c.execute("DELETE FROM voters WHERE email=?", (rem_email.strip().lower(),))
                conn.commit(); conn.close()
                # Optionally remove votes too (or keep for audit); here we keep votes
                st.success(f"{rem_email} removed.")
                try:
                    send_email(rem_email, "Voter Removed", "Your registration has been removed by the host.")
                except Exception:
                    st.warning("Removal notification email failed to send.")

    st.markdown("---")
    # Blockchain view (hashes only)
    st.subheader("Blockchain (immutable hashes)")
    for blk in blockchain.chain:
        # Block object: show index, timestamp, hash, previous_hash
        try:
            idx = blk.index
            ts = blk.timestamp
            h = blk.hash
            prev = blk.previous_hash
        except Exception:
            # backward compatibility if block stored as dict
            idx = blk['index']; ts = blk['timestamp']; h = blk['hash']; prev = blk['previous_hash']
        st.write(f"Index: {idx}  |  Timestamp: {ts}")
        st.write(f"Hash: `{h}`")
        st.write(f"Previous: `{prev}`")
        st.markdown("---")

    st.markdown("---")
    # Results (aggregated) - visible to host always, and to voters after ended
    st.subheader("Current Results (aggregate)")
    counts = tally_results()
    if counts:
        for cand, cnt in counts.items():
            st.write(f"- {cand}: **{cnt}**")
    else:
        st.info("No votes cast yet.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Host view — share the voter URL (no ?mode=host) with voters when you open registration/voting.")

# VOTER MODE (default)
else:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("Voter Portal")
    state = get_state()
    st.write(f"**Registration open:** {state['registration_open']}   |   **Voting open:** {state['voting_open']}   |   **Ended:** {state['ended']}")
    st.markdown("---")

    # Registration
    if state['registration_open']:
        st.subheader("Register to vote")
        name = st.text_input("Full name", key="reg_name")
        dob = st.date_input("Date of birth", key="reg_dob")
        email = st.text_input("Email", key="reg_email")
        if st.button("Register"):
            # age check
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                st.error("You must be at least 18 to register.")
            else:
                ok, msg = add_voter(name, dob.strftime("%Y-%m-%d"), email)
                if ok:
                    st.success("Registered successfully! Check your email for confirmation.")
                    try:
                        send_email(email, "Registration Successful", f"Hello {name}, you are registered to vote.")
                    except Exception:
                        st.warning("Confirmation email not sent (service limit?).")
                else:
                    st.error(msg)

    # Voting
    elif state['voting_open']:
        st.subheader("Voting")
        email = st.text_input("Enter your registered email to login", key="vote_email")
        if st.button("Login to vote"):
            voter = get_voter(email)
            if not voter:
                st.error("Email not found. Please register first.")
            else:
                vid, full_name, dob_str, em, has_voted = voter
                if has_voted:
                    st.warning("You have already voted.")
                else:
                    # show candidates
                    cands = list_candidates()
                    if not cands:
                        st.info("No candidates have been added yet.")
                    else:
                        names = [c[1] for c in cands]
                        choice = st.radio("Select candidate", names)
                        if st.button("Submit Vote"):
                            # create voter hash, and a vote fingerprint stored in blockchain
                            v_hash = voter_hash(email)
                            # create a vote fingerprint (we will not store candidate in chain; chain stores vote fingerprint only)
                            vote_fingerprint = hash_value(email.strip().lower() + "|" + choice + "|" + str(datetime.utcnow()))
                            blockchain.add_block(vote_fingerprint)
                            # store aggregate vote in votes table (this is how we tally while keeping chain private)
                            mark_voted(email, v_hash, choice)
                            st.success(f"Thank you — your vote for {choice} has been recorded.")
                            try:
                                send_email(email, "Vote Confirmation", f"Hello {full_name}, your vote for {choice} has been recorded.")
                            except Exception:
                                st.warning("Confirmation email not sent (service limit?)")

    # Results (after ended)
    elif state['ended']:
        st.subheader("Election Results")
        counts = tally_results()
        if counts:
            # nice display bars
            total = sum(counts.values())
            for cand, cnt in counts.items():
                pct = (cnt / total) * 100 if total > 0 else 0
                st.write(f"**{cand}** — {cnt} votes ({pct:.1f}%)")
                st.progress(min(int(pct), 100))
        else:
            st.info("No votes found.")
        st.markdown("---")
        st.subheader("Blockchain (audit view - hashes only)")
        for blk in blockchain.chain:
            try:
                idx = blk.index
                ts = blk.timestamp
                h = blk.hash
                prev = blk.previous_hash
            except Exception:
                idx = blk['index']; ts = blk['timestamp']; h = blk['hash']; prev = blk['previous_hash']
            st.write(f"Index: {idx}  |  Timestamp: {ts}")
            st.write(f"Hash: `{h}`")
            st.write(f"Previous: `{prev}`")
            st.markdown("---")

    else:
        st.info("Registration and voting are currently closed. Please come back later.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---- footer help / quick links ----
st.write("")
st.markdown("<div class='small-muted'>Host URL example: add `?mode=host` to the app URL to access the host dashboard directly.</div>", unsafe_allow_html=True)
