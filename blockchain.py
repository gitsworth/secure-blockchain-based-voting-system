import hashlib
import json
import time
from datetime import datetime
# Ensure these imports are ready at the start
from ecdsa import VerifyingKey, BadSignatureError, SECP256k1 
from ecdsa.util import sigencode_der, sigdecode_der

# --- BLOCK CLASS ---
# ... (rest of the file remains the same)
# --- BLOCK CLASS ---
class Block:
    """Represents a single block in the blockchain."""
    def __init__(self, index, timestamp, previous_hash, transactions, host_public_key, host_private_key, proof=0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.proof = proof
        self.host_public_key = host_public_key
        
        # Calculate and sign the hash immediately upon creation
        self.hash = self.calculate_hash()
        self.host_signature = self.sign_block(host_private_key)

    def calculate_hash(self):
        """Creates a SHA256 hash of the block's contents."""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'proof': self.proof,
            'host_public_key': self.host_public_key 
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def sign_block(self, host_private_key):
        """Signs the block's hash using the Host's Private Key (Proof-of-Authority)."""
        if not host_private_key:
            raise ValueError("Host Private Key required to sign the block.")
        
        # Load Private Key for signing
        try:
            from ecdsa import SigningKey
            sk = SigningKey.from_string(bytes.fromhex(host_private_key), curve=SECP256k1)
            
            # Sign the block's hash
            signature = sk.sign_with_hash(bytes.fromhex(self.hash), sigencode=sigencode_der)
            return signature.hex()
        except Exception as e:
            print(f"Error signing block: {e}")
            return None

    def verify_signature(self):
        """Verifies the block's signature against the stored Host Public Key."""
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(self.host_public_key), curve=SECP256k1)
            
            # The data signed is the calculated hash of the block's contents
            calculated_hash = self.calculate_hash()
            
            # Verify the signature against the calculated hash
            return vk.verify(
                bytes.fromhex(self.host_signature),
                bytes.fromhex(calculated_hash),
                sigdecode=sigdecode_der
            )
        except BadSignatureError:
            return False
        except Exception as e:
            print(f"Verification Error: {e}")
            return False
            
    def to_dict(self):
        """Converts the block object to a dictionary for JSON serialization."""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'transactions': self.transactions,
            'host_signature': self.host_signature,
            'host_public_key': self.host_public_key,
            'hash': self.hash,
            'proof': self.proof
        }

    @classmethod
    def from_dict(cls, data):
        """Creates a Block object from a dictionary."""
        # Create a dummy block first to avoid circular dependency in __init__
        block = cls(
            index=data['index'],
            timestamp=data['timestamp'],
            previous_hash=data['previous_hash'],
            transactions=data['transactions'],
            host_public_key=data['host_public_key'],
            host_private_key=None, # Private key is not stored in the block
            proof=data.get('proof', 0)
        )
        # Manually set the calculated hash and signature from the loaded data
        block.hash = data['hash']
        block.host_signature = data['host_signature']
        return block

# --- BLOCKCHAIN CLASS ---
class Blockchain:
    """Manages the chain, adding new blocks and verifying integrity."""
    def __init__(self, host_public_key, host_private_key, filename):
        self.host_public_key = host_public_key
        self.host_private_key = host_private_key
        self.filename = filename
        self.chain = self.load_chain()
        self.current_transactions = []

        if not self.chain:
            self.create_genesis_block()

    def create_genesis_block(self):
        """Creates the first block in the chain."""
        genesis = Block(
            index=0,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            previous_hash="0",
            transactions=[{"message": "Genesis Block - Blockchain initialized"}],
            host_public_key=self.host_public_key,
            host_private_key=self.host_private_key
        )
        self.chain.append(genesis)
        self.save_chain()

    @property
    def last_block(self):
        """Returns the last block in the chain."""
        return self.chain[-1]

    def new_transaction(self, sender, recipient, vote):
        """Adds a new vote transaction to be included in the next block."""
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'vote': vote,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self.last_block.index + 1

    def new_block(self, proof=0):
        """Mines a new block and adds it to the chain."""
        block = Block(
            index=len(self.chain),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            previous_hash=self.last_block.hash,
            transactions=self.current_transactions,
            host_public_key=self.host_public_key,
            host_private_key=self.host_private_key,
            proof=proof
        )
        
        # Reset the current list of transactions
        self.current_transactions = []
        
        # Add the new block and save the updated chain
        self.chain.append(block)
        self.save_chain()
        return block

    def is_valid(self):
        """Determines if a given blockchain is valid by checking hashes and signatures."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            # 1. Check if the block's stored hash is correct
            if current_block.hash != current_block.calculate_hash():
                print(f"Chain check failed: Block {i} hash mismatch.")
                return False

            # 2. Check if the previous_hash link is correct
            if current_block.previous_hash != previous_block.hash:
                print(f"Chain check failed: Block {i} previous hash mismatch.")
                return False
                
            # 3. Verify the Host's digital signature
            # IMPORTANT: We verify using the public key stored *in the block*, 
            # ensuring it matches the expected host authority.
            if not current_block.verify_signature():
                print(f"Chain check failed: Block {i} signature invalid.")
                return False

        return True

    def save_chain(self):
        """Saves the blockchain to a JSON file."""
        chain_data = [block.to_dict() for block in self.chain]
        with open(self.filename, 'w') as f:
            json.dump(chain_data, f, indent=4)
            
    def load_chain(self):
        """Loads the blockchain from a JSON file."""
        try:
            with open(self.filename, 'r') as f:
                chain_data = json.load(f)
                chain = [Block.from_dict(data) for data in chain_data]
                return chain
        except (FileNotFoundError, json.JSONDecodeError):
            return []
