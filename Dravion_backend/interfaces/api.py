from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from tasks.task import Task
from tasks.task_scheduler import task_scheduler
from tasks.task_registry import task_registry
from core.logger import log

app = FastAPI(title="DRAVION v2 API")

class IntentRequest(BaseModel):
    intent: str
    priority: int = 5

@app.post("/api/v1/intent")
async def submit_intent(request: IntentRequest):
    """Submit a text intent to DRAVION"""
    # Create task (assuming conversation agent for simple text input)
    task = Task(
        intent=request.intent,
        agent="conversation_agent",
        priority=request.priority
    )
    
    await task_scheduler.schedule(task)
    
    return {"task_id": task.id, "status": "scheduled"}

@app.get("/api/v1/task/{task_id}")
async def get_task_status(task_id: str):
    """Poll task status"""
    task = task_registry.get_task(task_id)
    if not task:
        return {"error": "Task not found"}
        
    return {
        "task_id": task.id,
        "status": task.status.value,
        "result": task.result,
        "error": task.error
    }
