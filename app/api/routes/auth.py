from fastapi import APIRouter, Depends, Form, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.auth import login_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/jwt/login", response_model=TokenResponse, status_code=status.HTTP_200_OK
)
def login(
    payload: LoginRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """логинит пользователя и выдает токен"""

    token = login_user(db, payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.post(
    "/token", response_model=TokenResponse, status_code=status.HTTP_200_OK
)
def login_for_swagger(
    email: str = Form(..., description="email пользователя"),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """логинит пользователя через swagger oauth2 form"""

    token = login_user(db, email, password)
    return TokenResponse(access_token=token)


@router.get(
    "/users/me", response_model=UserRead, status_code=status.HTTP_200_OK
)
def read_me(user=Depends(get_current_user)) -> UserRead:
    """возвращает текущего пользователя"""

    return UserRead.model_validate(user)
