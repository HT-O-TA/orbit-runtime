import asyncio
from typing import List, Callable, Any, Dict
from ..models.task import SubTask


class SpeculativeExecutor:
    def __init__(self, executor_func: Callable[[SubTask], Any]):
        self.executor_func = executor_func

    async def execute_branches(self, candidate_tasks: List[SubTask]) -> Dict[str, Any]:
        if not candidate_tasks:
            return {}
        tasks = [self.executor_func(st) for st in candidate_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {st.id: res for st, res in zip(candidate_tasks, results)}
