import pytest
from orbit.scheduler.base_dispatcher import TaskDispatcher
from orbit.models.task import OrbitTask, SubTask, TaskStatus


class TestTaskDispatcher:
    def test_init(self):
        dispatcher = TaskDispatcher()
        assert len(dispatcher.executed_tasks) == 0
        assert len(dispatcher.running_tasks) == 0

    def test_mark_started(self):
        dispatcher = TaskDispatcher()
        dispatcher.mark_started("subtask-001")
        assert "subtask-001" in dispatcher.running_tasks

    def test_mark_completed(self):
        dispatcher = TaskDispatcher()
        dispatcher.mark_started("subtask-001")
        dispatcher.mark_completed("subtask-001", "result")
        assert "subtask-001" in dispatcher.executed_tasks
        assert "subtask-001" not in dispatcher.running_tasks

    def test_has_cycles_acyclic(self):
        dispatcher = TaskDispatcher()
        dag = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
        assert dispatcher.has_cycles(dag) is False

    def test_has_cycles_cyclic(self):
        dispatcher = TaskDispatcher()
        dag = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
        }
        assert dispatcher.has_cycles(dag) is True

    def test_topological_sort(self):
        dispatcher = TaskDispatcher()
        dag = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
        result = dispatcher.topological_sort(dag)
        assert result is not None
        assert len(result) == 4
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")

    def test_topological_sort_cyclic(self):
        dispatcher = TaskDispatcher()
        dag = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
        }
        result = dispatcher.topological_sort(dag)
        assert result is None

    def test_get_ready_tasks_no_dependencies(self):
        dispatcher = TaskDispatcher()
        subtask = SubTask(
            id="sub-001",
            name="Task 1",
            agent_type="planner",
            dependencies=[],
            input_context={},
        )
        task = OrbitTask(
            task_id="task-123",
            user_query="Test",
            sub_tasks=[subtask],
            dag_adjacency={"sub-001": []},
            created_at="2024-01-01",
        )
        ready = dispatcher.get_ready_tasks(task)
        assert len(ready) == 1
        assert ready[0].id == "sub-001"

    def test_get_ready_tasks_with_dependencies(self):
        dispatcher = TaskDispatcher()
        subtask1 = SubTask(
            id="sub-001",
            name="Task 1",
            agent_type="planner",
            dependencies=[],
            input_context={},
        )
        subtask2 = SubTask(
            id="sub-002",
            name="Task 2",
            agent_type="researcher",
            dependencies=["sub-001"],
            input_context={},
        )
        task = OrbitTask(
            task_id="task-123",
            user_query="Test",
            sub_tasks=[subtask1, subtask2],
            dag_adjacency={"sub-001": ["sub-002"], "sub-002": []},
            created_at="2024-01-01",
        )
        ready = dispatcher.get_ready_tasks(task)
        assert len(ready) == 1
        assert ready[0].id == "sub-001"

        dispatcher.mark_completed("sub-001", "result")
        ready = dispatcher.get_ready_tasks(task)
        assert len(ready) == 1
        assert ready[0].id == "sub-002"

    def test_is_task_complete(self):
        dispatcher = TaskDispatcher()
        subtask1 = SubTask(
            id="sub-001",
            name="Task 1",
            agent_type="planner",
            dependencies=[],
            input_context={},
            status=TaskStatus.COMPLETED,
        )
        subtask2 = SubTask(
            id="sub-002",
            name="Task 2",
            agent_type="researcher",
            dependencies=["sub-001"],
            input_context={},
            status=TaskStatus.COMPLETED,
        )
        task = OrbitTask(
            task_id="task-123",
            user_query="Test",
            sub_tasks=[subtask1, subtask2],
            dag_adjacency={"sub-001": ["sub-002"], "sub-002": []},
            created_at="2024-01-01",
        )
        assert dispatcher.is_task_complete(task) is True

        subtask2.status = TaskStatus.PENDING
        assert dispatcher.is_task_complete(task) is False
