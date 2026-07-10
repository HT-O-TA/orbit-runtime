from typing import List, Dict, Set, Optional
from ..models.task import OrbitTask, SubTask, TaskStatus


class TaskDispatcher:
    def __init__(self):
        self.executed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()

    def get_ready_tasks(self, task: OrbitTask) -> List[SubTask]:
        ready = []
        for subtask in task.sub_tasks:
            if subtask.status != TaskStatus.PENDING:
                continue
            if subtask.id in self.executed_tasks:
                continue
            if all(dep in self.executed_tasks for dep in subtask.dependencies):
                ready.append(subtask)
        return ready

    def mark_started(self, subtask_id: str) -> None:
        self.running_tasks.add(subtask_id)

    def mark_completed(self, subtask_id: str, result: str) -> None:
        self.executed_tasks.add(subtask_id)
        self.running_tasks.discard(subtask_id)

    def has_cycles(self, dag: Dict[str, List[str]]) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in dag.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in dag:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def topological_sort(self, dag: Dict[str, List[str]]) -> Optional[List[str]]:
        if self.has_cycles(dag):
            return None

        in_degree = {node: 0 for node in dag}
        for node in dag:
            for neighbor in dag[node]:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1

        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in dag.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(dag):
            return None
        return result

    def is_task_complete(self, task: OrbitTask) -> bool:
        return all(st.status == TaskStatus.COMPLETED for st in task.sub_tasks)
