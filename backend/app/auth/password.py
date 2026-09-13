import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hash plaintext password using bcrypt with standard salt rounds.
    Returns: UTF-8 encoded bcrypt hash string.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    # bcrypt limits passwords to 72 bytes
    password_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Securely verify plain password against stored bcrypt hash using constant-time check.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False
