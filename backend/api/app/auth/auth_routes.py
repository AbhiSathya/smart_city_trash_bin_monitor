from fastapi import APIRouter, HTTPException, Depends   # type: ignore
from fastapi.security import OAuth2PasswordRequestForm  # type: ignore
from sqlalchemy import text                        # type: ignore
from passlib.context import CryptContext        # type: ignore
from app.db import engine
from app.auth.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password

    with engine.connect() as conn:
        user = conn.execute(
            text("""
                SELECT username, password_hash, role
                FROM api_users
                WHERE username = :username
            """),
            {"username": username}
        ).mappings().first()

    if not user or not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": user["username"],
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
