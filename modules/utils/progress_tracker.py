from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum, auto
import json
import os
import asyncio
from datetime import datetime

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TaskProgress:
    """Data class to hold task progress information"""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    context: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.context is None:
            self.context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['status'] = self.status.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        """Create instance from dictionary"""
        data['status'] = TaskStatus[data['status']]
        return cls(**data)

class AsyncProgressTracker:
    """Asynchronously track progress of tasks"""
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.progress_file = os.path.join(workspace_root, "agent_progress.json")
        self.tasks: Dict[str, TaskProgress] = {}
        self._lock = asyncio.Lock()
        self.pending_changes: List[Dict[str, Any]] = []
        
    async def add_task(self, task_id: str, context: Dict[str, Any] = None) -> None:
        """Add a new task to track"""
        async with self._lock:
            self.tasks[task_id] = TaskProgress(
                task_id=task_id,
                context=context or {}
            )
            await self._save_progress()
    
    async def update_task_progress(self, task_id: str, progress: float, 
                                 message: str, status: TaskStatus) -> None:
        """Update progress of a task"""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.progress = progress
                task.message = message
                task.status = status
                task.timestamp = datetime.now().isoformat()
                await self._save_progress()
    
    async def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get context for a specific task"""
        if task_id in self.tasks:
            return self.tasks[task_id].context
        return None
    
    def get_pending_tasks(self) -> List[str]:
        """Get list of pending task IDs"""
        return [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        ]
    
    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get list of pending changes"""
        return self.pending_changes
    
    async def save_checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """Save a progress checkpoint"""
        async with self._lock:
            self.pending_changes.append({
                'timestamp': datetime.now().isoformat(),
                **checkpoint_data
            })
            await self._save_progress()
    
    async def load_progress(self) -> Dict[str, Any]:
        """Load progress from file"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    
                # Restore tasks
                self.tasks = {
                    task_id: TaskProgress.from_dict(task_data)
                    for task_id, task_data in data.get('tasks', {}).items()
                }
                
                # Restore pending changes
                self.pending_changes = data.get('pending_changes', [])
                
                return {
                    'current_task': data.get('current_task'),
                    'last_file': data.get('last_file'),
                    'last_position': data.get('last_position'),
                    'pending_changes': self.pending_changes,
                    'remaining_tasks': self.get_pending_tasks()
                }
        except Exception as e:
            print(f"Error loading progress: {e}")
            return {
                'current_task': None,
                'last_file': None,
                'last_position': None,
                'pending_changes': [],
                'remaining_tasks': []
            }
    
    async def _save_progress(self) -> None:
        """Save current progress to file"""
        async with self._lock:
            data = {
                'tasks': {
                    task_id: task.to_dict()
                    for task_id, task in self.tasks.items()
                },
                'pending_changes': self.pending_changes,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                with open(self.progress_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error saving progress: {e}")
    
    async def reset(self) -> None:
        """Reset all progress"""
        async with self._lock:
            self.tasks.clear()
            self.pending_changes.clear()
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)