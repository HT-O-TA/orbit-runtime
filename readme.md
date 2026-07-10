# 🚀 Orbit — Enterprise Multi-Agent Runtime Platform

> **项目代号**：Orbit（轨道）
>
> **核心定位**：面向企业级复杂长流程任务，设计并实现一套支持多智能体协作、A2A通信、持久化执行与深度可观测性的**智能体基础设施层（Agent Infrastructure）**。

---

## 📖 1. 项目概述（2026-07-09 修订版 · 深度聚焦）

Orbit 定位于 **“下一代智能体调度基础设施”** ，核心使命是解决多 Agent 系统在复杂长流程任务中的 **效率与鲁棒性** 问题。

**本项目极度聚焦两大深度创新点（区别于市面上所有 Dify/LangGraph 开源方案）：**

1. **智能调度引擎（核心攻坚方向）**：
   - 超越简单的 DAG 拓扑排序，引入 **“Token 预算感知（Budget-Aware）”** 与 **“投机执行（Speculative Execution）”** 机制。
   - 调度器能根据子任务预估的 Token 消耗和耗时，动态调整并行度；在依赖不明朗的分支处，提前并行执行可能路径，以空间换时间，大幅降低端到端延迟。

2. **基于 Planner 复盘的工作流自愈（辅助攻坚方向）**：
   - 当 Temporal 检测到子任务（Activity）失败时，不机械重试，而是触发 **Planner Agent 的复盘（Post-Mortem）**。
   - Planner 分析失败根因（工具超时？上下文不足？），动态生成“补丁子任务”插入 DAG，实现真正的“智能重试”，而非“暴力重试”。

**（暂缓开发）**：GraphRAG、复杂向量记忆在本阶段仅保留抽象接口，待调度内核稳定后再按需挂载。我们不堆砌功能，我们死磕深度。

---

## 🏗️ 2. 系统架构（聚焦调度闭环）

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REST API Gateway (FastAPI)                      │
│                   接收任务 → 返回 task_id → 前端轮询/等待 SSE             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    🧠 智能调度引擎 (Scheduler Engine)                     │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ 1. 任务拆解 (Planner Agent) → 生成 DAG + 预估 Token/耗时       │      │
│  │ 2. 动态优先级排序 (Budget-Aware) → 轻任务优先, 重任务预热     │      │
│  │ 3. 投机执行 (Speculative) → 并行跑候选分支, 舍弃错误结果     │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  ⚙️ 持久化执行层 (Temporal Workflow)                       │
│   - 原子执行子任务 (Activities)                                            │
│   - 失败触发器：调用 Planner 复盘 → 生成补丁 DAG → 继续执行              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    👁️ 可观测性 (OpenTelemetry + Jaeger)                   │
│              仅记录调度决策、子任务耗时、Token消耗，反哺优化               │
└─────────────────────────────────────────────────────────────────────────────┘

## 🧰 3. 技术栈选型（严格执行，禁止擅自替换）

| 层级 | 技术组件 | 版本要求 | 选择理由 |
| :--- | :--- | :--- | :--- |
| **Agent 框架** | **OpenAI Agents SDK** | `>=0.0.9` | 原生支持多 Agent Handoff、Tracing，轻量级且贴近厂商生态 |
| **工作流引擎** | **Temporal** | `temporalio>=1.7.0` | 提供久经考验的持久化执行、重试与可观测性，适合长时任务 |
| **Agent 通信** | **A2A (Agent2Agent)** | 参照 Google 2026 草案 | 解决 Agent 间标准化通信，体现前沿架构设计 |
| **可观测性** | **OpenTelemetry** + **Jaeger** | OTLP/gRPC | 业界标准，实现代码零侵入的全链路追踪 |
| **记忆与 RAG** | **MemGPT 风格语义记忆** + **GraphRAG** | 自研 / LightRAG | 短期工作记忆 + 长期向量记忆；图结构解决多跳推理 |
| **Web 框架** | **FastAPI** + **Uvicorn** | `>=0.115` | 高性能异步框架，原生支持 OpenAPI 文档 |
| **数据验证** | **Pydantic** + **Pydantic-Settings** | `>=2.0` | 强类型校验，配置管理优雅 |
| **数据库（元数据）** | **PostgreSQL** + **asyncpg** | `>=15` | 存储任务状态、Agent 注册信息（与项目一的向量库逻辑隔离） |
| **容器编排** | **Docker Compose** (开发) / K8s (生产) | `>=3.8` | 一键启动 Temporal、Jaeger、Postgres |

> **⚠️ 强制约束**：本项目**严禁**使用 **LangGraph**、**LangChain**、**Redis（作为消息队列）**、**RabbitMQ**。这些在项目一（MeetingMind）中已充分实践，此处需切换技术生态。

---

## 📂 4. 项目目录结构（AI 生成代码时必须严格遵守）

