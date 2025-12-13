import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime

# --- Module Imports ---
from database import load_voters, save_voters, update_voter_status 
from wallet import generate_key_pair, sign_transaction, verify_signature
from blockchain import Blockchain

# --- HOST KEYS ---
# ⚠️ REPLACE THESE WITH YOUR GENERATED KEYS
HOST_PUBLIC_KEY = "04f9812f864e29c8e29a99f18731d1020786522c07342921b777a824100c5c7d0d6118d052d9a3028211b777a824100c5c7d0d6118d052d9a3028211b714f3b573e35a11956e300109968412030040682121"
HOST_PRIVATE_KEY = "c8b4b74581f1d19d7e5d263a568c078864d2d4808386375354972e25d25e0c50"

# --- CONFIGURATION ---
DB_PATH = 'voters.csv' # Changed to CSV for simple pandas handling
BLOCKCHAIN_PATH = 'blockchain_data.json'

# --- INITIALIZATION ---

@st.cache_resource
def initialize_system():
    """Initialize the blockchain and load the voter database."""
    voters_df_init = load_voters(DB_PATH)
    try:
        bc = Blockchain(HOST_PUBLIC_KEY, HOST_PRIVATE_KEY, BLOCKCHAIN_PATH)
        if not bc.is_valid():
            st.warning("Blockchain integrity check failed on load. Chain may be compromised.")
        return voters_df_init, bc
    except Exception as e:
        st.error(f"Error initializing Blockchain: {e}")
        st.stop()

if 'blockchain' not in st.session_state:
    voters_df_init, bc = initialize_system()
    st.session_state.voters_df = voters_df_init
    st.session_state.blockchain = bc
    
blockchain = st.session_state.blockchain

# --- ELECTION STATE MANAGEMENT ---
if 'registration_open' not in st.session_state:
    st.session_state.registration_open = True
if 'voting_open' not in st.session_state:
    st.session_state.voting_open = False
if 'election_ended' not in st.session_state:
    st.session_state.election_ended = False
if 'candidates' not in st.session_state:
    st.session_state.candidates = ["Candidate A", "Candidate B", "Candidate C"]

# --- HELPER FUNCTIONS ---

def get_total_votes(candidates):
    results = {name: 0 for name in candidates}
    for block in blockchain.chain[1:]:
        for tx in block.transactions:
            vote_candidate = tx.get('candidate')
            if vote_candidate in results:
                results[vote_candidate] += 1
    return results

def get_voter_info(public_key):
    voters_df = st.session_state.voters_df
    # Ensure public_key lookup is correct
    return voters_df[voters_df['public_key'].astype(str) == str(public_key)]

# --- MAIN APP LAYOUT ---

st.set_page_config(layout="wide", page_title="Secure Blockchain Voting System")

