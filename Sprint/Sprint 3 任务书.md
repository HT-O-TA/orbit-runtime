## 🎯 Sprint 3 目标：让 Planner 具备“复盘自愈”能力

我们把 Sprint 3 拆解为 **3 个清晰的子目标**（按优先级排序）：

1. **将 SmartDispatcher 挂载到 Temporal Workflow 中**（保持现有逻辑不变，仅做适配）
2. **实现“失败触发复盘”机制**：当 Activity 执行失败时，Workflow 不直接重试，而是调用 Planner 的复盘方法生成“补丁子任务”
3. **补丁任务动态插入 DAG**：将复盘生成的补丁任务追加到当前 Workflow 的执行队列中，继续执行

> **⚠️ 严格约束**：
> - **绝不碰真实 OpenAI API**：Sprint 3 的 Agent 执行依然用 Mock（即 `async def mock_agent(subtask)`），但 Mock 要能模拟“成功”和“失败”两种场景，以便测试复盘逻辑。
> - **不引入新数据库**：补丁任务的状态保存在 Temporal Workflow 的内存上下文中（即 Workflow 的 `run` 方法的局部变量），不持久化到 PostgreSQL。
> - **所有逻辑在 1 个 Temporal Workflow 内闭环**：不跨 Workflow 通信，保证测试可复现。

---

## 📋 【Sprint 3 任务书：Temporal 集成 + Planner 复盘自愈】

### 1. 需要修改/新增的文件清单

```
src/orbit/temporal/
├── workflows.py          # 【修改】OrbitWorkflow 增加复盘逻辑
├── activities.py         # 【修改】增加失败回调（或直接在 workflow 中捕获异常）
└── patch_manager.py      # 【新增】补丁任务管理器（管理动态生成的补丁）

src/orbit/agents/
└── planner.py            # 【修改】增加 post_mortem(失败日志) 方法，生成补丁 DAG

tests/
└── test_temporal_retry.py  # 【新增】测试复盘自愈流程
```

> **说明**：Sprint 3 **不修改** `smart_dispatcher.py`，它的职责仍然是“正常调度”，Temporal 只负责“异常处理”。

---

### 2. 核心模块规格说明

#### A. 修改 `planner.py`：增加复盘能力

```python
# src/orbit/agents/planner.py

from typing import List, Dict, Optional
from ..models.task import SubTask, OrbitTask, TaskStatus

class PlannerAgent:
    # ... 原有的 __init__ 和 plan() 方法保持不变 ...

    async def post_mortem(
        self, 
        failed_subtask: SubTask, 
        error_message: str,
        original_task: OrbitTask
    ) -> List[SubTask]:
        """
        复盘失败原因，生成补丁子任务列表
        :param failed_subtask: 失败的那个子任务
        :param error_message: Temporal 捕获的异常信息
        :param original_task: 当前正在执行的完整任务（包含所有子任务）
        :return: 补丁子任务列表（可空）
        """
        # Sprint 3 采用硬编码策略（模拟复盘），后续可替换为真正的 LLM 推理
        # 规则：如果失败任务是 researcher 且错误包含 "timeout"，则生成一个"简化版 researcher"
        # 否则，生成一个"executor"任务，输出一个固定补偿信息
        print(f"[Planner Post-Mortem] 分析失败任务: {failed_subtask.id}, 错误: {error_message}")
        
        if "timeout" in error_message.lower() and failed_subtask.agent_type == "researcher":
            # 生成一个补丁任务：轻量级研究员
            patch = SubTask(
                id=f"patch_{failed_subtask.id}",
                name=f"补丁-简化调研",
                agent_type="researcher",  # 复用 researcher，但后续可标记为 "lightweight"
                dependencies=[failed_subtask.id],
                input_context={"original_query": failed_subtask.input_context.get("query", ""), "mode": "fast"},
                status=TaskStatus.PENDING
            )
            return [patch]
        else:
            # 默认补偿：直接返回一个"已确认"的结果
            patch = SubTask(
                id=f"patch_{failed_subtask.id}",
                name=f"补丁-默认补偿",
                agent_type="executor",
                dependencies=[failed_subtask.id],
                input_context={"message": f"自动补偿: {failed_subtask.name} 已跳过，错误已记录"},
                status=TaskStatus.PENDING
            )
            return [patch]
```

