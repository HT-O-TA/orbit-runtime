from typing import List, Dict
from ..models.task import SubTask


class PatchManager:
    def __init__(self):
        self.patches: Dict[str, List[SubTask]] = {}

    def add_patch(self, original_subtask_id: str, patches: List[SubTask]) -> None:
        if original_subtask_id not in self.patches:
            self.patches[original_subtask_id] = []
        self.patches[original_subtask_id].extend(patches)

    def get_patches_for(self, subtask_id: str) -> List[SubTask]:
        return self.patches.get(subtask_id, [])

    def clear(self) -> None:
        self.patches.clear()
