from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.models.security import User


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.utcnow()
    db.commit()
    return user


def build_token_for_user(user: User) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"email": user.email})
