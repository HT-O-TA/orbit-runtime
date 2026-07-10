import pytest
from orbit.models.task import TaskStatus, SubTask, OrbitTask
from orbit.models.agent_models import AgentType, AgentCapability, AgentResponse, AgentContext


class TestTaskStatus:
    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.SCHEDULED.value == "scheduled"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.WAITING_FOR_AGENT.value == "waiting_agent"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestSubTask:
    def test_subtask_instantiation(self):
        subtask = SubTask(
            id="subtask-001",
            name="Test Task",
            agent_type="planner",
            dependencies=["subtask-002"],
            input_context={"key": "value"},
            status=TaskStatus.PENDING,
            result=None,
        )
        assert subtask.id == "subtask-001"
        assert subtask.name == "Test Task"
        assert subtask.agent_type == "planner"
        assert subtask.dependencies == ["subtask-002"]
        assert subtask.input_context == {"key": "value"}
        assert subtask.status == TaskStatus.PENDING
        assert subtask.result is None

    def test_subtask_create_example(self):
        subtask = SubTask.create_example()
        assert subtask.id == "subtask-001"
        assert subtask.name == "市场调研"
        assert subtask.agent_type == "researcher"
        assert len(subtask.dependencies) == 0
        assert "topic" in subtask.input_context
        assert subtask.status == TaskStatus.PENDING

    def test_subtask_default_values(self):
        subtask = SubTask(
            id="subtask-001",
            name="Test",
            agent_type="planner",
        )
        assert subtask.dependencies == []
        assert subtask.input_context == {}
        assert subtask.status == TaskStatus.PENDING
        assert subtask.result is None


class TestOrbitTask:
    def test_orbit_task_instantiation(self):
        subtask = SubTask.create_example()
        task = OrbitTask(
            task_id="task-123",
            user_query="Test query",
            sub_tasks=[subtask],
            dag_adjacency={"subtask-001": []},
            created_at="2024-01-01T00:00:00",
        )
        assert task.task_id == "task-123"
        assert task.user_query == "Test query"
        assert len(task.sub_tasks) == 1
        assert task.dag_adjacency == {"subtask-001": []}
        assert task.created_at == "2024-01-01T00:00:00"

    def test_orbit_task_create_example(self):
        task = OrbitTask.create_example()
        assert task.task_id == "task-12345"
        assert "企业级AI Agent平台" in task.user_query
        assert len(task.sub_tasks) == 3
        assert len(task.dag_adjacency) == 3
        assert task.created_at is not None


class TestAgentType:
    def test_agent_type_values(self):
        assert AgentType.PLANNER.value == "planner"
        assert AgentType.RESEARCHER.value == "researcher"
        assert AgentType.CODER.value == "coder"
        assert AgentType.REVIEWER.value == "reviewer"
        assert AgentType.EXECUTOR.value == "executor"


class TestAgentCapability:
    def test_agent_capability_instantiation(self):
        capability = AgentCapability(
            agent_type=AgentType.RESEARCHER,
            name="Researcher",
            description="Does research",
            supported_tasks=["task1", "task2"],
            max_context_size=8192,
        )
        assert capability.agent_type == AgentType.RESEARCHER
        assert capability.name == "Researcher"
        assert capability.description == "Does research"
        assert capability.supported_tasks == ["task1", "task2"]
        assert capability.max_context_size == 8192

    def test_agent_capability_create_example(self):
        capability = AgentCapability.create_example()
        assert capability.agent_type == AgentType.RESEARCHER
        assert capability.name == "Researcher Agent"
        assert len(capability.supported_tasks) > 0


class TestAgentResponse:
    def test_agent_response_instantiation(self):
        response = AgentResponse(
            agent_type=AgentType.PLANNER,
            agent_id="agent-001",
            task_id="task-123",
            subtask_id="sub-001",
            content="Result content",
            status="completed",
            metadata={"key": "value"},
            error_message=None,
        )
        assert response.agent_type == AgentType.PLANNER
        assert response.agent_id == "agent-001"
        assert response.content == "Result content"
        assert response.status == "completed"

    def test_agent_response_create_example(self):
        response = AgentResponse.create_example()
        assert response.agent_type == AgentType.RESEARCHER
        assert response.status == "completed"
        assert response.error_message is None


class TestAgentContext:
    def test_agent_context_instantiation(self):
        context = AgentContext(
            task_id="task-123",
            subtask_id="sub-001",
            user_query="Test query",
            conversation_history=[],
            available_capabilities=[],
            shared_memory={},
            deadline=None,
        )
        assert context.task_id == "task-123"
        assert context.user_query == "Test query"

    def test_agent_context_create_example(self):
        context = AgentContext.create_example()
        assert context.task_id == "task-12345"
        assert len(context.conversation_history) == 2
        assert len(context.available_capabilities) == 1
