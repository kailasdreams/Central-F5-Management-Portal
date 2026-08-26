"""
Run this once before first startup to generate the secrets required in
backend/.env. Usage:
    python generate_keys.py
Then copy the printed values into backend/.env (see backend/.env.example).
"""
import secrets
from cryptography.fernet import Fernet

print("VAULT_KEY=" + Fernet.generate_key().decode())
print("JWT_SECRET_KEY=" + secrets.token_hex(32))
