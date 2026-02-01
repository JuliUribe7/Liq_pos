# utils.py
import hashlib

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def verify_password(pw: str, stored_hash: str) -> bool:
    return hash_password(pw) == stored_hash
