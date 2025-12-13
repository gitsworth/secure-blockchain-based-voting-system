import pandas as pd
import os
import sqlite3

# --- DATABASE MANAGEMENT ---

def load_voters(db_path):
    """
    Loads the voters list from a CSV file (acting as a simple database).
    Initializes an empty DataFrame if the file does not exist.
    """
    if os.path.exists(db_path):
        try:
            # We treat the public_key as the unique identifier index
            voters_df = pd.read_csv(db_path)
            # Ensure public_key is string type to avoid scientific notation issues
            voters_df['public_key'] = voters_df['public_key'].astype(str)
        except Exception:
            # Handle empty or corrupt file
            voters_df = initialize_voters_df()
    else:
        voters_df = initialize_voters_df()
        
    return voters_df

def initialize_voters_df():
    """Creates the initial, empty DataFrame structure."""
    return pd.DataFrame(columns=[
        'id',
        'name', 
        'email', 
        'public_key', # Voter ID
        'private_key', # Secret key
        'is_registered', 
        'has_voted',
        'registration_date'
    ])

def save_voters(voters_df, db_path):
    """Saves the current voters DataFrame to the CSV file."""
    voters_df.to_csv(db_path, index=False)

def update_voter_status(voters_df, public_key):
    """Marks a voter as having voted."""
    # Find the row by public_key
    mask = voters_df['public_key'].astype(str) == str(public_key)
    
    if mask.any():
        # Update the 'has_voted' column
        voters_df.loc[mask, 'has_voted'] = True
        return True
        
    return False
