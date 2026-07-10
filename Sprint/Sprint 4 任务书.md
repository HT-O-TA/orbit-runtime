## 📋 【Sprint 4 任务书·严格版：注入真实 LLM 推理】

### 🧭 目标（唯一且专注）

将 `BudgetEstimator` 和 `Planner.post_mortem` 从“硬编码/Mock”升级为“调用轻量级 LLM（如 Qwen2.5-0.5B）进行真实推理”，使调度器具备动态预估和智能复盘能力。

### 📂 允许修改的文件（仅限以下 3 个）

| 文件 | 修改内容 |
| :--- | :--- |
| `src/orbit/scheduler/budget_estimator.py` | 将 `estimate` 改为 `async`，内部调用 LLM API |
| `src/orbit/agents/planner.py` | 将 `post_mortem` 改为 `async`，内部调用 LLM API 生成补丁 JSON |
| `src/orbit/scheduler/smart_dispatcher.py` | 将 `dispatch` 中调用 `estimate` 的地方改为 `await` |

### 🚫 严格禁止（请 Trae 务必遵守）

- **禁止**创建任何新文件（包括测试文件、配置文件、工具类）。
- **禁止**修改 `pyproject.toml` 或新增依赖（我们会在 Sprint 4 完成后统一手动添加 `openai` SDK）。
- **禁止**实现真实 HTTP 客户端（直接用 `AsyncOpenAI` 的默认配置，不要封装自己的 `http_client`）。
- **禁止**添加日志框架（继续使用 `print` 即可）。
- **禁止**为“未来扩展”预留抽象类或接口。

### 🧪 验收标准（Trae 必须在完成后自检）

1. `BudgetEstimator.estimate` 被标记为 `async`，且能返回 `{"tokens": int, "time_ms": int}`。
2. `Planner.post_mortem` 被标记为 `async`，且能返回 `List[SubTask]`。
3. 所有依赖 LLM 调用的方法，在 API 失败时自动降级为原有硬编码值（`try-except` 包裹）。
4. 运行 `pytest tests/`，原有的 30 个测试依然全部通过（因为测试用的是 Mock，不依赖真实 LLM）。
5. **不新增任何新文件**，`git status` 显示只有 3 个文件被修改。

### 📝 给 Trae 的补充说明

- **关于 LLM 客户端**：使用 `openai.AsyncOpenAI`，`base_url` 和 `api_key` 从环境变量 `LLM_API_BASE` 和 `LLM_API_KEY` 读取（如果没有，则打印警告并降级）。
- **关于补丁生成**：确保 LLM 输出的 JSON 符合 `SubTask` 的 Pydantic 模型，如果解析失败，降级为硬编码补丁。
- **关于测试**：不需要新增测试，因为原有测试通过 Mock 覆盖了逻辑路径。

---