from fastapi import Depends, HTTPException, status, Request         # type: ignore
from fastapi.security import OAuth2PasswordBearer                   # type: ignore
from jose import jwt, JWTError                         # type: ignore  
from sqlalchemy import text         # type: ignore
from app.db import engine
from app.auth.jwt import SECRET_KEY, ALGORITHM
from app.middleware.rate_limit import rate_limiter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    with engine.connect() as conn:
        user = conn.execute(
            text("""
                SELECT username, role, is_active
                FROM api_users
                WHERE username = :username
            """),
            {"username": username}
        ).mappings().first()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Inactive user")

    request.state.user = user
    return user


def require_role(required_roles: list):
    async def role_checker(
        request: Request,
        user=Depends(get_current_user),
    ):
        if user["role"] not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        # 🔥 RATE LIMIT AFTER AUTH
        await rate_limiter(request)

        return user

    return role_checker

