# database.py
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional

DB = "voters.db"
MAX_VOTERS = 100
MAX_CANDIDATES = 5

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            dob TEXT,
            email TEXT UNIQUE,
            password TEXT,
            verified INTEGER DEFAULT 0,
            has_voted INTEGER DEFAULT 0,
            registered_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_hash TEXT,
            candidate TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS election_state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            registration_open INTEGER DEFAULT 0,
            voting_open INTEGER DEFAULT 0,
            ended INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS verification_tokens (
            email TEXT UNIQUE,
            token TEXT,
            created_at TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO election_state (id, registration_open, voting_open, ended) VALUES (1,0,0,0)")
    conn.commit()
    conn.close()

# ----------------- election state -----------------
def get_state() -> Dict[str,bool]:
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT registration_open, voting_open, ended FROM election_state WHERE id=1")
    row = c.fetchone(); conn.close()
    if not row:
        return {'registration_open': False, 'voting_open': False, 'ended': False}
    return {'registration_open': bool(row[0]), 'voting_open': bool(row[1]), 'ended': bool(row[2])}

def set_registration(open_bool: bool):
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE election_state SET registration_open=?, voting_open=0, ended=0 WHERE id=1", (1 if open_bool else 0,))
    conn.commit(); conn.close()

def start_voting():
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE election_state SET registration_open=0, voting_open=1, ended=0 WHERE id=1")
    conn.commit(); conn.close()

def end_voting():
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE election_state SET registration_open=0, voting_open=0, ended=1 WHERE id=1")
    conn.commit(); conn.close()

# ----------------- voters -----------------
def count_voters() -> int:
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM voters"); n=c.fetchone()[0]; conn.close(); return n

def add_voter(full_name: str, dob: str, email: str, password: str) -> Tuple[bool,str]:
    """
    Add voter. Reject if:
      - DB already contains the same (name + dob + email) combination
      - email already exists (UNIQUE)
      - max voters reached
    """
    if count_voters() >= MAX_VOTERS:
        return False, "Voter limit reached (100)."

    normalized_name = ' '.join(part.strip() for part in full_name.split())
    conn=get_conn(); c=conn.cursor()

    # strict duplicate: same name + dob + email
    c.execute("SELECT id FROM voters WHERE lower(full_name)=? AND dob=? AND lower(email)=?",
              (normalized_name.lower(), dob, email.strip().lower()))
    if c.fetchone():
        conn.close()
        return False, "Duplicate registration (same name + DOB + email)."

    try:
        c.execute("INSERT INTO voters (full_name, dob, email, password, registered_at) VALUES (?, ?, ?, ?, ?)",
                  (normalized_name, dob, email.strip().lower(), password, datetime.utcnow().isoformat()))
        conn.commit(); conn.close()
        return True, "Registered (pending email verification)."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already registered."

def list_voters() -> List[Tuple]:
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id, full_name, dob, email, verified, has_voted, registered_at FROM voters ORDER BY id")
    rows=c.fetchall(); conn.close(); return rows

def get_voter_by_email(email: str) -> Optional[tuple]:
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id, full_name, dob, email, password, verified, has_voted FROM voters WHERE email=?", (email.strip().lower(),))
    row=c.fetchone(); conn.close(); return row

def mark_verified(email: str):
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE voters SET verified=1 WHERE email=?", (email.strip().lower(),))
    conn.commit(); conn.close()

def update_voter_voted(email: str):
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE voters SET has_voted=1 WHERE email=?", (email.strip().lower(),))
    conn.commit(); conn.close()

def remove_voter(voter_id: int):
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM voters WHERE id=?", (voter_id,))
    conn.commit(); conn.close()

# ----------------- candidates -----------------
def add_candidate(name: str) -> Tuple[bool,str]:
    if len(list_candidates()) >= MAX_CANDIDATES:
        return False, "Candidate limit reached (5)."
    conn=get_conn(); c=conn.cursor()
    try:
        c.execute("INSERT INTO candidates (name) VALUES (?)", (name.strip(),))
        conn.commit(); conn.close(); return True, "Candidate added."
    except sqlite3.IntegrityError:
        conn.close(); return False, "Candidate exists."

def list_candidates() -> List[Tuple]:
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id, name FROM candidates ORDER BY id")
    rows=c.fetchall(); conn.close(); return rows

def remove_candidate(cand_id: int):
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM candidates WHERE id=?", (cand_id,))
    conn.commit(); conn.close()

# ----------------- votes (DB copy for tally only) -----------------
def insert_vote_record(voter_hash: str, candidate: str):
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO votes (voter_hash, candidate, timestamp) VALUES (?, ?, ?)",
              (voter_hash, candidate, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def tally_results() -> Dict[str,int]:
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT candidate, COUNT(*) FROM votes GROUP BY candidate")
    rows=c.fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

# ----------------- verification tokens -----------------
def store_verification_token(email: str, token: str):
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT OR REPLACE INTO verification_tokens (email, token, created_at) VALUES (?, ?, ?)",
              (email.strip().lower(), token, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def get_email_by_token(token: str) -> Optional[str]:
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT email FROM verification_tokens WHERE token=?", (token,))
    row=c.fetchone(); conn.close()
    return row[0] if row else None

def delete_token(token: str):
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM verification_tokens WHERE token=?", (token,))
    conn.commit(); conn.close()
