import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import InvalidTokenError

from core.config import settings


def create_dev_keys(private_path: Path, public_path: Path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)


def get_keys() -> tuple[str, str]:
    private_path = Path(settings.PRIVATE_KEY_PATH)
    public_path = Path(settings.PUBLIC_KEY_PATH)

    if settings.DEBUG and (not private_path.exists() or not public_path.exists()):
        create_dev_keys(private_path, public_path)

    if not private_path.exists():
        raise RuntimeError(
            f"Private key not found: {private_path}"
        )

    if not public_path.exists():
        raise RuntimeError(
            f"Public key not found: {public_path}"
        )

    return (
        private_path.read_text(),
        public_path.read_text(),
    )


private_key, public_key = get_keys()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
    ).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(hash_token(token), token_hash)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_payload() -> dict:
    now = utcnow()
    return {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
    }


def create_access_token(*, user_id: int, person_id: str, role: int, session_id: int) -> str:
    expire = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        **new_payload(),
        "sub": str(user_id),
        "person_id": person_id,
        "role": role,
        "sid": session_id,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, private_key, algorithm=settings.ALGORITHM)


def create_refresh_token(*, user_id: int, session_id: int) -> tuple[str, datetime]:
    expire = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        **new_payload(),
        "sub": str(user_id),
        "sid": session_id,
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),
        "exp": expire,
    }
    token = jwt.encode(payload, private_key, algorithm=settings.ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        public_key,
        algorithms=[settings.ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
        options={"require": ["exp", "iat", "nbf", "sub", "type"]},
    )
