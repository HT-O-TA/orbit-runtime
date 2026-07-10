from .base_agent import BaseAgent
from ..models.agent_models import AgentContext, AgentResponse, AgentType


class ResearcherAgent(BaseAgent):
    agent_type = AgentType.RESEARCHER

    def __init__(self, agent_id: str = "researcher-agent"):
        super().__init__(agent_id)

    async def execute(self, context: AgentContext) -> AgentResponse:
        try:
            research_result = self._conduct_research(context)
            
            return self._create_response(
                task_id=context.task_id,
                subtask_id=context.subtask_id,
                content=research_result,
                status="completed",
                metadata={"research_scope": str(len(context.user_query))},
            )
        except Exception as e:
            return self._create_response(
                task_id=context.task_id,
                subtask_id=context.subtask_id,
                content="",
                status="failed",
                error_message=str(e),
            )

    def _conduct_research(self, context: AgentContext) -> str:
        return f"调研结果：关于 '{context.user_query}' 的信息收集完成。\n" \
               f"- 相关文档：3 篇\n" \
               f"- 关键要点：待补充具体调研内容\n" \
               f"- 时间范围：最近 30 天"
