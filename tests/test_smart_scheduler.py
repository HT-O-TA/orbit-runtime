import pytest
import asyncio
from orbit.scheduler.budget_estimator import BudgetEstimator
from orbit.scheduler.speculative_executor import SpeculativeExecutor
from orbit.scheduler.smart_dispatcher import SmartDispatcher
from orbit.models.task import OrbitTask, SubTask, TaskStatus


async def mock_agent_executor(subtask):
    await asyncio.sleep(0.01)
    return f"ok_{subtask.id}"


class TestBudgetEstimator:
    @pytest.mark.asyncio
    async def test_budget_estimator(self):
        estimator = BudgetEstimator()
        
        planner_task = SubTask(
            id="sub-001",
            name="Plan",
            agent_type="planner",
            dependencies=[],
            input_context={},
        )
        
        researcher_task = SubTask(
            id="sub-002",
            name="Research",
            agent_type="researcher",
            dependencies=[],
            input_context={},
        )
        
        planner_budget = await estimator.estimate(planner_task)
        researcher_budget = await estimator.estimate(researcher_task)
        
        assert researcher_budget["tokens"] > planner_budget["tokens"]
        assert researcher_budget["time_ms"] > planner_budget["time_ms"]


class TestSpeculativeExecutor:
    @pytest.mark.asyncio
    async def test_speculative_execution(self):
        executor = SpeculativeExecutor(mock_agent_executor)
        
        branch_tasks = [
            SubTask(id="branch-a", name="Branch A", agent_type="coder", dependencies=[], input_context={}),
            SubTask(id="branch-b", name="Branch B", agent_type="coder", dependencies=[], input_context={}),
            SubTask(id="branch-c", name="Branch C", agent_type="coder", dependencies=[], input_context={}),
        ]
        
        results = await executor.execute_branches(branch_tasks)
        
        assert len(results) == 3
        assert "branch-a" in results
        assert "branch-b" in results
        assert "branch-c" in results
        assert results["branch-a"] == "ok_branch-a"
        assert results["branch-b"] == "ok_branch-b"
        assert results["branch-c"] == "ok_branch-c"


class TestSmartDispatcher:
    @pytest.mark.asyncio
    async def test_smart_dispatcher_priority(self):
        planner_task = SubTask(
            id="sub-planner",
            name="Plan Task",
            agent_type="planner",
            dependencies=[],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        researcher_task = SubTask(
            id="sub-researcher",
            name="Research Task",
            agent_type="researcher",
            dependencies=[],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        task = OrbitTask(
            task_id="test-priority",
            user_query="Test priority",
            sub_tasks=[researcher_task, planner_task],
            dag_adjacency={"sub-planner": [], "sub-researcher": []},
            created_at="2024-01-01",
        )
        
        dispatcher = SmartDispatcher(mock_agent_executor)
        result = await dispatcher.dispatch(task)
        
        assert planner_task.status == TaskStatus.COMPLETED
        assert researcher_task.status == TaskStatus.COMPLETED
        assert planner_task.result == "ok_sub-planner"
        assert researcher_task.result == "ok_sub-researcher"

    @pytest.mark.asyncio
    async def test_full_dag_with_speculation(self):
        root_task = SubTask(
            id="root",
            name="Root",
            agent_type="planner",
            dependencies=[],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        branch_a = SubTask(
            id="branch-a",
            name="Branch A",
            agent_type="coder",
            dependencies=["root"],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        branch_b = SubTask(
            id="branch-b",
            name="Branch B",
            agent_type="researcher",
            dependencies=["root"],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        branch_c = SubTask(
            id="branch-c",
            name="Branch C",
            agent_type="reviewer",
            dependencies=["root"],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        final_task = SubTask(
            id="final",
            name="Final",
            agent_type="executor",
            dependencies=["branch-a", "branch-b", "branch-c"],
            input_context={},
            status=TaskStatus.PENDING,
        )
        
        task = OrbitTask(
            task_id="test-spec-full",
            user_query="Test speculative execution",
            sub_tasks=[root_task, branch_a, branch_b, branch_c, final_task],
            dag_adjacency={
                "root": ["branch-a", "branch-b", "branch-c"],
                "branch-a": ["final"],
                "branch-b": ["final"],
                "branch-c": ["final"],
                "final": [],
            },
            created_at="2024-01-01",
        )
        
        dispatcher = SmartDispatcher(mock_agent_executor)
        result = await dispatcher.dispatch(task)
        
        assert root_task.status == TaskStatus.COMPLETED
        assert branch_a.status == TaskStatus.COMPLETED
        assert branch_b.status == TaskStatus.COMPLETED
        assert branch_c.status == TaskStatus.COMPLETED
        assert final_task.status == TaskStatus.COMPLETED
        assert "speculative_result_" in branch_a.result or branch_a.result == "ok_branch-a"
        assert "speculative_result_" in branch_b.result or branch_b.result == "ok_branch-b"
        assert "speculative_result_" in branch_c.result or branch_c.result == "ok_branch-c"
