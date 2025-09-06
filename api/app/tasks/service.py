"""Task service with timezone support."""

import logging
from typing import List, Optional

from fastapi import Request

from ..utils.timezone import (
    convert_to_user_timezone,
    get_current_utc_time,
)
from .models import Task, TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing tasks."""

    def __init__(self):
        """Initialize the task service."""
        self.tasks: List[Task] = []
        self._counter = 0

    def create_task(self, task_data: TaskCreate, request: Request) -> Task:
        """Create a new task with timezone awareness.

        Args:
            task_data: Task creation data
            request: FastAPI request object for timezone context

        Returns:
            Created task

        """
        # Get user timezone from request state (set by middleware)
        user_timezone = getattr(request.state, "user_timezone", None)

        # Use task-specific timezone or fallback to request timezone
        final_timezone = task_data.user_timezone or user_timezone

        # Create task with UTC timestamps
        task = Task(
            id=self._counter,
            title=task_data.title,
            description=task_data.description,
            status=task_data.status,
            user_timezone=final_timezone,
            created_at=get_current_utc_time(),
        )

        self._counter += 1
        self.tasks.append(task)

        logger.info(f"Created task {task.id} with timezone {final_timezone}")
        return task

    def get_task(self, task_id: int, request: Request) -> Optional[Task]:
        """Get a task by ID, converting timestamps to user timezone.

        Args:
            task_id: Task ID to retrieve
            request: FastAPI request object for timezone context

        Returns:
            Task with localized timestamps

        """
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return None

        # Get user timezone preference
        user_timezone = getattr(request.state, "user_timezone", None)
        if final_timezone := task.user_timezone or user_timezone:
            # Create a copy with localized timestamps for display
            localized_task = task.model_copy()
            if localized_task.created_at:
                localized_task.created_at = convert_to_user_timezone(
                    localized_task.created_at,
                    final_timezone,
                )
            if localized_task.updated_at:
                localized_task.updated_at = convert_to_user_timezone(
                    localized_task.updated_at,
                    final_timezone,
                )
            return localized_task

        return task

    def get_tasks(self, request: Request) -> List[Task]:
        """Get all tasks with timezone-aware timestamps.

        Args:
            request: FastAPI request object for timezone context

        Returns:
            List of tasks with localized timestamps

        """
        user_timezone = getattr(request.state, "user_timezone", None)

        if not user_timezone:
            return self.tasks

        # Convert all timestamps to user timezone
        localized_tasks = []
        for task in self.tasks:
            localized_task = task.model_copy()
            if localized_task.created_at:
                localized_task.created_at = convert_to_user_timezone(
                    localized_task.created_at,
                    user_timezone,
                )
            if localized_task.updated_at:
                localized_task.updated_at = convert_to_user_timezone(
                    localized_task.updated_at,
                    user_timezone,
                )
            localized_tasks.append(localized_task)

        return localized_tasks

    def update_task(  # noqa: D417
        self,
        task_id: int,
        task_data: TaskUpdate,
        request: Request,  # noqa: ARG002
    ) -> Optional[Task]:
        """Update a task with timezone awareness.

        Args:
            task_id: Task ID to update
            request: FastAPI request object for timezone context

        Returns:
            Updated task

        """
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return None

        # Update fields
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.status is not None:
            task.status = task_data.status
        if task_data.user_timezone is not None:
            task.user_timezone = task_data.user_timezone

        # Update timestamp
        task.updated_at = get_current_utc_time()

        logger.info(f"Updated task {task_id} with timezone {task.user_timezone}")
        return task

    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID.

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted, False if not found

        """
        if task := next((t for t in self.tasks if t.id == task_id), None):
            self.tasks.remove(task)
            logger.info(f"Deleted task {task_id}")
            return True
        return False


# Global instance
task_service = TaskService()
