"""
Utilidades de seguridad: hashing de contraseñas y JWT.
Login MVP: usuario y contraseña propios (sin SSO), 1 solo usuario en el arranque.

Nota: se usa bcrypt directamente (no passlib). passlib no se actualiza desde 2020
y es incompatible con bcrypt >= 4.1 (error conocido: 'password cannot be longer
than 72 bytes' incluso con contraseñas cortas, por un self-test interno de passlib
que rompe con la API nueva de bcrypt). bcrypt por si solo es simple y mantenido.
"""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 horas; ajustable mas adelante

BCRYPT_MAX_BYTES = 72  # limite duro de bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": subject, "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