st.markdown("""
    <style>
    .big-font { font-size:30px !important; font-weight: bold; color: #1E40AF; border-bottom: 2px solid #60A5FA; padding-bottom: 5px; margin-top: 10px; }
    .stButton>button { width: 100%; border-radius: 8px; padding: 10px 0; background-color: #10B981; color: white; font-size: 18px; font-weight: 700; }
    .stButton>button:hover { background-color: #059669; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Secure Blockchain-Based Voting System")

tab_host, tab_voter, tab_results, tab_ledger = st.tabs([
    "Host Portal (Registration & Setup)", 
    "Voter Portal (Casting Vote)", 
    "Election Results", 
    "Blockchain Ledger"
])

# ==============================================================================
# 1. HOST PORTAL
# ==============================================================================
with tab_host:
    st.markdown("<p class='big-font'>Host Authority Management</p>", unsafe_allow_html=True)
    st.code(f"HOST PUBLIC KEY: {HOST_PUBLIC_KEY}")
    
    st.subheader("Election Status Control")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.session_state.registration_open: st.success("Registration is OPEN")
        else: st.error("Registration is CLOSED")
    with col2:
        if st.session_state.voting_open: st.success("Voting is OPEN")
        else: st.warning("Voting is CLOSED")
    with col3:
        if st.session_state.election_ended: st.info("Election Ended")
        else: st.info("Election Active")
            
    st.markdown("---")
    
    # Candidate Management
    st.subheader("Candidate Management")
    new_candidates_text = st.text_area("Candidate List (One per line)", value="\n".join(st.session_state.candidates))
    if st.button("Update Candidates"):
        updated_list = [c.strip() for c in new_candidates_text.split('\n') if c.strip()]
        if not updated_list:
            st.error("List cannot be empty.")
        else:
            st.session_state.candidates = updated_list
            st.success("Updated!")
            st.rerun()

    st.markdown("---")

    # Registration Form
    st.markdown("<p class='big-font'>Voter Registration</p>", unsafe_allow_html=True)
    if st.session_state.registration_open:
        with st.form("voter_registration"):
            new_name = st.text_input("Voter Name")
            submitted = st.form_submit_button("Register & Generate Credentials")
            
            if submitted:
                voters_df = st.session_state.voters_df
                if not new_name:
                    st.error("Enter voter name.")
                elif new_name in voters_df['name'].values:
                    st.warning("Name already registered.")
                else:
                    private_key, public_key = generate_key_pair()
                    new_voter = pd.DataFrame([{
                        'id': voters_df['id'].max() + 1 if not voters_df.empty else 1,
                        'name': new_name,
                        'email': 'N/A', 
                        'public_key': public_key,
                        'private_key': private_key,
                        'is_registered': True,
                        'has_voted': False,
                        'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    
                    st.session_state.voters_df = pd.concat([voters_df, new_voter], ignore_index=True)
                    save_voters(st.session_state.voters_df, DB_PATH)
                    
                    st.success(f"Registered {new_name}!")
                    st.subheader("MANUAL CREDENTIAL COPY")
                    st.code(f"Public Key (ID): {public_key}")
                    st.code(f"Private Key (Secret): {private_key}")
                    st.rerun()
    else:
        st.info("Registration closed.")

    st.subheader("Current Registered Voters")
    st.dataframe(st.session_state.voters_df[['id', 'name', 'public_key', 'has_voted']], use_container_width=True)

    st.markdown("---")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("Open Voting"):
            st.session_state.registration_open = False
            st.session_state.voting_open = True
            st.session_state.election_ended = False
            st.rerun()
    with colB:
        if st.button("End Voting"):
            st.session_state.voting_open = False
            st.session_state.election_ended = True
            st.rerun()
    with colC:
        if st.button("Reset Election"):
            if st.button("CONFIRM RESET"):
                blockchain.reset_chain()
                st.session_state.voters_df['has_voted'] = False
                save_voters(st.session_state.voters_df, DB_PATH)
                st.session_state.registration_open = True
                st.session_state.voting_open = False
                st.session_state.election_ended = False
                st.success("Reset complete.")
                st.rerun()

# ==============================================================================
# 2. VOTER PORTAL
# ==============================================================================
with tab_voter:
    st.markdown("<p class='big-font'>Cast Your Secure Vote</p>", unsafe_allow_html=True)
    
    if st.session_state.voting_open and not st.session_state.election_ended:
        with st.form("vote_casting"):
            st.subheader("Identity Verification")
            # Added Name Input
            voter_name_input = st.text_input("Voter Name (As Registered)")
            voter_id = st.text_input("Voter ID (Public Key)")
            secret_key = st.text_input("Secret Wallet Key (Private Key)", type="password")
            
            st.subheader("Ballot")
            candidate = st.selectbox("Select Candidate:", st.session_state.candidates)
            
            cast_vote_button = st.form_submit_button("Cast Vote Securely")
            
            if cast_vote_button:
                if not voter_name_input or not voter_id or not secret_key:
                    st.error("Please fill in all fields (Name, Public Key, Private Key).")
                else:
                    voter_row = get_voter_info(voter_id)
                    
                    if voter_row.empty:
                        st.error("Invalid Voter ID.")
                    else:
                        voter_info = voter_row.iloc[0]
                        registered_name = str(voter_info['name'])
                        
                        # --- NAME VERIFICATION (Case-Insensitive) ---
                        if voter_name_input.strip().lower() != registered_name.strip().lower():
                            st.error(f"Authentication Failed: The name '{voter_name_input}' does not match the registered name for this Public Key.")
                        elif voter_info['has_voted']:
                            st.warning("You have already cast your vote.")
                        elif str(voter_info['private_key']) != str(secret_key):
                            st.error("Invalid Secret Wallet Key.")
                        else:
                            # Proceed with vote
                            data_to_sign = f"VOTE|{voter_id}|{candidate}|{datetime.now().isoformat()}"
                            signature = sign_transaction(secret_key, data_to_sign)
                            
                            if signature and verify_signature(voter_id, data_to_sign, signature):
                                blockchain.new_transaction(voter_id, candidate, candidate)
                                blockchain.new_block()
                                
                                if update_voter_status(st.session_state.voters_df, voter_id):
                                    save_voters(st.session_state.voters_df, DB_PATH)
                                    st.success(f"Vote cast for {candidate}!")
                                    st.rerun()
                                else:
                                    st.error("Database update failed.")
                            else:
                                st.error("Cryptographic verification failed.")
    elif st.session_state.election_ended:
        st.info("Election has ended.")
    else:
        st.warning("Voting is closed.")

# ==============================================================================
# 3. ELECTION RESULTS
# ==============================================================================
with tab_results:
    st.markdown("<p class='big-font'>Live Election Results</p>", unsafe_allow_html=True)
    results = get_total_votes(st.session_state.candidates)
    total_votes = sum(results.values())
    
    if st.session_state.election_ended: st.success("FINAL RESULTS")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Votes", total_votes)
    
    if total_votes > 0:
        results_df = pd.DataFrame(list(results.items()), columns=['Candidate', 'Votes'])
        st.bar_chart(results_df.set_index('Candidate'))
        st.dataframe(results_df)
    else:
        st.info("No votes yet.")

# ==============================================================================
# 4. BLOCKCHAIN LEDGER
# ==============================================================================
with tab_ledger:
    st.markdown("<p class='big-font'>Blockchain Ledger</p>", unsafe_allow_html=True)
    for block in reversed(blockchain.chain):
        with st.expander(f"Block #{block.index}"):
            st.write(block.to_dict())
