# database.py
import sqlite3
from datetime import datetime

DB = "voters.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    try:
        conn = get_conn()
        c = conn.cursor()
        # voters table
        c.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                dob TEXT,
                email TEXT UNIQUE,
                password TEXT,
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
        # votes table
        c.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_hash TEXT,
                candidate TEXT,
                timestamp TEXT
            )
        """)
        # election state table
        c.execute("""
            CREATE TABLE IF NOT EXISTS election_state (
                id INTEGER PRIMARY KEY CHECK(id=1),
                registration_open INTEGER DEFAULT 0,
                voting_open INTEGER DEFAULT 0,
                ended INTEGER DEFAULT 0
            )
        """)
        c.execute("INSERT OR IGNORE INTO election_state (id, registration_open, voting_open, ended) VALUES (1,0,0,0)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise e

# ------------------------ VOTER / CANDIDATE OPERATIONS ------------------------

def add_voter(full_name, dob, email, password):
    conn = get_conn()
    c = conn.cursor()
    normalized = ' '.join(part.strip() for part in full_name.split()).lower()
    try:
        c.execute("INSERT INTO voters (full_name, dob, email, password) VALUES (?, ?, ?, ?)",
                  (normalized, dob, email.strip().lower(), password))
        conn.commit(); conn.close()
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
    try:
        c.execute("INSERT INTO candidates (name) VALUES (?)", (name.strip(),))
        conn.commit(); conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def list_candidates():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id, name FROM candidates ORDER BY id"); rows=c.fetchall(); conn.close()
    return rows

def count_voters():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM voters"); n=c.fetchone()[0]; conn.close()
    return n

def tally_results():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT candidate, COUNT(*) FROM votes GROUP BY candidate")
    rows=c.fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

# ------------------------ ELECTION STATE ------------------------

def get_state():
    conn = get_conn(); c = conn.cursor()
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
