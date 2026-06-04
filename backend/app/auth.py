import os
from datetime import datetime, timedelta
from jose import jwt
from passlib.hash import bcrypt

JWT_SECRET = os.getenv("JWT_SECRET","change_me_secret")
JWT_ALGO = os.getenv("JWT_ALGO","HS256")

def create_token(sub: str, role: str = "editor", expires_hours: int = 8):
    payload = {"sub": sub, "role": role, "exp": datetime.utcnow() + timedelta(hours=expires_hours)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)

def hash_password(password: str) -> str:
    return bcrypt.hash(password)
