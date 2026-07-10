import pytest
import asyncio
from orbit.agents.planner import PlannerAgent
from orbit.models.task import OrbitTask, SubTask, TaskStatus


class TestPlannerPostMortem:
    @pytest.mark.asyncio
    async def test_post_mortem_researcher_timeout(self):
        planner = PlannerAgent()
        
        failed_task = SubTask(
            id="researcher_1",
            name="调研任务",
            agent_type="researcher",
            dependencies=[],
            input_context={"query": "test"},
            status=TaskStatus.PENDING
        )
        
        original_task = OrbitTask(
            task_id="test_task",
            user_query="test",
            sub_tasks=[failed_task],
            dag_adjacency={"researcher_1": []},
            created_at="2026-07-08"
        )
        
        patches = await planner.post_mortem(failed_task, "timeout error", original_task)
        
        assert len(patches) == 1
        patch = patches[0]
        assert patch.id.startswith("patch_")
        assert patch.name == "补丁-简化调研"
        assert patch.agent_type == "executor"
        assert patch.dependencies == ["researcher_1"]

    @pytest.mark.asyncio
    async def test_post_mortem_default_compensation(self):
        planner = PlannerAgent()
        
        failed_task = SubTask(
            id="planner_1",
            name="规划任务",
            agent_type="planner",
            dependencies=[],
            input_context={"query": "test"},
            status=TaskStatus.PENDING
        )
        
        original_task = OrbitTask(
            task_id="test_task",
            user_query="test",
            sub_tasks=[failed_task],
            dag_adjacency={"planner_1": []},
            created_at="2026-07-08"
        )
        
        patches = await planner.post_mortem(failed_task, "some error", original_task)
        
        assert len(patches) == 1
        patch = patches[0]
        assert patch.id.startswith("patch_")
        assert patch.name == "补丁-默认补偿"
        assert patch.agent_type == "executor"


@pytest.mark.asyncio
async def test_workflow_logic_with_failure():
    from orbit.temporal.workflows import OrbitWorkflow
    
    async def mock_executor(subtask):
        if subtask.agent_type == "executor":
            return f"Executed {subtask.id} successfully"
        raise Exception(f"Simulated failure for {subtask.id} (timeout)")
    
    failed_task = SubTask(
        id="researcher_1",
        name="调研任务",
        agent_type="researcher",
        dependencies=[],
        input_context={"query": "test"},
        status=TaskStatus.PENDING
    )
    
    task = OrbitTask(
        task_id="test_task",
        user_query="test",
        sub_tasks=[failed_task],
        dag_adjacency={"researcher_1": []},
        created_at="2026-07-08"
    )
    
    workflow_instance = OrbitWorkflow.__new__(OrbitWorkflow)
    workflow_instance.patch_manager = type('obj', (object,), {'add_patch': lambda self, *args: None})()
    workflow_instance.planner = PlannerAgent()
    
    executed = set()
    dag = {st.id: st.dependencies for st in task.sub_tasks}
    
    while not workflow_instance._is_task_complete(task, executed):
        ready = workflow_instance._get_ready_tasks(task, dag, executed)
        if not ready:
            break
        
        for subtask in ready:
            if subtask.id in executed:
                continue
            
            try:
                result = await mock_executor(subtask)
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result
                executed.add(subtask.id)
            except Exception as e:
                patches = await workflow_instance.planner.post_mortem(subtask, str(e), task)
                for patch in patches:
                    task.sub_tasks.append(patch)
                    dag[patch.id] = patch.dependencies
                subtask.status = TaskStatus.FAILED
                executed.add(subtask.id)
    
    assert len(task.sub_tasks) == 2
    assert task.sub_tasks[0].status == TaskStatus.FAILED
    assert task.sub_tasks[1].status == TaskStatus.COMPLETED
    assert task.sub_tasks[1].id.startswith("patch_")
