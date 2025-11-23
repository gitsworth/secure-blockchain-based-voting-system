import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Import core blockchain and wallet logic
from blockchain import Blockchain
from wallet import generate_key_pair
from database import load_voters, save_voters, update_voter_status
from email_utils import send_email # Now uses yagmail/SMTP

# --- HOST KEYS ---
# ⚠️ CRITICAL STEP 1: Paste the unique keys you generated here!
# These keys are required for the Host Authority to sign all blocks (Proof-of-Authority)
HOST_PUBLIC_KEY = "'59f7315aac41eee895e32a095a11ece8f9f270c2a24b61d48870727e56f0cdac1b1653812f3f246c1d513a2757fc9aa547b1be6c1e0d8ac779560c2a7554c3b3"  # PASTE THE SECOND STRING HERE
HOST_PRIVATE_KEY = "30132997b575254fe80a7ff388324e257b0f787e10279f68c083a0f769c3625b" # PASTE THE FIRST STRING HERE

# --- CONFIGURATION (CRITICAL for Email) ---
DB_PATH = 'voters.db'
BLOCKCHAIN_PATH = 'blockchain_data.json'

# ⚠️ CRITICAL STEP 2: Configure your email credentials here for the registration feature.
# Use the email address that will send the email and the corresponding App Password or SMTP API Key.
# The email feature will fail if these are left as placeholders.
SMTP_SENDER_EMAIL = "host@example.com" 
SMTP_API_KEY = "your_smtp_api_key_or_app_password" 


# --- INITIALIZATION ---
# Initialize the Blockchain and Database
try:
    blockchain = Blockchain(HOST_PUBLIC_KEY, HOST_PRIVATE_KEY, BLOCKCHAIN_PATH)
except Exception as e:
    st.error(f"Error initializing Blockchain: {e}")
    st.stop()

# Initialize voters DataFrame
voters_df = load_voters(DB_PATH)

# --- STREAMLIT PAGE SETUP ---
st.set_page_config(layout="wide", page_title="Secure Blockchain Voting System - Host Portal")

