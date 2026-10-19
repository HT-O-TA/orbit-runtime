# Orbit Runtime

面向多智能体长流程任务的调度实验项目，探索 DAG 依赖执行、Token 预算估计、候选分支执行与失败补偿。使用 Python、FastAPI 和 Temporal 组织 API、调度器及工作流模块。

> 当前为工程原型：调度、工作流与 Agent 模块已有代码，Web API 尚未贯通完整持久化执行链路。首页展示的是实现范围，不将规划目标作为已测性能。

## 研究内容

- **依赖调度**：任务模型、依赖图、环检测、拓扑排序和就绪任务选择。
- **预算估计**：对子任务估计 Token 与耗时，并据此调整处理顺序。
- **候选分支执行**：通过独立执行器探索分支并发与结果选择。
- **失败补偿**：Temporal Activity 失败后生成补丁子任务；Planner 支持模型调用与缺配置时的降级路径。
- **观测与演示**：调度决策日志、统计 API、OpenTelemetry 模块和静态仪表盘。

## 当前实现边界

| 模块 | 实现与限制 |
| --- | --- |
| FastAPI | 提供任务提交、状态、健康检查及调度统计接口；`/submit` 当前返回规划结果，未启动完整工作流 |
| Planner | 当前初始拆解为固定的分析、调研、审核任务；不代表通用模型规划已完成 |
| SmartDispatcher | 已有预算排序和分支执行逻辑；日志中的 Token、耗时字段包含模拟值，不用于真实降本结论 |
| Temporal | 包含 Workflow、Activity 与补丁管理代码；需要独立部署、启动 Worker 并验证恢复行为 |
| 任务状态 | `/status/{task_id}` 当前为占位响应，未接持久化状态查询 |
| 记忆与通信 | 语义记忆模块及 Agent 模型用于扩展实验；不宣称完整 GraphRAG 或标准 A2A 互操作 |

## 代码导航

```text
main.py                         FastAPI 入口
src/orbit/
├── models/                     任务与 Agent 数据模型
├── agents/                     Planner、Researcher、Reviewer
├── scheduler/                  基础调度、预算估计、分支执行
├── temporal/                   Workflow、Activity、补丁管理
├── memory/                     语义记忆模块
├── observability/              Trace 配置
└── api/                        调度接口与静态仪表盘
tests/                          模型、调度器与工作流相关测试
scripts/                        基准脚本与数据库初始化材料
```

## 本地开发

需要 Python 3.12 或以上版本。以下命令在仓库根目录执行：

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell 改用：.\.venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
python -m uvicorn main:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

启动后访问：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`GET /health`
- 仪表盘：`http://127.0.0.1:8000/static/dashboard.html`
- 调度日志：`GET /api/scheduler/logs`
- 调度统计：`GET /api/scheduler/stats`

Temporal 等依赖的开发配置见 [docker-compose.yml](docker-compose.yml)。启动 API 不会自动启动 Temporal Worker。

## 测试与后续方向

```bash
python -m pytest tests/
```

测试实现与基准脚本分别位于 [tests](tests/) 和 [scripts](scripts/)。当前首页不报告未复核的成功率、延迟、恢复率或 Token 节省比例。

后续重点是贯通 API 与工作流、持久化状态查询、用真实调用替换模拟观测值，以及验证分支执行与补偿的正确性。阶段任务材料保留在 [Sprint](Sprint/) 供追溯。

