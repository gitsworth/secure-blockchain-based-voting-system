import sqlite3
import hashlib

DB_NAME = "voters.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Voter table
    c.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            dob TEXT,
            email TEXT UNIQUE,
            has_voted INTEGER DEFAULT 0
        )
    """)
    # Candidates table
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_voter(full_name, dob, email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO voters (full_name, dob, email) VALUES (?, ?, ?)",
                  (full_name, dob, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate email
    finally:
        conn.close()

def get_voter_by_email(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM voters WHERE email=?", (email,))
    voter = c.fetchone()
    conn.close()
    return voter

def mark_voted(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE voters SET has_voted=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()

def add_candidate(name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO candidates (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_candidates():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM candidates")
    candidates = c.fetchall()
    conn.close()
    return candidates
