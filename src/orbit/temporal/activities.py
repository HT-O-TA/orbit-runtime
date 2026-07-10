import asyncio
import random
import os
from temporalio import activity
from ..models.task import SubTask


@activity.defn
async def execute_subtask(subtask: SubTask) -> str:
    if subtask.agent_type == "executor":
        await asyncio.sleep(0.05)
        return f"Executed {subtask.id} successfully"

    fail_rate = float(os.environ.get("ACTIVITY_FAIL_RATE", "0.2"))
    if random.random() < fail_rate:
        raise Exception(f"Simulated failure for {subtask.id} (timeout)")

    await asyncio.sleep(0.1)

    if subtask.agent_type == "planner":
        return f"Planned DAG for {subtask.id}"
    elif subtask.agent_type == "researcher":
        return f"Research result for {subtask.id}: found 5 relevant documents"
    elif subtask.agent_type == "coder":
        return f"Code generated for {subtask.id}: def solution(): pass"
    elif subtask.agent_type == "reviewer":
        return f"Review passed for {subtask.id}"
    else:
        return f"Executed {subtask.id} successfully"
