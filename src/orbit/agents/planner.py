import os
from .base_agent import BaseAgent
from ..models.agent_models import AgentContext, AgentResponse, AgentType
from ..models.task import OrbitTask, SubTask, TaskStatus
from typing import Dict, List


class PlannerAgent(BaseAgent):
    agent_type = AgentType.PLANNER

    def __init__(self, agent_id: str = "planner-agent"):
        super().__init__(agent_id)

    async def execute(self, context: AgentContext) -> AgentResponse:
        try:
            decomposed_tasks = self._decompose_task(context.user_query)
            dag = self._build_dag(decomposed_tasks)
            
            content = {
                "subtasks": [t.dict() for t in decomposed_tasks],
                "dag": dag,
            }
            
            return self._create_response(
                task_id=context.task_id,
                subtask_id=context.subtask_id,
                content=str(content),
                status="completed",
                metadata={"decomposed_count": str(len(decomposed_tasks))},
            )
        except Exception as e:
            return self._create_response(
                task_id=context.task_id,
                subtask_id=context.subtask_id,
                content="",
                status="failed",
                error_message=str(e),
            )

    def _decompose_task(self, user_query: str) -> List[SubTask]:
        return [
            SubTask(
                id="subtask-001",
                name="任务分析",
                agent_type="planner",
                dependencies=[],
                input_context={"query": user_query},
                status=TaskStatus.PENDING,
            ),
            SubTask(
                id="subtask-002",
                name="执行调研",
                agent_type="researcher",
                dependencies=["subtask-001"],
                input_context={"query": user_query},
                status=TaskStatus.PENDING,
            ),
            SubTask(
                id="subtask-003",
                name="结果审核",
                agent_type="reviewer",
                dependencies=["subtask-002"],
                input_context={"query": user_query},
                status=TaskStatus.PENDING,
            ),
        ]

    def _build_dag(self, subtasks: List[SubTask]) -> Dict[str, List[str]]:
        dag = {}
        for subtask in subtasks:
            successors = [s.id for s in subtasks if subtask.id in s.dependencies]
            dag[subtask.id] = successors
        return dag

    async def post_mortem(
        self,
        failed_subtask: SubTask,
        error_message: str,
        original_task: OrbitTask
    ) -> List[SubTask]:
        print(f"[Planner Post-Mortem] 分析失败任务: {failed_subtask.id}, 错误: {error_message}")

        llm_api_base = os.environ.get("LLM_API_BASE")
        llm_api_key = os.environ.get("LLM_API_KEY")

        if not llm_api_base or not llm_api_key:
            print("[Planner Post-Mortem] LLM API 配置未设置，使用降级策略")
            return self._get_fallback_patch(failed_subtask, error_message)

        try:
            from openai import AsyncOpenAI
            import json

            client = AsyncOpenAI(
                base_url=llm_api_base,
                api_key=llm_api_key,
            )

            prompt = f"""
            请分析以下子任务失败原因，并生成补丁子任务来修复或补偿。
            
            失败子任务信息：
            - ID: {failed_subtask.id}
            - 名称: {failed_subtask.name}
            - Agent 类型: {failed_subtask.agent_type}
            - 输入上下文: {failed_subtask.input_context}
            
            错误信息: {error_message}
            
            请生成补丁子任务列表（可以为空列表），以 JSON 格式返回。每个补丁子任务必须包含以下字段：
            - id: 字符串，格式为 "patch_原任务ID"
            - name: 字符串，补丁任务名称
            - agent_type: 字符串，可选值: planner, researcher, coder, reviewer, executor
            - dependencies: 数组，包含依赖的任务ID（至少包含失败任务的ID）
            - input_context: 对象，补丁任务的输入上下文
            
            返回格式示例：
            [{{"id": "patch_task1", "name": "补丁任务", "agent_type": "executor", "dependencies": ["task1"], "input_context": {{"message": "补偿信息"}}}}]
            """.strip()

            response = await client.chat.completions.create(
                model="Qwen2.5-0.5B",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()
            patches_data = json.loads(content)

            patches = []
            for patch_data in patches_data:
                try:
                    patch = SubTask(
                        id=patch_data.get("id", f"patch_{failed_subtask.id}"),
                        name=patch_data.get("name", f"补丁-{failed_subtask.name}"),
                        agent_type=patch_data.get("agent_type", "executor"),
                        dependencies=patch_data.get("dependencies", [failed_subtask.id]),
                        input_context=patch_data.get("input_context", {}),
                        status=TaskStatus.PENDING
                    )
                    patches.append(patch)
                except Exception as parse_error:
                    print(f"[Planner Post-Mortem] 解析补丁数据失败: {parse_error}")
                    continue

            if patches:
                return patches
            else:
                return self._get_fallback_patch(failed_subtask, error_message)
        except Exception as e:
            print(f"[Planner Post-Mortem] LLM 调用失败，使用降级策略: {str(e)}")
            return self._get_fallback_patch(failed_subtask, error_message)

    def _get_fallback_patch(self, failed_subtask: SubTask, error_message: str) -> List[SubTask]:
        if "timeout" in error_message.lower() and failed_subtask.agent_type == "researcher":
            patch = SubTask(
                id=f"patch_{failed_subtask.id}",
                name=f"补丁-简化调研",
                agent_type="executor",
                dependencies=[failed_subtask.id],
                input_context={"message": f"自动补偿: {failed_subtask.name} 调研超时，已使用缓存结果"},
                status=TaskStatus.PENDING
            )
            return [patch]
        else:
            patch = SubTask(
                id=f"patch_{failed_subtask.id}",
                name=f"补丁-默认补偿",
                agent_type="executor",
                dependencies=[failed_subtask.id],
                input_context={"message": f"自动补偿: {failed_subtask.name} 已跳过，错误已记录"},
                status=TaskStatus.PENDING
            )
            return [patch]
