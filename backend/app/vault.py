"""
Encrypted credential vault.
Device usernames/passwords are stored encrypted at rest using Fernet
(AES-128-CBC + HMAC). The VAULT_KEY must be provided via environment
variable and never committed to source control.
"""
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings


class VaultError(Exception):
    pass


def _get_fernet() -> Fernet:
    if not settings.VAULT_KEY:
        raise VaultError(
            "VAULT_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and set it as an environment variable."
        )
    return Fernet(settings.VAULT_KEY.encode())


def encrypt_secret(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise VaultError("Failed to decrypt credential - VAULT_KEY may have changed or data is corrupt.")
