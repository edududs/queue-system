from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str
