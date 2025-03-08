from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum, auto
from datetime import datetime
import os
import json
import asyncio
import logging

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TaskProgress:
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    start_time: datetime = None
    end_time: datetime = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.context is None:
            self.context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.name
        data['start_time'] = self.start_time.isoformat() if self.start_time else None
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus[data['status']]
        if 'start_time' in data and data['start_time'] and isinstance(data['start_time'], str):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if 'end_time' in data and data['end_time'] and isinstance(data['end_time'], str):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
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
            if context is None:
                context = {}
            self.tasks[task_id] = TaskProgress(
                task_id=task_id,
                context=context,
                start_time=datetime.now()
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
                task.end_time = datetime.now() if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] else None
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
        """Get pending changes to be applied"""
        return self.pending_changes
    
    async def save_checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """Save a checkpoint of current progress"""
        self.pending_changes.append(checkpoint_data)
        await self._save_progress()
    
    async def load_progress(self) -> Dict[str, Any]:
        """Load progress from file"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load tasks
                    if 'tasks' in data and isinstance(data['tasks'], list):
                        for task_data in data['tasks']:
                            try:
                                task = TaskProgress.from_dict(task_data)
                                self.tasks[task.task_id] = task
                            except Exception as e:
                                logging.error(f"Error loading task: {e}")
                    
                    # Load pending changes
                    if 'pending_changes' in data and isinstance(data['pending_changes'], list):
                        self.pending_changes = data['pending_changes']
                    
                    return {
                        'current_task': data.get('current_task', ''),
                        'last_file': data.get('last_file_edited', ''),
                        'last_position': data.get('last_position', ''),
                        'remaining_tasks': self.get_pending_tasks(),
                        'pending_changes': self.pending_changes
                    }
            else:
                return {
                    'current_task': '',
                    'last_file': '',
                    'last_position': '',
                    'remaining_tasks': [],
                    'pending_changes': []
                }
                
        except Exception as e:
            logging.error(f"Error loading progress: {e}")
            return {
                'current_task': '',
                'last_file': '',
                'last_position': '',
                'remaining_tasks': [],
                'pending_changes': []
            }
    
    async def _save_progress(self) -> None:
        """Save progress to file"""
        try:
            data = {
                'last_update': datetime.now().isoformat(),
                'current_task': next(iter(self.get_pending_tasks()), ''),
                'tasks': [task.to_dict() for task in self.tasks.values()],
                'completed_tasks': [
                    task_id for task_id, task in self.tasks.items() 
                    if task.status == TaskStatus.COMPLETED
                ],
                'remaining_tasks': self.get_pending_tasks(),
                'task_context': {},
                'last_file_edited': '',
                'pending_changes': self.pending_changes
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=4)
                
        except Exception as e:
            logging.error(f"Error saving progress: {e}")
    
    async def reset(self) -> None:
        """Reset all progress"""
        async with self._lock:
            self.tasks.clear()
            self.pending_changes.clear()
            await self._save_progress()