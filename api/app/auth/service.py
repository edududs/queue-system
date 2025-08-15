import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..exceptions import AuthenticationError
from ..models.users import User
from ..settings.config import settings
from . import models

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return bcrypt_context.hash(password)


def authenticate_user(username: str, password: str, db: Session) -> User | bool:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, str(user.hashed_password)):
        logging.warning(f"Failed authentication attempt for username: {username}")
        return False
    return user


def create_access_token(email: str, user_id: UUID, expires_delta: timedelta) -> str:
    encode = {
        "sub": email,
        "id": str(user_id),
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> models.TokenData:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("id")
        return models.TokenData(user_id=user_id)
    except PyJWTError as e:
        logging.warning(f"Token verification failed: {e!s}")
        raise AuthenticationError from e


def register_user(
    db: Session,
    register_user_request: models.RegisterUserRequest,
) -> None:
    try:
        create_user_model = User(
            id=uuid4(),
            username=register_user_request.username,
            email=register_user_request.email,
            first_name=register_user_request.first_name,
            last_name=register_user_request.last_name,
            hashed_password=get_password_hash(register_user_request.password),
        )
        db.add(create_user_model)
        db.commit()
    except Exception as e:
        logging.error(
            f"Failed to register user: {register_user_request.email}. Error: {e!s}",
        )
        raise


def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> models.TokenData:
    return verify_token(token)


CurrentUser = Annotated[models.TokenData, Depends(get_current_user)]


def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session,
    token_type: str = "bearer",
) -> models.Token:
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user or not isinstance(user, User):
        raise AuthenticationError
    token = create_access_token(
        str(user.email),
        UUID(str(user.id)),
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return models.Token(access_token=token, token_type=token_type)
