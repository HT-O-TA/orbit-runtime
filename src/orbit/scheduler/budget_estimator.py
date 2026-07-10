import os
import json
from typing import Dict
from ..models.task import SubTask


class BudgetEstimator:
    DEFAULT_BUDGETS = {
        "planner": {"tokens": 500, "time_ms": 800},
        "researcher": {"tokens": 2000, "time_ms": 2500},
        "coder": {"tokens": 1500, "time_ms": 2000},
        "reviewer": {"tokens": 300, "time_ms": 600},
        "executor": {"tokens": 100, "time_ms": 200},
    }

    def _get_fallback_budget(self, subtask: SubTask) -> Dict[str, int]:
        base = self.DEFAULT_BUDGETS.get(subtask.agent_type, {"tokens": 500, "time_ms": 1000})
        length_factor = max(1, len(str(subtask.input_context)) // 100)
        return {
            "tokens": base["tokens"] + length_factor * 10,
            "time_ms": base["time_ms"] + length_factor * 20,
            "actual_tokens": 0,
            "actual_time_ms": 0,
        }

    async def estimate(self, subtask: SubTask) -> Dict[str, int]:
        llm_api_base = os.environ.get("LLM_API_BASE")
        llm_api_key = os.environ.get("LLM_API_KEY")

        if not llm_api_base or not llm_api_key:
            print("[BudgetEstimator] LLM API 配置未设置，使用降级策略")
            return self._get_fallback_budget(subtask)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=llm_api_base,
                api_key=llm_api_key,
            )

            prompt = f"""
            请根据以下子任务信息预估其 Token 消耗和执行耗时（毫秒）：
            
            子任务名称: {subtask.name}
            Agent 类型: {subtask.agent_type}
            输入上下文: {subtask.input_context}
            
            请以 JSON 格式返回，格式如下：
            {{"tokens": 整数, "time_ms": 整数}}
            
            tokens 范围建议：100-5000
            time_ms 范围建议：100-5000
            """.strip()

            response = await client.chat.completions.create(
                model="Qwen2.5-0.5B",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return {
                "tokens": int(result.get("tokens", 500)),
                "time_ms": int(result.get("time_ms", 1000)),
                "actual_tokens": 0,
                "actual_time_ms": 0,
            }
        except Exception as e:
            print(f"[BudgetEstimator] LLM 调用失败，使用降级策略: {str(e)}")
            return self._get_fallback_budget(subtask)
