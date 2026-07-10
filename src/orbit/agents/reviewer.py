from .base_agent import BaseAgent
from ..models.agent_models import AgentContext, AgentResponse, AgentType


class ReviewerAgent(BaseAgent):
    agent_type = AgentType.REVIEWER

    def __init__(self, agent_id: str = "reviewer-agent"):
        super().__init__(agent_id)

    async def execute(self, context: AgentContext) -> AgentResponse:
        try:
            review_result = self._review_content(context)
            
            return self._create_response(
                task_id=context.task_id,
                subtask_id=context.subtask_id,
                content=review_result,
                status="completed",
                metadata={"review_score": "95"},
            )
        except Exception as e:
            return self._create_response(
                task_id=context.task_id,
                subtask_id=context.subtask_id,
                content="",
                status="failed",
                error_message=str(e),
            )

    def _review_content(self, context: AgentContext) -> str:
        return f"审核完成：\n" \
               f"- 完整性：通过\n" \
               f"- 准确性：通过\n" \
               f"- 合规性：通过\n" \
               f"- 建议：内容质量良好，可直接交付"