```text
orbit-runtime/
├── .env.example                 # 环境变量模板
├── .gitignore
├── docker-compose.yml           # 包含 temporal, jaeger, postgres
├── pyproject.toml               # 依赖管理（使用 uv 或 poetry）
├── README.md                    # 本文件
├── main.py                      # FastAPI 入口
├── src/
│   ├── __init__.py
│   ├── api/                     # 路由层
│   │   ├── __init__.py
│   │   ├── routes.py            # /submit, /status, /trace
│   │   └── dependencies.py      # 依赖注入
│   ├── core/                    # 核心配置与常量
│   │   ├── __init__.py
│   │   └── config.py            # Pydantic Settings
│   ├── models/                  # Pydantic 数据模型（POCO）
│   │   ├── __init__.py
│   │   ├── task.py              # OrbitTask, SubTask, TaskStatus
│   │   └── agent_models.py      # AgentCapability, AgentResponse
│   ├── agents/                  # Agent 定义（基于 OpenAI Agents SDK）
│   │   ├── __init__.py
│   │   ├── base.py              # 基础 Agent 抽象类
│   │   ├── planner.py           # 任务拆解与规划
│   │   ├── researcher.py        # 信息检索与调研
│   │   ├── coder.py             # 代码生成与修改
│   │   ├── reviewer.py          # 结果审核与质检
│   │   └── executor.py          # 最终动作执行（通知/写入）
│   ├── scheduler/               # 调度引擎
│   │   ├── __init__.py
│   │   ├── dispatcher.py        # DAG 解析 + 并发分发
│   │   └── priority.py          # 优先级队列逻辑
│   ├── temporal/                # Temporal 工作流定义
│   │   ├── __init__.py
│   │   ├── workflows.py         # OrbitWorkflow 定义
│   │   ├── activities.py        # 封装各 Agent 调用的 Activity
│   │   └── client.py            # Temporal Client 单例
│   ├── memory/                  # 记忆系统
│   │   ├── __init__.py
│   │   ├── semantic.py          # 向量记忆增删查 (ChromaDB/PGVector)
│   │   └── graph_rag.py         # 图谱构建与多跳检索
│   ├── observability/           # 可观测性
│   │   ├── __init__.py
│   │   ├── tracer.py            # OpenTelemetry Tracer 封装
│   │   └── metrics.py           # Prometheus 指标（可选）
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       └── logger.py            # 结构化日志
├── tests/                       # 测试目录（与 src 结构对应）
│   ├── __init__.py
│   ├── unit/
│   └── integration/
└── scripts/                     # 辅助脚本
    └── init_db.sql              # 初始化 PG 表结构
```

---

## 🧪 5. 验收标准与评估指标

项目完成时需达到以下量化目标（作为 Trae 实现时的性能指引）：

| 指标 | 目标值 | 测量方式 |
| :--- | :--- | :--- |
| 复杂任务端到端成功率 | ≥ 85% | 基于 50+ 个预定义测试集 |
| 子任务调度延迟（不含 LLM） | < 200ms (P95) | 内部计时器 |
| Temporal 任务恢复成功率 | 100% | 手动注入故障（Kill Worker）后验证 |
| Trace 覆盖率 | 100% | 每个 HTTP 请求均生成完整 Trace |
| Token 消耗优化（vs 单 Agent） | 降低 ≥ 40% | 统计 LLM 调用 Token 总数 |
| GraphRAG 多跳召回率提升 | ≥ 15% (vs 传统 RAG) | 使用人工标注的复杂问答对 |

---

## 🚦 6. 开发路线图（Sprint 计划）

| 阶段 | 任务 | 交付物 |
| :--- | :--- | :--- |
| **Sprint 1** | **项目骨架与数据模型** | `pyproject.toml`、Docker Compose、Pydantic Models、Temporal Client 占位 |
| **Sprint 2** | **调度器 (DAG) + Planner Agent** | 任务拆解逻辑、依赖图解析、并发分发框架 |
| **Sprint 3** | **Temporal 工作流集成** | `OrbitWorkflow` 定义、Activities 实现、断点续传验证 |
| **Sprint 4** | **多 Agent 实现 + A2A 通信** | 5 类 Agent 具体 Prompt 与调用逻辑、Agent 间消息总线 |
| **Sprint 5** | **可观测性 + 记忆 + GraphRAG** | OTel Span 埋点、Jaeger 展示、向量记忆存储与检索 |
| **Sprint 6** | **评估与压测** | 基准测试脚本、量化指标收集、README 更新 |

---

## 📌 7. AI 助手行为准则（给 Trae 的强制约束）

> 以下规则 Trae 在生成任何代码时必须严格遵守：

1. **技术栈锁定**：严禁引入 `langchain`、`langgraph`、`redis`（作为 Broker）、`rabbitmq`。若需状态存储，优先使用 Temporal 或 PostgreSQL。
2. **异步优先**：所有 I/O 操作（HTTP、DB、Temporal）必须使用 `async/await` 语法。
3. **类型安全**：所有函数必须标注参数与返回值类型（Type Hints），所有数据容器必须使用 Pydantic 模型。
4. **测试驱动**：新增核心功能（如 Scheduler、Temporal Workflow）必须同步生成对应的 `pytest-asyncio` 单元测试。
5. **配置外部化**：数据库连接、Temporal 地址、OpenAI Key 等必须从 `.env` 环境变量读取，禁止硬编码。
6. **最小生成原则**：若用户（我）未明确要求，禁止额外生成与当前 Sprint 无关的复杂模块（如前端界面、K8s 编排文件）。
7. **日志结构化**：使用 `structlog` 或标准 `logging` 输出 JSON 格式日志，便于后续采集。

---

## 🛠️ 8. 快速启动（开发环境）

```bash
# 1. 克隆项目并进入目录
cd orbit-runtime

# 2. 启动基础中间件（Temporal + Jaeger + Postgres）
docker-compose up -d

# 3. 安装 Python 依赖（使用 uv，若没有则: pip install uv）
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# 4. 运行测试（验证环境是否就绪）
pytest tests/

# 5. 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📚 9. 参考资料

- [OpenAI Agents SDK 官方文档](https://openai.github.io/openai-agents-python/)
- [Temporal Python SDK 文档](https://docs.temporal.io/developer-guide/python/)
- [A2A Protocol 草案](https://a2a-protocol.org) *(注：当前可能未完全标准化，设计时参照其核心思路即可)*
- [OpenTelemetry Python 手册](https://opentelemetry.io/docs/languages/python/)

---

> **版本**：v0.1.0 | **最后更新**：2026-07-08 | **维护者**：何涛
```

---
