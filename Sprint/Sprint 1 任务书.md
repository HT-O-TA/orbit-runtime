### 📋 【Sprint 1 任务书：Orbit 项目初始化与数据模型定义】

**目标**：创建 Python 虚拟环境，安装核心依赖，定义好所有 Pydantic 数据模型和 Temporal 工作流接口，让项目能 `python -m pytest` 跑通（即使全是占位测试）。

**1. 项目目录结构（Trae 请严格按此创建）：**
```
orbit-runtime/
├── pyproject.toml          # 使用 uv 或 poetry 管理依赖（推荐 uv）
├── .env.example
├── docker-compose.yml      # 包含 Temporal Server + Postgres + Jaeger
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py         # 定义 Task, SubTask, TaskDependency
│   │   └── agent_models.py # 定义 AgentCapability, AgentResponse, AgentContext
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py   # 抽象基类 (ABC)
│   │   ├── planner.py      # Planner Agent
│   │   ├── researcher.py   # Researcher Agent
│   │   └── reviewer.py     # Reviewer Agent
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── dispatcher.py   # 依赖图解析 + 任务分发
│   ├── temporal/
│   │   ├── __init__.py
│   │   ├── workflows.py    # 定义 OrbitWorkflow (使用 Temporal @workflow.defn)
│   │   └── activities.py   # 定义各 Agent 调用的 Activity
│   ├── memory/
│   │   ├── __init__.py
│   │   └── semantic_memory.py # 向量记忆读写接口
│   └── observability/
│       ├── __init__.py
│       └── tracer.py       # OpenTelemetry 封装
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   └── test_scheduler.py
└── main.py                 # FastAPI 入口
```

**2. 依赖列表（写入 pyproject.toml）：**
- `python` >= 3.12
- `fastapi` + `uvicorn[standard]`
- `temporalio` (官方 SDK)
- `openai-agents` (OpenAI Agents SDK，用于多 Agent 原生编排)
- `opentelemetry-api` + `opentelemetry-sdk` + `opentelemetry-exporter-otlp`
- `pydantic` + `pydantic-settings`
- `asyncpg` + `sqlalchemy[asyncio]` (用于元数据存储)
- `pytest` + `pytest-asyncio`

**3. 核心数据模型定义（Trae 请生成代码）：**
在 `src/models/task.py` 中定义：
```python
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Dict

class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    WAITING_FOR_AGENT = "waiting_agent"
    COMPLETED = "completed"
    FAILED = "failed"

class SubTask(BaseModel):
    id: str
    name: str
    agent_type: str  # "planner" | "researcher" | "coder" | "reviewer"
    dependencies: List[str] = []  # 依赖的 SubTask id
    input_context: Dict[str, str]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None

class OrbitTask(BaseModel):
    task_id: str
    user_query: str
    sub_tasks: List[SubTask]
    dag_adjacency: Dict[str, List[str]]  # 依赖邻接表
    created_at: str
```
*(Trae 需根据此生成完整的 Pydantic 类，并加上示例工厂方法)*

**4. 验收标准：**
- 运行 `pytest tests/test_models.py` 至少能通过简单的实例化测试。
- `docker-compose up -d` 能拉取 `temporalio/auto-setup` 和 `jaegertracing/all-in-one` 镜像并启动。

---
