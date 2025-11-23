# app.py
import streamlit as st
from blockchain import Blockchain
from email_utils import send_email
import database as db
import hashlib
from datetime import datetime, date

# ------------------------ CONFIG ------------------------
MAX_VOTERS = 100
MAX_CANDIDATES = 5
THEME_BLUE = "#1e63d6"

st.set_page_config(page_title="Secure Voting System", layout="wide")

st.markdown(f"""
<style>
.stApp {{ background: #f8fbff; }}
.card {{ background: white; padding: 18px; border-radius: 10px; box-shadow: 0 4px 12px rgba(30,99,214,0.08); }}
.blue-btn {{ background: {THEME_BLUE}; color: white; padding: 8px 16px; border-radius: 8px; border: none; font-weight:600; }}
</style>
""", unsafe_allow_html=True)

# ------------------------ INIT ------------------------
db.init_db()
blockchain = Blockchain()

# ------------------------ HELPERS ------------------------
def hash_value(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def voter_hash(email):
    return hash_value(email.strip().lower() + "|securevoting")

# ------------------------ MODE ------------------------
query = st.experimental_get_query_params()
mode = query.get("mode", ["host"])[0]

st.sidebar.title("Navigation")
st.sidebar.markdown("Host" if mode=="host" else "Voter")

view_chain = st.sidebar.button("View Blockchain")
show_results = st.sidebar.button("Results")

state = db.get_state()

# ------------------------ HOST ------------------------
if mode=="host":
    st.header("Secure Blockchain Voting System (Host)")
    col1,col2=st.columns(2)
    with col1:
        if state['registration_open']:
            if st.button("Close Registration"): db.set_registration(False)
        else:
            if st.button("Enable Registration"): db.set_registration(True)
    with col2:
        if state['voting_open']:
            if st.button("End Voting"): db.end_voting()
        else:
            if st.button("Start Voting"):
                cands=db.list_candidates()
                if len(cands)<2: st.warning("Not enough candidates")
                else: db.start_voting()

    st.subheader("Candidates")
    cname = st.text_input("Candidate Name")
    if st.button("Add Candidate"):
        if len(db.list_candidates())>=MAX_CANDIDATES: st.warning("Max candidates reached")
        else: db.add_candidate(cname)

    st.subheader("Voters")
    voters_conn=db.get_conn(); c=voters_conn.cursor()
    c.execute("SELECT full_name,dob,email,has_voted FROM voters ORDER BY id")
    rows=c.fetchall(); voters_conn.close()
    for r in rows:
        st.write(f"Name: {r[0]} | DOB: {r[1]} | Email: {r[2]} | Voted: {bool(r[3])}")

# ------------------------ VOTER ------------------------
else:
    st.header("Welcome to Secure Voting")
    if state['registration_open']:
        name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            today=date.today()
            age=today.year-dob.year-((today.month,today.day)<(dob.month,dob.day))
            if age<18: st.error("Not eligible")
            else:
                ok,msg=db.add_voter(name,dob.strftime("%Y-%m-%d"),email,password)
                if ok: st.success(msg)
                else: st.error(msg)

# ------------------------ BLOCKCHAIN ------------------------
if view_chain:
    st.subheader("Blockchain Explorer")
    for blk in blockchain.chain:
        st.write(f"Block #{blk.index} | Data: {blk.data} | Hash: {blk.hash}")
