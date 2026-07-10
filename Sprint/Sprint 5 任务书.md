## 📋 【Sprint 5 任务书：可视化调度决策 + 基准评估】

### 🧭 核心目标

构建三个交付物，让智能调度的效果被直观看见和量化评估：

1. **结构化决策日志**：每次调度记录预估 vs 实际、投机执行命中情况
2. **Web 调试面板**：一个极简页面展示决策日志和对比图表
3. **基准评估脚本**：自动化运行测试任务，输出量化指标报告

---

### 📂 允许修改/新增的文件（严格限定）

| 操作 | 文件路径 | 内容说明 |
| :--- | :--- | :--- |
| **修改** | `src/orbit/scheduler/smart_dispatcher.py` | 在 `dispatch` 方法中记录决策日志到 `self.decision_logs` |
| **修改** | `src/orbit/scheduler/budget_estimator.py` | `estimate` 返回值增加 `actual_tokens` 字段（预留，供后续对比） |
| **新增** | `src/orbit/api/routes.py` | 添加 `GET /api/scheduler/logs` 和 `GET /api/scheduler/stats` 两个路由 |
| **新增** | `src/orbit/api/dashboard.py` | （可选）如果 routes 已复杂，可单独拆分；但建议直接在 routes.py 中新增 |
| **新增** | `src/orbit/api/static/dashboard.html` | 调试面板 HTML 文件（内嵌 CSS + ECharts CDN） |
| **新增** | `scripts/run_benchmark.py` | 基准评估脚本，运行 20 个预定义测试任务并输出报告 |
| **新增** | `scripts/benchmark_tasks.json` | 预定义的 20 个测试任务描述（JSON 格式） |

**注意**：`static` 目录需在 `main.py` 中挂载静态文件服务：
```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="src/orbit/api/static"), name="static")
```

---

### 🚫 严格禁止

1. **禁止**新增任何外部依赖（ECharts 通过 CDN 加载，不写入 `pyproject.toml`）。
2. **禁止**修改任何测试文件（`tests/` 下的 30 个测试必须保持全绿）。
3. **禁止**实现数据库持久化（日志仅存内存，服务重启即重置）。
4. **禁止**修改 `planner.py` 或 `activities.py`（Sprint 4 的功能已稳定，不再动）。
5. **禁止**引入前端构建工具（Vue/React 等），仅用原生 HTML + CDN。

---

### 🔧 模块规格说明

#### A. 修改 `smart_dispatcher.py` —— 记录决策日志

在 `SmartDispatcher` 的 `__init__` 中增加：
```python
self.decision_logs = []  # 存储最近 100 条日志
self.max_logs = 100
```

在 `dispatch` 方法的关键节点（预估、执行、投机）记录日志，每条日志格式：
```python
{
    "task_id": str,
    "timestamp": str (ISO 格式),
    "subtask_id": str,
    "agent_type": str,
    "estimated_tokens": int,
    "estimated_time_ms": int,
    "actual_tokens": int,  # Sprint 5 中设为预估值的 0.8~1.2 倍随机模拟，后续可接真实统计
    "actual_time_ms": int, # 同上，模拟值
    "speculation_triggered": bool,
    "speculation_branches": int,  # 触发投机时的分支数
    "speculation_hit": bool,  # 投机执行的分支是否被最终采用
    "status": str  # "success" | "failed" | "compensated"
}
```

> **关于 `actual_tokens` 和 `actual_time_ms`**：Sprint 5 中由于仍是 Mock 执行，可以用 `estimated * random.uniform(0.8, 1.2)` 生成模拟值，但**在注释中明确标记为 "TODO: 接入真实 LLM 调用统计"**，体现你对后续优化的思考。

#### B. 新增 `routes.py` 中的 API 路由

```python
@router.get("/scheduler/logs")
async def get_scheduler_logs(limit: int = 20):
    """返回最近的调度决策日志"""
    # 从 SmartDispatcher 实例获取日志（需要将 dispatcher 设为全局单例或通过依赖注入）
    pass

@router.get("/scheduler/stats")
async def get_scheduler_stats():
    """返回汇总统计：总任务数、平均预估误差、投机命中率等"""
    pass
```

> **关于依赖注入**：如果 `SmartDispatcher` 是在 `main.py` 中初始化的，可以通过 `app.state.dispatcher` 存储，然后在路由中通过 `request.app.state.dispatcher` 访问。

#### C. 新增 `dashboard.html` —— 调试面板

页面功能要求：
1. **日志表格**：展示最近 20 条决策日志，包含所有关键字段。
2. **预估 vs 实际对比图**：用 ECharts 柱状图展示最近 10 次调度的 Token 预估与“实际”对比。
3. **统计卡片**：顶部显示：总任务数、平均预估误差率、投机命中率。
4. **自动刷新**：每 5 秒自动刷新数据（`setInterval` 调用 API）。

> **ECharts CDN**：`https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`

#### D. 新增 `scripts/run_benchmark.py` —— 基准评估脚本

功能：
1. 从 `benchmark_tasks.json` 读取 20 个预定义测试任务（涵盖 Planner/Researcher/Coder/Reviewer/Executor 各种组合）。
2. 依次执行每个任务，收集调度日志。
3. 输出 `benchmark_report.json`，包含：
   ```json
   {
       "total_tasks": 20,
       "success_rate": 0.85,
       "avg_estimation_error": 0.12,  // 平均绝对百分比误差
       "speculation_hit_rate": 0.67,
       "avg_scheduling_latency_ms": 45,
       "patch_generation_success_rate": 0.90,
       "details": [...]
   }
   ```

> **注意**：脚本应使用 `uv run` 执行，且**不依赖任何真实 LLM API**（即所有 LLM 调用使用 Mock 或已配置的测试环境）。

---

### 🧪 验收标准

| 检查项 | 验证方式 |
| :--- | :--- |
| 原有的 30 个测试全绿 | 运行 `pytest tests/ -v` |
| 访问 `/api/scheduler/logs` 返回 JSON | 浏览器访问或 `curl` |
| 访问 `/static/dashboard.html` 显示页面 | 浏览器打开，无 404 错误 |
| 页面能展示图表和日志表格 | 肉眼确认 |
| `run_benchmark.py` 能完整运行并输出 JSON | 运行 `uv run python scripts/run_benchmark.py` |
| **无新增依赖** | 检查 `pyproject.toml` 未被修改 |

