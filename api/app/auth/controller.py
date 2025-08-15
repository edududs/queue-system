from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from ..rate_limiter import limiter
from ..settings.database import DbSession
from . import models, service

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register_user(
    request: Request,
    db: DbSession,
    register_user_request: models.RegisterUserRequest,
):
    service.register_user(db, register_user_request)


@router.post("/token", response_model=models.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    return service.login_for_access_token(form_data, db)