---

#### B. 新增 `patch_manager.py`：管理补丁任务

```python
# src/orbit/temporal/patch_manager.py

from typing import List, Dict
from ..models.task import SubTask

class PatchManager:
    """补丁任务管理器：负责将复盘生成的补丁任务插入当前执行队列"""
    
    def __init__(self):
        self.patches: Dict[str, List[SubTask]] = {}  # {原始任务id: [补丁列表]}

    def add_patch(self, original_subtask_id: str, patches: List[SubTask]) -> None:
        """存储补丁任务"""
        if original_subtask_id not in self.patches:
            self.patches[original_subtask_id] = []
        self.patches[original_subtask_id].extend(patches)

    def get_patches_for(self, subtask_id: str) -> List[SubTask]:
        """获取某个任务的所有补丁"""
        return self.patches.get(subtask_id, [])

    def clear(self) -> None:
        self.patches.clear()
```

---

#### C. 修改 `workflows.py`：集成复盘自愈

这是 Sprint 3 的核心改动。**关键思路**：在 `OrbitWorkflow` 的 `run` 方法中，我们不再直接调用 `await activity.execute_subtask(subtask)`，而是用 `try-except` 包裹，当 Activity 失败时，触发 `planner.post_mortem` 生成补丁，然后**递归追加到执行队列**中。

```python
# src/orbit/temporal/workflows.py

from temporalio import workflow
from datetime import timedelta
from typing import List
from ..models.task import OrbitTask, SubTask, TaskStatus
from ..agents.planner import PlannerAgent
from .patch_manager import PatchManager
from .activities import execute_subtask

@workflow.defn
class OrbitWorkflow:
    def __init__(self):
        self.patch_manager = PatchManager()
        self.planner = PlannerAgent()

    @workflow.run
    async def run(self, task: OrbitTask) -> OrbitTask:
        # 初始化执行状态（模仿 SmartDispatcher 的调度循环，但运行在 Temporal 上下文中）
        executed = set()
        running = set()

        # 构建 DAG（简化版，直接使用 task.sub_tasks 的 dependencies）
        dag = {st.id: st.dependencies for st in task.sub_tasks}

        # 主循环：不断执行就绪任务（含补丁）
        while not self._is_task_complete(task, executed):
            ready = self._get_ready_tasks(task, dag, executed)
            if not ready:
                # 无就绪任务，退出（防止死循环）
                break

            # 逐个执行就绪任务（Sprint 3 暂不并行，简化逻辑，聚焦复盘流程）
            for subtask in ready:
                # 检查是否已被补丁替代（如果补丁已存在，原任务跳过）
                if subtask.id in executed:
                    continue

                print(f"[Workflow] 执行子任务: {subtask.id} ({subtask.agent_type})")
                try:
                    # 调用 Activity（Temporal 会捕获异常）
                    result = await workflow.execute_activity(
                        execute_subtask,
                        subtask,
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    subtask.status = TaskStatus.COMPLETED
                    subtask.result = result
                    executed.add(subtask.id)
                except Exception as e:
                    # --- 核心：失败触发复盘 ---
                    print(f"[Workflow] 子任务失败: {subtask.id}, 错误: {str(e)}")
                    # 1. 调用 Planner 复盘生成补丁
                    patches = await self.planner.post_mortem(subtask, str(e), task)
                    # 2. 存储补丁
                    self.patch_manager.add_patch(subtask.id, patches)
                    # 3. 将补丁追加到任务列表和 DAG 中
                    for patch in patches:
                        task.sub_tasks.append(patch)
                        dag[patch.id] = patch.dependencies
                    # 4. 将原任务标记为失败（但补丁会替代它）
                    subtask.status = TaskStatus.FAILED
                    # 注意：不将 subtask.id 加入 executed，因为补丁依赖它，需要等补丁执行完
                    # 但我们标记为 FAILED，并在后续跳过它

        return task

    def _is_task_complete(self, task: OrbitTask, executed: set) -> bool:
        # 所有任务（含补丁）都完成或失败
        return all(st.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] for st in task.sub_tasks)

    def _get_ready_tasks(self, task: OrbitTask, dag: dict, executed: set) -> List[SubTask]:
        ready = []
        for st in task.sub_tasks:
            if st.id in executed:
                continue
            if st.status != TaskStatus.PENDING:
                continue
            if all(dep in executed for dep in st.dependencies):
                ready.append(st)
        return ready
```

