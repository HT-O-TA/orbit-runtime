from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from orbit.models.task import OrbitTask, SubTask, TaskStatus
from orbit.models.agent_models import AgentType, AgentCapability, AgentResponse, AgentContext
from orbit.scheduler.smart_dispatcher import SmartDispatcher
from orbit.scheduler.base_dispatcher import TaskDispatcher
from orbit.agents.planner import PlannerAgent
from orbit.agents.researcher import ResearcherAgent
from orbit.agents.reviewer import ReviewerAgent
from orbit.api.routes import router
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio


app = FastAPI(title="Orbit Runtime API", version="0.1.0")


async def mock_agent_executor(subtask: SubTask) -> str:
    await asyncio.sleep(0.05)
    return f"executed_{subtask.id}"


app.state.dispatcher = SmartDispatcher(mock_agent_executor)


app.mount("/static", StaticFiles(directory="src/orbit/api/static"), name="static")
app.include_router(router)


class SubmitTaskRequest(BaseModel):
    user_query: str = Field(..., description="用户查询")


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    subtasks: List[dict] = Field(default_factory=list, description="子任务列表")


@app.get("/")
async def root():
    return {"message": "Orbit Runtime API", "version": "0.1.0"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    favicon_data = b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x04\x00(\x00\x00\x00\x16\x00\x00\x00 \x00\x00\x00\x10\x00\x00\x00\x01\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    return Response(content=favicon_data, media_type="image/vnd.microsoft.icon")


@app.post("/submit", response_model=OrbitTask)
async def submit_task(request: SubmitTaskRequest):
    planner = PlannerAgent()
    context = AgentContext(
        task_id=f"task-{datetime.now().timestamp()}",
        subtask_id="initial",
        user_query=request.user_query,
        conversation_history=[],
        available_capabilities=[],
        shared_memory={},
    )

    response = await planner.execute(context)

    import json
    try:
        result_data = json.loads(response.content)
        subtasks_data = result_data.get("subtasks", [])
        dag_data = result_data.get("dag", {})
    except:
        subtasks_data = []
        dag_data = {}

    orbit_task = OrbitTask(
        task_id=context.task_id,
        user_query=request.user_query,
        sub_tasks=[SubTask(**st) for st in subtasks_data] if subtasks_data else [],
        dag_adjacency=dag_data,
        created_at=datetime.now().isoformat(),
    )

    return orbit_task


@app.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    return {
        "task_id": task_id,
        "status": "pending",
        "subtasks": [],
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
