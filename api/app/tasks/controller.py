from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from ..exceptions import TaskNotFoundError
from .models import Task, TaskCreate, TaskUpdate
from .queue import queue_manager
from .service import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, request: Request):
    return task_service.create_task(task_data, request)


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int, request: Request):
    if task := task_service.get_task(task_id, request):
        return task
    raise TaskNotFoundError(task_id)


@router.get("/", response_model=list[Task])
def list_tasks(request: Request):
    return task_service.get_tasks(request)


@router.put("/{task_id}", response_model=Task)
def update_task(task_id: int, task_data: TaskUpdate, request: Request):
    if task := task_service.update_task(task_id, task_data, request):
        return task
    raise TaskNotFoundError(task_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    ok = task_service.delete_task(task_id)
    if not ok:
        raise TaskNotFoundError(task_id)


class EnqueuePayload(BaseModel):
    title: str
    description: str
    status: str = "pending"
    should_fail: bool | None = False


@router.post("/enqueue", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_task(payload: EnqueuePayload):
    try:
        message_id = await queue_manager.publish_to_main(payload.model_dump())
        return {"message_id": message_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/queue/health")
async def queue_health():
    ok = await queue_manager.ping()
    return {"rabbitmq": "connected" if ok else "disconnected"}
