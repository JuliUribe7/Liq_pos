# utils.py
import bcrypt


def hash_password(pw: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw.encode("utf-8"), salt).decode("utf-8")


def verify_password(pw: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(pw.encode("utf-8"), stored_hash.encode("utf-8"))
