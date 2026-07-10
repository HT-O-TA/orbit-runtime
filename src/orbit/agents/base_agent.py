from abc import ABC, abstractmethod
from typing import Dict, Optional
from ..models.agent_models import AgentContext, AgentResponse, AgentType


class BaseAgent(ABC):
    agent_type: AgentType

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResponse:
        pass

    def get_capability(self) -> Dict[str, str]:
        return {
            "agent_type": self.agent_type.value,
            "agent_id": self.agent_id,
        }

    def _create_response(
        self,
        task_id: str,
        subtask_id: str,
        content: str,
        status: str = "completed",
        metadata: Optional[Dict[str, str]] = None,
        error_message: Optional[str] = None,
    ) -> AgentResponse:
        return AgentResponse(
            agent_type=self.agent_type,
            agent_id=self.agent_id,
            task_id=task_id,
            subtask_id=subtask_id,
            content=content,
            status=status,
            metadata=metadata or {},
            error_message=error_message,
        )
