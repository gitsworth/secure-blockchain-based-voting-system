# app.py
import streamlit as st
from datetime import date, datetime
import hashlib, secrets as pysecrets
import pandas as pd
from typing import Optional

import database as db
from blockchain import Blockchain
from email_utils import send_verification_email

# ---------------- config ----------------
THEME_BLUE = "#1e63d6"
GREY_BOX = "#f1f3f6"
GREEN_BOX = "#c6f6d5"

st.set_page_config(page_title="Secure Blockchain Voting", layout="wide")

# ---------------- css ----------------
st.markdown(f"""
<style>
/* left sidebar background (works in many Streamlit releases) */
[data-testid="stSidebar"] > div:first-child {{
  background: {THEME_BLUE};
  padding-top: 12px;
  color: white;
}}
.card {{
  background: {GREY_BOX};
  padding: 12px;
  border-radius: 12px;
  margin-bottom: 8px;
}}
.candidate-box {{
  background: {GREY_BOX};
  padding: 12px;
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 2px solid rgba(0,0,0,0);
}}
.candidate-box.selected {{
  background: {GREEN_BOX};
  border-color: rgba(0,0,0,0.08);
}}
.scroll-box {{
  max-height: 420px;
  overflow-y: auto;
}}
.footer-button {{
  position: fixed;
  bottom: 16px;
  left: 16px;
  right: 16px;
  display: flex;
  justify-content: center;
}}
.small-muted {{ color: #6b7280; font-size: 13px; }}
</style>
""", unsafe_allow_html=True)

# ---------------- init ----------------
db.init_db()
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()

# MODE: host (default) or voter via ?mode=voter
query = st.experimental_get_query_params()
mode = query.get("mode", ["host"])[0]

# sidebar tabs
if mode == "host":
    tab = st.sidebar.radio("Host", ["Home", "Voters", "Candidates", "Blockchain"])
else:
    tab = st.sidebar.radio("Voter", ["Home", "Register", "Vote", "Blockchain"])

# election state (DB)
state = db.get_state()

# ---------------- helpers ----------------
def make_vote_fingerprint(email: str, candidate: str, secret_nonce: str) -> str:
    """Create irreversible fingerprint stored on blockchain."""
    # combine normalized email (or other voter secret), candidate, nonce, timestamp
    payload = f"{email.strip().lower()}|{candidate}|{secret_nonce}|{datetime.utcnow().isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()

def voter_hash_for_db(email: str) -> str:
    """A stable hashed id stored in DB votes table to avoid storing plaintext."""
    return hashlib.sha256((email.strip().lower() + "|voter").encode()).hexdigest()

def generate_token() -> str:
    return pysecrets.token_urlsafe(24)

