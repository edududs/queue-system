from datetime import datetime
from typing import ClassVar, Optional

from pydantic import BaseModel, Field

from ..utils.timezone import get_current_utc_time


class TaskBase(BaseModel):
    """Base model for Task with common fields."""

    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Task description",
    )
    status: str = Field(..., description="Task status")
    user_timezone: Optional[str] = Field(
        default=None,
        description="User's timezone for datetime display",
    )


class TaskCreate(TaskBase):
    """Model for creating a new task."""


class Task(TaskBase):
    """Complete Task model with all fields."""

    id: int
    created_at: datetime = Field(default_factory=get_current_utc_time)
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders: ClassVar = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class TaskUpdate(BaseModel):
    """Model for updating a task. All fields are optional."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    status: Optional[str] = Field(default=None)
    user_timezone: Optional[str] = Field(default=None)
