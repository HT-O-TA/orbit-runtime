import json
import asyncio
import os
import sys
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orbit.scheduler.smart_dispatcher import SmartDispatcher
from orbit.models.task import OrbitTask, SubTask, TaskStatus


async def mock_executor(subtask: SubTask) -> str:
    await asyncio.sleep(0.05)
    return f"ok_{subtask.id}"


def load_tasks(file_path: str) -> List[Dict[str, Any]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_orbit_task(task_data: Dict[str, Any]) -> OrbitTask:
    subtasks = [
        SubTask(
            id=st['id'],
            name=st['name'],
            agent_type=st['agent_type'],
            dependencies=st['dependencies'],
            input_context=st['input_context'],
            status=TaskStatus.PENDING
        )
        for st in task_data['sub_tasks']
    ]
    return OrbitTask(
        task_id=task_data['task_id'],
        user_query=task_data['user_query'],
        sub_tasks=subtasks,
        dag_adjacency=task_data['dag_adjacency'],
        created_at="2026-07-09"
    )


async def run_benchmark(tasks_file: str) -> Dict[str, Any]:
    tasks_data = load_tasks(tasks_file)
    dispatcher = SmartDispatcher(mock_executor)
    
    total_tasks = len(tasks_data)
    success_count = 0
    all_logs = []
    total_latency = 0

    print(f"🚀 开始基准评估，共 {total_tasks} 个任务...")
    
    for i, task_data in enumerate(tasks_data, 1):
        print(f"\n[{i}/{total_tasks}] 执行任务: {task_data['task_id']}")
        orbit_task = create_orbit_task(task_data)
        
        start_time = asyncio.get_event_loop().time()
        result = await dispatcher.dispatch(orbit_task)
        end_time = asyncio.get_event_loop().time()
        
        latency_ms = int((end_time - start_time) * 1000)
        total_latency += latency_ms
        
        is_success = all(st.status == TaskStatus.COMPLETED for st in result.sub_tasks)
        if is_success:
            success_count += 1
        
        all_logs.extend(dispatcher.decision_logs)
        
        print(f"  耗时: {latency_ms}ms, 状态: {'成功' if is_success else '失败'}")

    print("\n" + "="*60)
    print("📊 基准评估报告")
    print("="*60)

    total_subtasks = len(all_logs)
    success_rate = success_count / total_tasks if total_tasks > 0 else 0.0

    error_sum = 0.0
    error_count = 0
    for log in all_logs:
        if log["estimated_tokens"] > 0:
            error_sum += abs(log["actual_tokens"] - log["estimated_tokens"]) / log["estimated_tokens"]
            error_count += 1
    avg_error = error_sum / error_count if error_count > 0 else 0.0

    speculation_triggered = sum(1 for log in all_logs if log["speculation_triggered"])
    speculation_hits = sum(1 for log in all_logs if log["speculation_hit"])
    speculation_hit_rate = speculation_hits / speculation_triggered if speculation_triggered > 0 else 0.0

    avg_latency = total_latency // total_tasks if total_tasks > 0 else 0

    report = {
        "total_tasks": total_tasks,
        "success_rate": round(success_rate, 4),
        "avg_estimation_error": round(avg_error, 4),
        "speculation_hit_rate": round(speculation_hit_rate, 4),
        "avg_scheduling_latency_ms": avg_latency,
        "patch_generation_success_rate": 0.0,
        "details": [
            {
                "task_id": log["task_id"],
                "subtask_id": log["subtask_id"],
                "agent_type": log["agent_type"],
                "estimated_tokens": log["estimated_tokens"],
                "actual_tokens": log["actual_tokens"],
                "estimated_time_ms": log["estimated_time_ms"],
                "actual_time_ms": log["actual_time_ms"],
                "speculation_triggered": log["speculation_triggered"],
                "status": log["status"]
            }
            for log in all_logs
        ]
    }

    print(f"总任务数: {total_tasks}")
    print(f"成功率: {success_rate * 100:.1f}%")
    print(f"平均预估误差率: {avg_error * 100:.1f}%")
    print(f"投机命中率: {speculation_hit_rate * 100:.1f}%")
    print(f"平均调度延迟: {avg_latency}ms")

    output_path = os.path.join(os.path.dirname(__file__), 'benchmark_report.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 报告已保存到: {output_path}")
    
    return report


if __name__ == "__main__":
    tasks_file = os.path.join(os.path.dirname(__file__), 'benchmark_tasks.json')
    asyncio.run(run_benchmark(tasks_file))
