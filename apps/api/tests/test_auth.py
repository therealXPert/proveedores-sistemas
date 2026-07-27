from app.services.auth_service import authenticate_user, build_token_for_user
from app.core.security import decode_access_token, hash_password, verify_password


def test_password_hash_and_verify():
    hashed = hash_password("MiPassword123!")
    assert hashed != "MiPassword123!"
    assert verify_password("MiPassword123!", hashed)
    assert not verify_password("otra-cosa", hashed)


def test_authenticate_user_success(db_session, admin_user):
    user = authenticate_user(db_session, "admin@test.com", "Password123!")
    assert user is not None
    assert user.email == "admin@test.com"


def test_authenticate_user_wrong_password(db_session, admin_user):
    user = authenticate_user(db_session, "admin@test.com", "incorrecta")
    assert user is None


def test_authenticate_user_unknown_email(db_session, admin_user):
    user = authenticate_user(db_session, "no-existe@test.com", "cualquiera")
    assert user is None


def test_token_roundtrip(admin_user):
    token = build_token_for_user(admin_user)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(admin_user.id)
    assert payload["email"] == "admin@test.com"


def test_user_roles_property(admin_user):
    assert admin_user.roles == ["Administrador"]