---

#### D. 修改 `activities.py`：增加 Mock 失败模式

为了让复盘机制可测试，Activity 需要能模拟失败。

```python
# src/orbit/temporal/activities.py

import asyncio
from temporalio import activity
from ..models.task import SubTask

@activity.defn
async def execute_subtask(subtask: SubTask) -> str:
    """执行一个子任务（Mock 版本，可配置失败率）"""
    # 模拟随机失败（20% 概率，用于测试复盘）
    import random
    if random.random() < 0.2:  # 20% 概率失败
        raise Exception(f"Simulated failure for {subtask.id} (timeout)")

    # 模拟执行耗时
    await asyncio.sleep(0.1)

    # 根据 Agent 类型返回不同的 Mock 结果
    if subtask.agent_type == "planner":
        return f"Planned DAG for {subtask.id}"
    elif subtask.agent_type == "researcher":
        return f"Research result for {subtask.id}: found 5 relevant documents"
    elif subtask.agent_type == "coder":
        return f"Code generated for {subtask.id}: def solution(): pass"
    elif subtask.agent_type == "reviewer":
        return f"Review passed for {subtask.id}"
    else:
        return f"Executed {subtask.id} successfully"
```

---

#### E. 新增测试 `test_temporal_retry.py`

```python
import pytest
from temporalio.testing import WorkflowEnvironment
from src.orbit.temporal.workflows import OrbitWorkflow
from src.orbit.models.task import OrbitTask, SubTask, TaskStatus

@pytest.mark.asyncio
async def test_planner_post_mortem_generates_patch():
    """测试：当 researcher 超时时，Planner 生成补丁任务"""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        client = env.client
        # 构造一个简单的任务：1 个 researcher 子任务
        subtask = SubTask(
            id="researcher_1",
            name="调研任务",
            agent_type="researcher",
            dependencies=[],
            input_context={"query": "test"},
            status=TaskStatus.PENDING
        )
        task = OrbitTask(
            task_id="test_task_1",
            user_query="test",
            sub_tasks=[subtask],
            dag_adjacency={},
            created_at="2026-07-08"
        )

        # 执行 Workflow（强制让 Activity 失败，需要修改 activities.py 中的随机失败逻辑，或直接注入异常）
        # 为简化测试，我们在 activities.py 中临时将失败率设为 100%
        result = await client.execute_workflow(
            OrbitWorkflow.run,
            task,
            id="test_workflow_1",
            task_queue="test-queue",
        )

        # 验证：补丁任务被生成并执行
        assert len(result.sub_tasks) == 2  # 原始 + 1 个补丁
        patch = result.sub_tasks[-1]
        assert patch.id.startswith("patch_")
        assert patch.status == TaskStatus.COMPLETED
```

---

### 3. 验收标准

1. **新增测试通过**：`pytest tests/test_temporal_retry.py -v` 全绿。
2. **原有的 27 个测试依然全绿**（Sprint 2 的调度逻辑不受影响）。
3. **手动运行验证**：启动 Temporal 服务后，运行 `uv run python main.py`，能看到 Workflow 执行时，20% 概率失败并触发复盘，补丁任务被追加。

---

### 4. 给 Trae 的强制提醒

1. **不要忘记修改 `__init__.py`**：确保 `PatchManager` 被正确导出。
2. **保持 Activities 轻量**：`execute_subtask` 依然使用 Mock，不要引入真实 OpenAI 调用。
3. **测试用例的随机失败**：为了避免测试不稳定，建议在测试文件里通过环境变量或全局 flag 控制失败率（例如 `ACTIVITY_FAIL_RATE=1` 强制失败）。

---
