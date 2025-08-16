from fastapi import HTTPException


class UserError(HTTPException):
    """Base exception for user-related errors."""


class UserNotFoundError(UserError):
    def __init__(self, user_id=None):
        message = (
            "User not found" if user_id is None else f"User with id {user_id} not found"
        )
        super().__init__(status_code=404, detail=message)


class PasswordMismatchError(UserError):
    def __init__(self):
        super().__init__(status_code=400, detail="New passwords do not match")


class InvalidPasswordError(UserError):
    def __init__(self):
        super().__init__(status_code=401, detail="Current password is incorrect")


class AuthenticationError(HTTPException):
    def __init__(self, message: str = "Could not validate user"):
        super().__init__(status_code=401, detail=message)


class UserAlreadyExistsError(HTTPException):
    def __init__(self, message: str = "User already exists"):
        super().__init__(status_code=400, detail=message)


class TaskError(HTTPException):
    """Base exception for task-related errors."""


class TaskNotFoundError(TaskError):
    def __init__(self, task_id=None):
        message = "Task not found" if task_id is None else f"Task with id {task_id} not found"
        super().__init__(status_code=404, detail=message)
