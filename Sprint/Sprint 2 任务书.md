### 📋 【Sprint 2 任务书：智能调度引擎 —— Token 感知 + 投机执行】

**Sprint 目标**：将原有的 `TaskDispatcher` 升级为 **`SmartDispatcher`**，实现：
1. **Token/耗时预估（Budget Estimator）**：为每个子任务标记预估消耗（初期硬编码/Mock）。
2. **动态优先级重排（Budget-Aware Priority）**：轻量级任务（低 Token）优先出队，重量级任务（高 Token）提前“预热”上下文（以 `print` 模拟）。
3. **投机执行（Speculative Execution）**：当 DAG 中某个节点后出现**2 条及以上并行分支**时，同时执行所有候选分支（用 `asyncio.gather`），一旦某分支确认有效，立即终止/忽略其他分支（模拟“分支预测”）。

> **⚠️ 严格约束**：所有 Agent 执行（`planner.execute`、`researcher.execute` 等）一律使用 **Mock 异步函数**（如 `async def mock_execute(subtask): await asyncio.sleep(random.uniform(0.1, 0.5)); return "mock_result"`）。**禁止**在 Sprint 2 中引入真实的 OpenAI API 调用或数据库持久化，确保测试 100% 可复现且无需外部密钥。

---

#### 1. 需要新增/修改的文件清单（Trae 请严格创建）：

```
src/orbit/scheduler/
├── __init__.py                         # 更新导出
├── base_dispatcher.py                  # 【重命名】将原 dispatcher.py 重命名为 base_dispatcher.py（保留基础解析能力）
├── budget_estimator.py                 # 【新增】预算预估器
├── speculative_executor.py             # 【新增】投机执行器
└── smart_dispatcher.py                 # 【新增】核心智能调度器（继承或组合 BaseDispatcher）
```

> **注意**：原 `dispatcher.py` 建议保留为 `base_dispatcher.py`，确保 Sprint 1 的测试依然能跑通。

---

#### 2. 核心模块规格说明（Trae 必须严格按此接口实现）

**A. `budget_estimator.py`**

```python
from typing import Dict
from ..models.task import SubTask

class BudgetEstimator:
    """预算预估器：为每个子任务预估 Token 消耗和执行耗时（毫秒）"""
    
    # 初期基于 Agent 类型硬编码 Mock 数据（后续可替换为真实模型推理预估）
    DEFAULT_BUDGETS = {
        "planner":    {"tokens": 500,  "time_ms": 800},
        "researcher": {"tokens": 2000, "time_ms": 2500},
        "coder":      {"tokens": 1500, "time_ms": 2000},
        "reviewer":   {"tokens": 300,  "time_ms": 600},
        "executor":   {"tokens": 100,  "time_ms": 200},
    }

    def estimate(self, subtask: SubTask) -> Dict[str, int]:
        """返回 {"tokens": int, "time_ms": int}"""
        base = self.DEFAULT_BUDGETS.get(subtask.agent_type, {"tokens": 500, "time_ms": 1000})
        # 可根据 subtask.input_context 的字符长度微调（模拟复杂度）
        length_factor = max(1, len(str(subtask.input_context)) // 100)
        return {
            "tokens": base["tokens"] + length_factor * 10,
            "time_ms": base["time_ms"] + length_factor * 20,
        }
```

**B. `speculative_executor.py`**

```python
import asyncio
from typing import List, Callable, Any, Dict
from ..models.task import SubTask

class SpeculativeExecutor:
    """投机执行器：针对 DAG 分支执行“预跑”"""
    
    def __init__(self, executor_func: Callable[[SubTask], Any]):
        """
        executor_func: 异步函数，接收 SubTask 返回结果（即 Mock Agent 执行器）
        """
        self.executor_func = executor_func

    async def execute_branches(self, candidate_tasks: List[SubTask]) -> Dict[str, Any]:
        """
        同时执行候选任务列表（并发），返回 {subtask_id: result}
        :param candidate_tasks: 可能被执行的分支子任务列表（通常 2~3 个）
        """
        if not candidate_tasks:
            return {}
        tasks = [self.executor_func(st) for st in candidate_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {st.id: res for st, res in zip(candidate_tasks, results)}
```

**C. `smart_dispatcher.py`（核心）**

