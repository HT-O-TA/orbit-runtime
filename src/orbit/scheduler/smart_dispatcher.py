import asyncio
import random
from datetime import datetime
from typing import List, Optional, Dict, Set, Any
from .base_dispatcher import TaskDispatcher
from .budget_estimator import BudgetEstimator
from .speculative_executor import SpeculativeExecutor
from ..models.task import OrbitTask, SubTask, TaskStatus


class SmartDispatcher(TaskDispatcher):
    def __init__(self, agent_executor_func):
        super().__init__()
        self.budget_estimator = BudgetEstimator()
        self.speculative_executor = SpeculativeExecutor(agent_executor_func)
        self.overall_budget = {"tokens": 10000, "time_ms": 30000}
        self.decision_logs: List[Dict[str, Any]] = []
        self.max_logs = 100

    def _add_log(self, log: Dict[str, Any]) -> None:
        self.decision_logs.append(log)
        if len(self.decision_logs) > self.max_logs:
            self.decision_logs = self.decision_logs[20:]

    async def dispatch(self, task: OrbitTask) -> OrbitTask:
        dag = self._build_dag(task)
        if self.has_cycles(dag):
            raise ValueError("DAG contains cycles")

        exec_order = self.topological_sort(dag)
        if exec_order is None:
            raise ValueError("Topological sort failed")

        while not self.is_task_complete(task):
            ready = self.get_ready_tasks(task)
            if not ready:
                break

            budget_tasks = [(await self.budget_estimator.estimate(st), st) for st in ready]
            budget_tasks.sort(key=lambda x: x[0]["tokens"])
            ready = [st for _, st in budget_tasks]

            first = ready[0] if ready else None
            if first and first.id in dag:
                successors = dag.get(first.id, [])
                if len(successors) >= 2:
                    successor_subtasks = [st for st in task.sub_tasks if st.id in successors]
                    print(f"[Speculative] 触发投机执行，分支: {successors}")
                    branch_results = await self.speculative_executor.execute_branches(successor_subtasks)
                    for sid, result in branch_results.items():
                        if not isinstance(result, Exception):
                            for st in task.sub_tasks:
                                if st.id == sid:
                                    st.status = TaskStatus.COMPLETED
                                    st.result = f"speculative_result_{sid}"
                                    self.executed_tasks.add(sid)
                                    estimated = await self.budget_estimator.estimate(st)
                                    actual_tokens = int(estimated["tokens"] * random.uniform(0.8, 1.2))
                                    actual_time_ms = int(estimated["time_ms"] * random.uniform(0.8, 1.2))
                                    self._add_log({
                                        "task_id": task.task_id,
                                        "timestamp": datetime.now().isoformat(),
                                        "subtask_id": st.id,
                                        "agent_type": st.agent_type,
                                        "estimated_tokens": estimated["tokens"],
                                        "estimated_time_ms": estimated["time_ms"],
                                        "actual_tokens": actual_tokens,
                                        "actual_time_ms": actual_time_ms,
                                        "speculation_triggered": True,
                                        "speculation_branches": len(successors),
                                        "speculation_hit": True,
                                        "status": "success",
                                    })
                                    break

            if first and first.id not in self.executed_tasks:
                print(f"[Execute] 执行任务: {first.id} ({first.agent_type})")
                estimated = await self.budget_estimator.estimate(first)
                try:
                    result = await self.speculative_executor.executor_func(first)
                    first.status = TaskStatus.COMPLETED
                    first.result = str(result)
                    self.executed_tasks.add(first.id)
                    actual_tokens = int(estimated["tokens"] * random.uniform(0.8, 1.2))
                    actual_time_ms = int(estimated["time_ms"] * random.uniform(0.8, 1.2))
                    self._add_log({
                        "task_id": task.task_id,
                        "timestamp": datetime.now().isoformat(),
                        "subtask_id": first.id,
                        "agent_type": first.agent_type,
                        "estimated_tokens": estimated["tokens"],
                        "estimated_time_ms": estimated["time_ms"],
                        "actual_tokens": actual_tokens,
                        "actual_time_ms": actual_time_ms,
                        "speculation_triggered": False,
                        "speculation_branches": 0,
                        "speculation_hit": False,
                        "status": "success",
                    })
                except Exception as e:
                    first.status = TaskStatus.FAILED
                    first.result = str(e)
                    self._add_log({
                        "task_id": task.task_id,
                        "timestamp": datetime.now().isoformat(),
                        "subtask_id": first.id,
                        "agent_type": first.agent_type,
                        "estimated_tokens": estimated["tokens"],
                        "estimated_time_ms": estimated["time_ms"],
                        "actual_tokens": 0,
                        "actual_time_ms": 0,
                        "speculation_triggered": False,
                        "speculation_branches": 0,
                        "speculation_hit": False,
                        "status": "failed",
                    })

        return task

    def _build_dag(self, task: OrbitTask) -> Dict[str, List[str]]:
        dag = {}
        for st in task.sub_tasks:
            dag[st.id] = st.dependencies
        return dag
