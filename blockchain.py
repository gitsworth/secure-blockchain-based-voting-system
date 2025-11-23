import hashlib
import datetime
import json

class Block:
    def __init__(self, index, timestamp, vote_hash, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.vote_hash = vote_hash
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "vote_hash": self.vote_hash,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, str(datetime.datetime.now()), "Genesis Block", "0")
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, vote_hash):
        index = self.last_block.index + 1
        timestamp = str(datetime.datetime.now())
        previous_hash = self.last_block.hash
        block = Block(index, timestamp, vote_hash, previous_hash)
        self.chain.append(block)
        return block

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i-1]
            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != prev.hash:
                return False
        return True
