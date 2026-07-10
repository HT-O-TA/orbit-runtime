from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    WAITING_FOR_AGENT = "waiting_agent"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(BaseModel):
    id: str = Field(..., description="子任务唯一标识符")
    name: str = Field(..., description="子任务名称")
    agent_type: str = Field(..., description="执行该子任务的Agent类型")
    dependencies: List[str] = Field(default_factory=list, description="依赖的SubTask id列表")
    input_context: Dict[str, str] = Field(default_factory=dict, description="输入上下文数据")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="子任务状态")
    result: Optional[str] = Field(default=None, description="子任务执行结果")

    @classmethod
    def create_example(cls) -> "SubTask":
        return cls(
            id="subtask-001",
            name="市场调研",
            agent_type="researcher",
            dependencies=[],
            input_context={"topic": "AI Agent 市场趋势"},
            status=TaskStatus.PENDING,
        )


class OrbitTask(BaseModel):
    task_id: str = Field(..., description="任务唯一标识符")
    user_query: str = Field(..., description="用户原始查询")
    sub_tasks: List[SubTask] = Field(default_factory=list, description="子任务列表")
    dag_adjacency: Dict[str, List[str]] = Field(default_factory=dict, description="依赖邻接表")
    created_at: str = Field(..., description="任务创建时间")

    @classmethod
    def create_example(cls) -> "OrbitTask":
        subtask1 = SubTask.create_example()
        subtask2 = SubTask(
            id="subtask-002",
            name="方案设计",
            agent_type="planner",
            dependencies=["subtask-001"],
            input_context={"research_result": "待填充"},
            status=TaskStatus.PENDING,
        )
        subtask3 = SubTask(
            id="subtask-003",
            name="结果审核",
            agent_type="reviewer",
            dependencies=["subtask-002"],
            input_context={"design_doc": "待填充"},
            status=TaskStatus.PENDING,
        )
        return cls(
            task_id="task-12345",
            user_query="帮我设计一个企业级AI Agent平台",
            sub_tasks=[subtask1, subtask2, subtask3],
            dag_adjacency={
                "subtask-001": ["subtask-002"],
                "subtask-002": ["subtask-003"],
                "subtask-003": [],
            },
            created_at=datetime.now().isoformat(),
        )