# ---------------- HOST UI ----------------
if mode == "host":
    st.title("Secure\nBlockchain\nVoting System")

    if tab == "Home":
        st.header("Host Controls")
        st.write("Use the controls below to open registration, start/stop voting, and view results.")
        col1, col2, col3 = st.columns(3)
        with col1:
            if state['registration_open']:
                st.success("Registration: OPEN")
            else:
                st.info("Registration: CLOSED")
        with col2:
            if state['voting_open']:
                st.success("Voting: OPEN")
            else:
                st.info("Voting: CLOSED")
        with col3:
            if state['ended']:
                st.warning("Election ended")
            else:
                st.info("Election active")

        st.markdown("---")

        if state['registration_open']:
            if st.button("Close Registration"):
                db.set_registration(False)
                st.experimental_rerun()
        else:
            if st.button("Open Registration"):
                db.set_registration(True)
                st.experimental_rerun()

        if state['voting_open']:
            if st.button("End Voting"):
                db.end_voting()
                st.experimental_rerun()
        else:
            if st.button("Start Voting"):
                # require at least 2 candidates
                if len(db.list_candidates()) < 2:
                    st.warning("Need at least 2 candidates to start voting.")
                else:
                    db.start_voting()
                    st.experimental_rerun()

        st.markdown("---")
        st.subheader("Results (quick view)")
        results = db.tally_results()
        if results:
            df = pd.DataFrame(list(results.items()), columns=["Candidate","Votes"])
            st.bar_chart(df.set_index("Candidate")["Votes"])
            st.table(df)
        else:
            st.info("No votes yet (or results not available).")

    elif tab == "Voters":
        st.header("Registered Voters")
        st.markdown("<div class='scroll-box'>", unsafe_allow_html=True)
        voters = db.list_voters()
        for v in voters:
            vid, name, dob, email, password, verified, has_voted, registered_at = v
            cols = st.columns([10,1])
            with cols[0]:
                verified_text = "✅" if verified else "⏳"
                voted_text = "✅" if has_voted else "—"
                st.markdown(f"<div class='card'><b>{name.title()}</b><br><span class='small-muted'>DOB: {dob} • Email: {email}</span><br>Verified: {verified_text} • Voted: {voted_text}</div>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("❌", key=f"remove_voter_{vid}"):
                    db.remove_voter(vid)
                    st.experimental_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    elif tab == "Candidates":
        st.header("Candidates")
        c_name = st.text_input("Candidate name", key="host_new_cand")
        if st.button("Add Candidate"):
            ok,msg = db.add_candidate(c_name)
            if ok:
                st.success(msg); st.experimental_rerun()
            else:
                st.warning(msg)
        st.markdown("<div class='scroll-box'>", unsafe_allow_html=True)
        for cid, cname in db.list_candidates():
            cols = st.columns([10,1])
            with cols[0]:
                st.markdown(f"<div class='card'><b>{cname}</b></div>", unsafe_allow_html=True)
            with cols[1]:
                if st.button("❌", key=f"remcand_{cid}"):
                    db.remove_candidate(cid)
                    st.experimental_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    elif tab == "Blockchain":
        st.header("Blockchain Explorer (hashed votes only)")
        bc = st.session_state.blockchain
        st.markdown("<div class='scroll-box'>", unsafe_allow_html=True)
        for blk in bc.chain:
            st.markdown(f"**Block #{blk.index}** — {blk.timestamp}")
            st.write(f"Hash: `{blk.hash}`")
            st.write(f"Prev: `{blk.previous_hash}`")
            st.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- VOTER UI ----------------
else:
    # Voter mode
    if tab == "Home":
        st.title("Welcome")
        st.write("This is the voter portal. If registration is open you can register. If voting is open you can vote.")
        st.write("")
        st.write(f"Registration open: **{state['registration_open']}**  — Voting open: **{state['voting_open']}**  — Election ended: **{state['ended']}**")
        if st.button("Results"):
            if not state['ended']:
                st.info("Voting not ended yet.")
            else:
                results = db.tally_results()
                if not results:
                    st.info("No votes recorded.")
                else:
                    df = pd.DataFrame(list(results.items()), columns=["Candidate","Votes"])
                    st.bar_chart(df.set_index("Candidate")["Votes"])
                    st.table(df)

    elif tab == "Register":
        st.header("Register to vote")
        if not state['registration_open']:
            st.info("Registration is currently closed.")
        else:
            with st.form("register_form"):
                name = st.text_input("Full name")
                dob = st.date_input(
    "Date of birth",
    min_value=date(1900, 1, 1),
    max_value=date.today()
)

                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Register and send verification email")
                if submitted:
                    # basic checks
                    if not name.strip() or not email.strip() or not password:
                        st.error("Please fill all fields.")
                    else:
                        # age check
                        today = date.today()
                        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                        if age < 18:
                            st.error("You must be at least 18 to register.")
                        else:
                            ok,msg = db.add_voter(name, dob.strftime("%Y-%m-%d"), email, password)
                            if not ok:
                                st.warning(msg)
                            else:
                                # create verification token and send email (if configured)
                                token = make_token = pysecrets.token_urlsafe(24)
                                db.store_verification_token(email, token)
                                verification_link = st.request_host_url() + "?" + "mode=voter&verify=" + token
                                sent, send_msg = send_verification_email(email, verification_link)
                                if sent:
                                    st.success("Registered — verification email sent. Check your inbox.")
                                else:
                                    st.warning("Registered, but verification email could not be sent (check SMTP). The verification link is shown below.")
                                    st.code(verification_link)

    elif tab == "Vote":
        st.header("Vote")
        if not state['voting_open']:
            st.info("Voting not open.")
        else:
            candidates = db.list_candidates()
            if not candidates:
                st.info("No candidates available yet.")
            else:
                # candidate selection boxes (visual)
                st.write("Click a candidate to select (only one).")
                # store selection in session_state to persist across reruns
                if "selected_candidate" not in st.session_state:
                    st.session_state.selected_candidate = None

                # render candidate boxes; clicking sets session_state.selected_candidate
                for cid, cname in candidates:
                    # create a unique key per candidate for the button
                    key = f"cand_btn_{cid}"
                    selected = (st.session_state.selected_candidate == cname)
                    box_class = "candidate-box selected" if selected else "candidate-box"
                    cols = st.columns([10,1])
                    with cols[0]:
                        st.markdown(f"<div class='{box_class}'>{cname}</div>", unsafe_allow_html=True)
                    with cols[1]:
                        if st.button("Select", key=key):
                            st.session_state.selected_candidate = cname
                            st.experimental_rerun()

                st.markdown("---")
                st.write("When ready, confirm your choice. You will be asked to enter your credentials (email + password) to finalize the vote.")

                if st.session_state.get("selected_candidate", None):
                    if st.button("Confirm Choice"):
                        # open a modal to request credentials
                        with st.modal("Confirm Credentials"):
                            st.write("Enter your registered email and password to confirm your vote.")
                            v_email = st.text_input("Registered email", key="confirm_email")
                            v_pass = st.text_input("Password", type="password", key="confirm_pass")
                            if st.button("Submit Vote (final)"):
                                voter = db.get_voter_by_email(v_email)
                                if not voter:
                                    st.error("No registered voter with that email.")
                                else:
                                    vid, full_name, dob, email, pwd, verified, has_voted, reg_at = voter
                                    # case-insensitive name not used here; we check email+password
                                    if not verified:
                                        st.error("Email not verified. Please verify your email before voting.")
                                    elif has_voted:
                                        st.warning("You have already voted.")
                                    elif pwd != v_pass:
                                        st.error("Wrong password.")
                                    else:
                                        # create fingerprint and record
                                        nonce = pysecrets.token_urlsafe(12)
                                        fingerprint = make_vote_fingerprint(email, st.session_state.selected_candidate, nonce)
                                        # add to blockchain (only fingerprint)
                                        blk = st.session_state.blockchain.add_block(fingerprint)
                                        # insert a DB vote record for tallying (stores hashed voter id, candidate)
                                        db.insert_vote_record(voter_hash_for_db(email), st.session_state.selected_candidate)
                                        # mark voter as voted
                                        db.update_voter_voted(email)
                                        st.success(f"Vote recorded on block #{blk.index}. Thank you!")
                                        # clear selection
                                        st.session_state.selected_candidate = None
                                        st.experimental_rerun()

    elif tab == "Blockchain":
        st.header("Blockchain Explorer (hashed votes only)")
        st.markdown("<div class='scroll-box'>", unsafe_allow_html=True)
        for blk in st.session_state.blockchain.chain:
            st.markdown(f"**Block #{blk.index}** — {blk.timestamp}")
            st.write(f"Hash: `{blk.hash}`")
            st.write(f"Prev: `{blk.previous_hash}`")
            st.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- verify token handler ----------------
verify_token = st.experimental_get_query_params().get("verify", [None])[0]
if verify_token:
    email = db.get_email_by_token(verify_token)
    if email:
        db.mark_verified(email)
        db.delete_token(verify_token)
        st.success(f"Email {email} verified — you can now vote when voting opens.")
        # clear query param by reloading without it
        st.experimental_set_query_params(mode="voter")