```python
import asyncio
from typing import List, Optional, Dict, Set
from .base_dispatcher import TaskDispatcher       # 继承基础 DAG 解析能力
from .budget_estimator import BudgetEstimator
from .speculative_executor import SpeculativeExecutor
from ..models.task import OrbitTask, SubTask, TaskStatus

class SmartDispatcher(TaskDispatcher):
    def __init__(self, agent_executor_func):
        super().__init__()
        self.budget_estimator = BudgetEstimator()
        self.speculative_executor = SpeculativeExecutor(agent_executor_func)
        self.overall_budget = {"tokens": 10000, "time_ms": 30000}  # 任务总预算

    async def dispatch(self, task: OrbitTask) -> OrbitTask:
        """
        智能调度主入口：
        1. 解析 DAG 获取执行顺序（继承自 base）
        2. 引入预算感知：重排序就绪任务（轻量优先）
        3. 对每个节点检查是否存在分支 → 触发投机执行
        4. 标记完成状态
        """
        # 1. 基础校验
        dag = self._build_dag(task)
        if self.has_cycles(dag):
            raise ValueError("DAG contains cycles")

        # 2. 获取拓扑顺序（仅为参考，调度器按自己的智能逻辑执行）
        exec_order = self.topological_sort(dag)
        if exec_order is None:
            raise ValueError("Topological sort failed")

        # 3. 执行调度循环
        while not self.is_task_complete(task):
            ready = self.get_ready_tasks(task)
            if not ready:
                break

            # --- 核心智能逻辑 ---
            # 3a. 按 Token 预估升序排序（轻任务优先）
            ready.sort(key=lambda st: self.budget_estimator.estimate(st)["tokens"])

            # 3b. 检查是否存在投机执行条件（当前节点的后续分支）
            #    简单策略：取第一个就绪任务，检查它的后驱是否有多个分支
            #    若存在，则投机执行所有后驱候选。
            first = ready[0] if ready else None
            if first and first.id in dag:
                successors = dag.get(first.id, [])
                if len(successors) >= 2:
                    # 将后继节点转为 SubTask 列表（投机执行）
                    successor_subtasks = [st for st in task.sub_tasks if st.id in successors]
                    print(f"[Speculative] 触发投机执行，分支: {successors}")
                    # 异步执行所有分支，不阻塞主循环（这里 await 但实际是并行）
                    branch_results = await self.speculative_executor.execute_branches(successor_subtasks)
                    # 将投机结果暂存到内存（例如 self._speculative_cache），后续用到时直接取
                    # 为避免复杂，Sprint 2 只演示：只要结果不为异常，就标记对应子任务为 COMPLETED
                    for sid, result in branch_results.items():
                        if not isinstance(result, Exception):
                            # 直接标记完成（实际业务中需上下文验证，Sprint 2 简化）
                            for st in task.sub_tasks:
                                if st.id == sid:
                                    st.status = TaskStatus.COMPLETED
                                    st.result = f"speculative_result_{sid}"
                                    self.executed_tasks.add(sid)
                                    break

            # 3c. 正常执行当前任务（如果当前任务已被投机完成，则跳过）
            if first and first.id not in self.executed_tasks:
                print(f"[Execute] 执行任务: {first.id} ({first.agent_type})")
                # 调用真实 Agent 执行（此时为 Mock）
                result = await self.speculative_executor.executor_func(first)
                first.status = TaskStatus.COMPLETED
                first.result = str(result)
                self.executed_tasks.add(first.id)

        return task

    def _build_dag(self, task: OrbitTask) -> Dict[str, List[str]]:
        dag = {}
        for st in task.sub_tasks:
            dag[st.id] = st.dependencies
        return dag
```

**D. 更新 `src/orbit/scheduler/__init__.py`**：
```python
from .base_dispatcher import TaskDispatcher
from .smart_dispatcher import SmartDispatcher
from .budget_estimator import BudgetEstimator
from .speculative_executor import SpeculativeExecutor

__all__ = ["TaskDispatcher", "SmartDispatcher", "BudgetEstimator", "SpeculativeExecutor"]
```

---

#### 3. 测试文件（Sprint 2 质量门禁）

在 `tests/test_smart_scheduler.py` 中新增以下测试用例：

1. **test_budget_estimator**：验证 Researcher 比 Planner 消耗更多 Token。
2. **test_speculative_execution**：构造一个具有 3 个后继分支的 DAG，验证 `execute_branches` 并行执行且所有分支完成。
3. **test_smart_dispatcher_priority**：构造就绪列表包含 Planner 和 Researcher，验证 Researcher（高 Token）排在 Planner 后面执行。
4. **test_full_dag_with_speculation**：运行完整 DAG，验证投机分支结果被正确接收，且无循环死锁。

> **验收标准**：运行 `pytest tests/test_smart_scheduler.py -v`，全部通过。

---

#### 4. 给 Trae 的强制提醒（已写入任务书，请一并发给它）

1. **不要调用真实 OpenAI**：所有 `executor_func` 用 `async def mock_agent(subtask): await asyncio.sleep(0.1); return f"ok_{subtask.id}"` 实现。
2. **保持原测试通过**：Sprint 1 的 `test_scheduler.py` 依然能跑通（因为 `base_dispatcher` 没变）。
3. **日志简洁**：只使用 `print` 输出关键调度日志（如 `[Speculative]`、`[Execute]`），方便你肉眼观察执行流程。

---
