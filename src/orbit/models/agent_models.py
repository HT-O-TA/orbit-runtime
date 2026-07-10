from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict


class AgentType(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"


class AgentCapability(BaseModel):
    agent_type: AgentType = Field(..., description="Agent类型")
    name: str = Field(..., description="Agent名称")
    description: str = Field(..., description="Agent功能描述")
    supported_tasks: List[str] = Field(default_factory=list, description="支持的任务类型列表")
    max_context_size: int = Field(default=8192, description="最大上下文窗口大小")

    @classmethod
    def create_example(cls) -> "AgentCapability":
        return cls(
            agent_type=AgentType.RESEARCHER,
            name="Researcher Agent",
            description="负责信息检索与市场调研",
            supported_tasks=["market_research", "information_gathering", "competitor_analysis"],
            max_context_size=16384,
        )


class AgentResponse(BaseModel):
    agent_type: AgentType = Field(..., description="响应来源Agent类型")
    agent_id: str = Field(..., description="响应来源Agent实例ID")
    task_id: str = Field(..., description="关联的任务ID")
    subtask_id: str = Field(..., description="关联的子任务ID")
    content: str = Field(..., description="响应内容")
    status: str = Field(..., description="执行状态")
    metadata: Dict[str, str] = Field(default_factory=dict, description="附加元数据")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    @classmethod
    def create_example(cls) -> "AgentResponse":
        return cls(
            agent_type=AgentType.RESEARCHER,
            agent_id="agent-researcher-001",
            task_id="task-12345",
            subtask_id="subtask-001",
            content="市场调研完成，AI Agent市场正快速增长...",
            status="completed",
            metadata={"tokens_used": "1200", "duration_ms": "3500"},
            error_message=None,
        )


class AgentContext(BaseModel):
    task_id: str = Field(..., description="任务ID")
    subtask_id: str = Field(..., description="当前子任务ID")
    user_query: str = Field(..., description="原始用户查询")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="对话历史")
    available_capabilities: List[AgentCapability] = Field(default_factory=list, description="可用Agent能力列表")
    shared_memory: Dict[str, str] = Field(default_factory=dict, description="跨Agent共享记忆")
    deadline: Optional[str] = Field(default=None, description="任务截止时间")

    @classmethod
    def create_example(cls) -> "AgentContext":
        return cls(
            task_id="task-12345",
            subtask_id="subtask-001",
            user_query="帮我设计一个企业级AI Agent平台",
            conversation_history=[
                {"role": "user", "content": "帮我设计一个企业级AI Agent平台"},
                {"role": "system", "content": "任务已拆解，开始执行调研阶段"},
            ],
            available_capabilities=[AgentCapability.create_example()],
            shared_memory={"project_scope": "企业级多Agent平台"},
            deadline=None,
        )
