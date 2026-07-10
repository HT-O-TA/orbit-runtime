from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker
from datetime import timedelta
from typing import List, Dict, Optional
from ..models.task import OrbitTask, SubTask, TaskStatus
from ..models.agent_models import AgentContext, AgentResponse, AgentType
from ..agents.planner import PlannerAgent
from ..scheduler.base_dispatcher import TaskDispatcher
from .patch_manager import PatchManager
from .activities import execute_subtask


@workflow.defn(name="OrbitWorkflow")
class OrbitWorkflow:
    def __init__(self):
        self.patch_manager = PatchManager()
        self.planner = PlannerAgent()

    @workflow.run
    async def run(self, task: OrbitTask) -> OrbitTask:
        executed = set()
        running = set()

        dag = {st.id: st.dependencies for st in task.sub_tasks}

        while not self._is_task_complete(task, executed):
            ready = self._get_ready_tasks(task, dag, executed)
            if not ready:
                break

            for subtask in ready:
                if subtask.id in executed:
                    continue

                print(f"[Workflow] 执行子任务: {subtask.id} ({subtask.agent_type})")
                try:
                    result = await workflow.execute_activity(
                        execute_subtask,
                        subtask,
                        start_to_close_timeout=timedelta(seconds=10),
                    )
                    subtask.status = TaskStatus.COMPLETED
                    subtask.result = result
                    executed.add(subtask.id)
                except Exception as e:
                    print(f"[Workflow] 子任务失败: {subtask.id}, 错误: {str(e)}")
                    patches = await self.planner.post_mortem(subtask, str(e), task)
                    self.patch_manager.add_patch(subtask.id, patches)
                    for patch in patches:
                        task.sub_tasks.append(patch)
                        dag[patch.id] = patch.dependencies
                    subtask.status = TaskStatus.FAILED
                    executed.add(subtask.id)

        return task

    def _is_task_complete(self, task: OrbitTask, executed: set) -> bool:
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


async def start_workflow(client: Client, orbit_task: OrbitTask) -> str:
    handle = await client.start_workflow(
        OrbitWorkflow.run,
        orbit_task,
        id=orbit_task.task_id,
        task_queue="orbit-task-queue",
    )
    return handle.id


async def get_workflow_result(client: Client, task_id: str) -> Dict[str, str]:
    result = await client.get_workflow_result(task_id)
    return result


async def create_worker(client: Client, task_queue: str = "orbit-task-queue") -> Worker:
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[OrbitWorkflow],
        activities=[execute_subtask],
    )