# Custom CSS for styling
st.markdown("""
<style>
    .stApp {
        background-color: #f7f9fc;
    }
    .header {
        font-size: 32px;
        font-weight: bold;
        color: #1e40af;
        border-bottom: 2px solid #1e40af;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        transition: all 0.2s;
        box-shadow: 0 4px #1e40af;
    }
    .stButton>button:hover {
        background-color: #2563eb;
    }
    .key-box {
        background-color: #e0f2fe;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #93c5fd;
        margin-bottom: 15px;
        word-wrap: break-word;
    }
    .success-box {
        background-color: #d1fae5;
        color: #065f46;
        padding: 10px;
        border-radius: 5px;
    }
    .error-box {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 10px;
        border-radius: 5px;
    }
    /* Hide the default Streamlit footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def display_host_portal():
    st.markdown('<div class="header">Host Authority Portal: Election Setup & Monitoring</div>', unsafe_allow_html=True)

    # Display Host Public Key for transparency
    st.subheader("Host Public Key (Authority ID)")
    st.markdown(f'<div class="key-box"><strong>{HOST_PUBLIC_KEY}</strong></div>', unsafe_allow_html=True)
    st.info("This key signs all validated blocks. It is visible to all voters.")
    
    # Display Email Configuration Warning
    if SMTP_SENDER_EMAIL == "host@example.com" or SMTP_API_KEY == "your_smtp_api_key_or_app_password":
        st.warning("⚠️ EMAIL FEATURE WARNING: Please update the `SMTP_SENDER_EMAIL` and `SMTP_API_KEY` in `app.py` before registering real voters, or email delivery will fail.")


    # --- Sidebar for Navigation ---
    st.sidebar.title("Navigation")
    portal_selection = st.sidebar.radio(
        "Go to",
        ["Election Configuration", "Voter Registration", "Blockchain Audit"]
    )

    if portal_selection == "Election Configuration":
        election_config_page()
    elif portal_selection == "Voter Registration":
        voter_registration_page()
    elif portal_selection == "Blockchain Audit":
        blockchain_audit_page()

def election_config_page():
    st.header("1. Election Configuration")
    
    # Initialize session state for candidates
    st.session_state.setdefault('candidates', ["Candidate A", "Candidate B", "Candidate C"])
    
    st.markdown("Edit the list of candidates below. Each candidate must have a unique name.")
    
    # Allow user to edit candidates
    candidates_input = st.text_area(
        "Candidates (one per line)",
        value="\n".join(st.session_state.candidates),
        height=150
    )

    new_candidates = [c.strip() for c in candidates_input.split('\n') if c.strip()]
    if new_candidates:
        st.session_state.candidates = new_candidates
        st.success("Candidate list updated.")
    else:
        st.error("Please enter at least one candidate.")

    st.subheader("Current Candidates:")
    for i, candidate in enumerate(st.session_state.candidates):
        st.write(f"{i+1}. **{candidate}**")

    st.markdown("---")

    # --- Election Results ---
    st.header("2. Real-Time Election Results")
    
    # Tally votes from the blockchain
    vote_tally = {}
    for candidate in st.session_state.candidates:
        vote_tally[candidate] = 0

    all_transactions = [block.transactions for block in blockchain.chain]
    for block_txs in all_transactions:
        for tx in block_txs:
            if 'vote' in tx and tx['vote'] in vote_tally:
                vote_tally[tx['vote']] += 1

    # Convert tally to DataFrame for visualization
    results_df = pd.DataFrame(
        list(vote_tally.items()),
        columns=['Candidate', 'Votes']
    ).sort_values(by='Votes', ascending=False).reset_index(drop=True)

    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    # Display Chart
    st.bar_chart(results_df.set_index('Candidate'))
    
    # --- Manual Vote Validation/Block Mining ---
    st.markdown("---")
    st.subheader("Block Mining (Vote Validation)")
    pending_votes = len(blockchain.current_transactions)
    st.info(f"There are **{pending_votes}** pending votes in the current transaction pool.")
    
    if st.button("Mine New Block (Validate Pending Votes)"):
        if pending_votes > 0:
            new_block = blockchain.new_block()
            st.markdown(f'<div class="success-box">✅ New Block #{new_block.index} Mined and added to the chain! {pending_votes} votes validated.</div>', unsafe_allow_html=True)
            # Need to re-run the script to refresh the results
            st.rerun() 
        else:
            st.warning("No pending votes to mine into a new block.")


def voter_registration_page():
    global voters_df
    st.header("Voter Registration")

    with st.form("voter_form"):
        st.subheader("Register New Voter")
        name = st.text_input("Full Name", max_chars=100).strip()
        email = st.text_input("Email Address").strip().lower()

        submitted = st.form_submit_button("Register Voter & Generate Wallet")

        if submitted:
            if not name or not email:
                st.markdown('<div class="error-box">Please fill in both Name and Email.</div>', unsafe_allow_html=True)
                st.stop()
            
            # 1. Check if voter already exists
            if email in voters_df['email'].values:
                st.markdown('<div class="error-box">Voter with this email is already registered.</div>', unsafe_allow_html=True)
                st.stop()
            
            # 2. Generate Key Pair (Wallet)
            private_key, public_key = generate_key_pair()
            
            # 3. Create a unique Voter ID (Public Key is the unique ID)
            new_voter = {
                'name': name,
                'email': email,
                'public_key': public_key,
                'private_key': private_key,
                'is_registered': True,
                'has_voted': False,
                'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 4. Add to DataFrame and Save Database
            voters_df = pd.concat([voters_df, pd.DataFrame([new_voter])], ignore_index=True)
            save_voters(voters_df, DB_PATH)
            
            # 5. Send Email with Credentials
            email_success = send_email(
                SMTP_SENDER_EMAIL,
                SMTP_API_KEY,
                email,
                "Your Secure Voting Credentials",
                f"Thank you for registering for the election, {name}. Use these keys in the Voter Portal to cast your ballot.",
                private_key, 
                public_key
            )
            
            st.markdown('<div class="success-box">Voter Registered Successfully!</div>', unsafe_allow_html=True)
            if email_success:
                 st.success("Credentials emailed successfully (check spam)!")
            else:
                 st.error("Credentials generated, but **EMAIL FAILED**. Check your SMTP configuration in `app.py`. Please securely copy the keys below.")
            
            st.subheader("Voter's Credentials (Securely share this with the voter)")
            
            # Display credentials for copying
            st.code(f"PUBLIC KEY (Voter ID):\n{public_key}", language='text')
            st.code(f"PRIVATE KEY (Secret Wallet):\n{private_key}", language='text')
            
            # Rerun to clear form and update voter list
            time.sleep(1)
            st.rerun()

    st.markdown("---")
    st.header("Registered Voters")
    if not voters_df.empty:
        # Display registered voters, hiding the private key for safety
        display_df = voters_df.drop(columns=['private_key']).sort_values(by='registration_date', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No voters registered yet.")


def blockchain_audit_page():
    st.header("Blockchain Audit")

    # 1. Display Chain Integrity Status
    st.subheader("Chain Integrity Check")
    if blockchain.is_valid():
        st.markdown('<div class="success-box">✅ Blockchain Integrity is VALID. All blocks are signed correctly by the Host Authority.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="error-box">🚨 Blockchain Integrity Check FAILED! The chain may have been tampered with.</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 2. Display the Chain Length
    st.subheader(f"Total Blocks: {len(blockchain.chain)}")
    st.write(f"The Genesis Block (Block #0) was created on: **{blockchain.chain[0].timestamp}**")
    
    st.markdown("---")

    # 3. Display all Blocks in Detail
    st.subheader("Block Details")
    
    # Reverse the chain for display (newest first)
    for i, block in enumerate(reversed(blockchain.chain)):
        
        # Calculate original index
        original_index = len(blockchain.chain) - 1 - i
        
        with st.expander(f"Block #{original_index} (Time: {block.timestamp})", expanded=True if original_index == len(blockchain.chain) - 1 else False):
            st.json({
                "index": block.index,
                "timestamp": block.timestamp,
                "previous_hash": block.previous_hash,
                "host_signature": block.host_signature,
                "transactions": block.transactions,
                "current_hash": block.hash
            })

# --- VOTER PORTAL STAND-IN ---
# This section simulates the voter's experience for testing, but ideally should be in a separate file.
def voter_portal_standin():
    global voters_df
    
    st.markdown('<div class="header" style="color:#059669; border-bottom: 2px solid #059669;">Voter Portal (Simulation)</div>', unsafe_allow_html=True)
    st.info("Use this section to test the voting process using the credentials generated in the Host Portal.")
    
    st.session_state.setdefault('candidates', ["Candidate A", "Candidate B", "Candidate C"])

    with st.form("vote_form"):
        st.subheader("Cast Your Vote")
        
        voter_public_key = st.text_input("VOTER ID (Public Key)").strip()
        voter_private_key = st.text_input("SECRET WALLET KEY (Private Key)", type="password").strip()
        
        vote_selection = st.selectbox("Select Candidate", st.session_state.candidates)
        
        submit_vote = st.form_submit_button("Cast Vote Securely")
        
        if submit_vote:
            if not voter_public_key or not voter_private_key:
                st.error("Please enter both your Public Key and Private Key.")
                st.stop()
            
            # 1. Look up voter in database
            voter_row = voters_df[voters_df['public_key'] == voter_public_key]
            
            if voter_row.empty:
                st.error("Error: Invalid Voter ID (Public Key).")
                st.stop()
            
            # 2. Basic verification (Private Key match)
            if voter_row['private_key'].iloc[0] != voter_private_key:
                st.error("Error: Private Key does not match Voter ID.")
                st.stop()
                
            # 3. Check if already voted
            if voter_row['has_voted'].iloc[0]:
                st.warning("You have already cast your vote. Multiple votes are prevented.")
                st.stop()
                
            # 4. Prepare data and sign transaction
            data_to_sign = f"{voter_public_key}:{vote_selection}:{time.time()}"
            
            from wallet import sign_transaction, verify_signature # Import here to avoid circular dependency issues
            signature = sign_transaction(voter_private_key, data_to_sign)

            if not signature:
                st.error("Failed to sign transaction. Check private key format.")
                st.stop()
                
            # 5. Verify the signature (A final sanity check, simulating verification on the network)
            if not verify_signature(voter_public_key, data_to_sign, signature):
                st.error("Signature verification failed. Potential tampering detected.")
                st.stop()
                
            # 6. Create the transaction and add to blockchain's pool
            blockchain.new_transaction(
                sender=voter_public_key,
                recipient="ElectionAuthority",
                vote=vote_selection
            )
            
            # 7. Update database status
            update_voter_status(voters_df, voter_public_key)
            save_voters(voters_df, DB_PATH)
            
            st.markdown(f'<div class="success-box">✅ Vote successfully cast for **{vote_selection}**!</div>', unsafe_allow_html=True)
            st.info("Your vote is now in the transaction pool and will be validated when the Host mines the next block.")
            
            st.write("--- Transaction Details ---")
            st.json({
                "Voter ID": voter_public_key,
                "Candidate": vote_selection,
                "Raw Data Signed": data_to_sign,
                "Signature": signature
            })
            
            # Rerun to clear form
            time.sleep(1)
            st.rerun()

# --- RUN APPLICATION ---
if __name__ == "__main__":
    if HOST_PUBLIC_KEY == "PASTE_YOUR_PUBLIC_KEY_HERE" or HOST_PRIVATE_KEY == "PASTE_YOUR_PRIVATE_KEY_HERE":
        st.error("⚠️ CRITICAL ERROR: HOST KEYS NOT SET!")
        st.warning("Please run the key generation command (`py -c \"from wallet import generate_key_pair; print(generate_key_pair())\"`), copy the Private Key and Public Key, and paste them into lines 16 & 17 of your `app.py` file, then save and relaunch.")
        st.stop()

    # Layout: Host Portal on the left, Voter Portal on the right
    col1, col2 = st.columns([1, 1])

    with col1:
        display_host_portal()

    with col2:
        voter_portal_standin()
