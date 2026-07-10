from fastapi import APIRouter, Request, Query
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api")


@router.get("/scheduler/logs", response_model=List[Dict[str, Any]])
async def get_scheduler_logs(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    dispatcher = getattr(request.app.state, "dispatcher", None)
    if not dispatcher:
        return []
    logs = dispatcher.decision_logs[-limit:]
    return logs


@router.get("/scheduler/stats", response_model=Dict[str, Any])
async def get_scheduler_stats(request: Request) -> Dict[str, Any]:
    dispatcher = getattr(request.app.state, "dispatcher", None)
    if not dispatcher or not dispatcher.decision_logs:
        return {
            "total_tasks": 0,
            "total_subtasks": 0,
            "success_rate": 0.0,
            "avg_estimation_error": 0.0,
            "speculation_hit_rate": 0.0,
            "avg_scheduling_latency_ms": 0,
            "patch_generation_success_rate": 0.0,
        }

    logs = dispatcher.decision_logs
    total_subtasks = len(logs)
    success_count = sum(1 for log in logs if log["status"] == "success")
    speculation_triggered = sum(1 for log in logs if log["speculation_triggered"])
    speculation_hits = sum(1 for log in logs if log["speculation_hit"])

    error_sum = 0.0
    error_count = 0
    for log in logs:
        if log["estimated_tokens"] > 0:
            error_sum += abs(log["actual_tokens"] - log["estimated_tokens"]) / log["estimated_tokens"]
            error_count += 1

    avg_error = error_sum / error_count if error_count > 0 else 0.0

    return {
        "total_tasks": len(set(log["task_id"] for log in logs)),
        "total_subtasks": total_subtasks,
        "success_rate": success_count / total_subtasks if total_subtasks > 0 else 0.0,
        "avg_estimation_error": avg_error,
        "speculation_hit_rate": speculation_hits / speculation_triggered if speculation_triggered > 0 else 0.0,
        "avg_scheduling_latency_ms": sum(log["actual_time_ms"] for log in logs) // total_subtasks if total_subtasks > 0 else 0,
        "patch_generation_success_rate": 0.0,
    }
