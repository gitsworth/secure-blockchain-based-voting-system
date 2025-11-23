# blockchain.py
import hashlib
from datetime import datetime
from typing import List, Dict, Any

class Block:
    def __init__(self, index: int, timestamp: str, data: str, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data          # only a hash/fingerprint representing a vote
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        payload = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, datetime.utcnow().isoformat(), "Genesis Block", "0")
        self.chain = [genesis]

    def last_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, data: str) -> Block:
        prev = self.last_block()
        new_index = prev.index + 1
        new_block = Block(new_index, datetime.utcnow().isoformat(), data, prev.hash)
        self.chain.append(new_block)
        return new_block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            cur = self.chain[i]
            prev = self.chain[i-1]
            if cur.previous_hash != prev.hash:
                return False
            if cur.compute_hash() != cur.hash:
                return False
        return True
