import os
import json
import asyncio
import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum, auto

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TaskProgress:
    name: str
    status: TaskStatus
    progress: float  # 0-100
    message: str
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    error: Optional[str] = None

class AsyncProgressTracker:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.progress_file = os.path.join(workspace_root, 'agent_progress.json')
        self.current_state = self._load_or_create_state()
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._task_queues: Dict[str, asyncio.Queue] = {}

    def _load_or_create_state(self) -> Dict[str, Any]:
        """Load existing progress state or create new one"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_initial_state()
        return self._create_initial_state()

    def _create_initial_state(self) -> Dict[str, Any]:
        """Create initial progress tracking state with task progress"""
        return {
            "last_update": "",
            "current_task": "",
            "tasks": [],
            "completed_tasks": [],
            "remaining_tasks": [],
            "task_context": {},
            "last_file_edited": "",
            "last_edit_position": "",
            "error_context": "",
            "workspace_state": {
                "files_modified": [],
                "pending_changes": []
            },
            "task_progress": {}
        }

    async def save_state_async(self) -> None:
        """Save current progress state to file asynchronously"""
        self.current_state["last_update"] = datetime.datetime.now().isoformat()
        try:
            # Run file write in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._save_state_sync
            )
        except Exception as e:
            print(f"Error saving progress state: {e}")

    def _save_state_sync(self) -> None:
        """Synchronous state saving implementation"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.current_state, f, indent=4)

    def register_progress_callback(self, task_id: str, callback: Callable[[TaskProgress], None]) -> None:
        """Register a callback for progress updates"""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)

    def _notify_progress(self, task_id: str, progress: TaskProgress) -> None:
        """Notify all registered callbacks of progress update"""
        if task_id in self._progress_callbacks:
            for callback in self._progress_callbacks[task_id]:
                try:
                    callback(progress)
                except Exception as e:
                    print(f"Error in progress callback: {e}")

    async def update_task_progress(self, task_id: str, progress: float, 
                                 message: str, status: TaskStatus) -> None:
        """Update task progress and notify callbacks"""
        task_progress = TaskProgress(
            name=task_id,
            status=status,
            progress=progress,
            message=message,
            started_at=datetime.datetime.now() if status == TaskStatus.IN_PROGRESS else None,
            completed_at=datetime.datetime.now() if status in 
                       [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] else None
        )
        
        self.current_state["task_progress"][task_id] = {
            "status": status.name,
            "progress": progress,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self._notify_progress(task_id, task_progress)
        await self.save_state_async()

    async def start_task(self, task_id: str) -> None:
        """Start tracking a task"""
        await self.update_task_progress(
            task_id, 0.0, "Starting...", TaskStatus.IN_PROGRESS
        )

    async def complete_task(self, task_id: str) -> None:
        """Mark a task as completed"""
        await self.update_task_progress(
            task_id, 100.0, "Completed", TaskStatus.COMPLETED
        )
        if task_id in self.current_state["tasks"]:
            self.current_state["tasks"].remove(task_id)
            self.current_state["completed_tasks"].append(task_id)
            await self.save_state_async()

    async def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed"""
        task_progress = TaskProgress(
            name=task_id,
            status=TaskStatus.FAILED,
            progress=0.0,
            message=f"Failed: {error}",
            error=error
        )
        self._notify_progress(task_id, task_progress)
        await self.save_state_async()

    async def cancel_task(self, task_id: str) -> None:
        """Mark a task as cancelled"""
        await self.update_task_progress(
            task_id, 0.0, "Cancelled", TaskStatus.CANCELLED
        )

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a task"""
        return self.current_state["task_progress"].get(task_id)

    def get_active_tasks(self) -> List[str]:
        """Get list of tasks currently in progress"""
        return [
            task_id for task_id, progress in self.current_state["task_progress"].items()
            if progress["status"] == TaskStatus.IN_PROGRESS.name
        ]

    async def cleanup(self) -> None:
        """Clean up resources and save final state"""
        # Cancel all active tasks
        active_tasks = self.get_active_tasks()
        for task_id in active_tasks:
            await self.cancel_task(task_id)
        
        # Save final state
        await self.save_state_async()

    # Original methods remain but delegate to async versions where appropriate
    def set_current_task(self, task: str) -> None:
        """Set the current task being worked on"""
        self.current_state["current_task"] = task
        asyncio.create_task(self.save_state_async())

    def add_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Add a new task to the task list"""
        if task not in self.current_state["tasks"]:
            self.current_state["tasks"].append(task)
            if context:
                self.current_state["task_context"][task] = context
            asyncio.create_task(self.save_state_async())

    def add_modified_file(self, file_path: str) -> None:
        """Track a modified file"""
        rel_path = os.path.relpath(file_path, self.workspace_root)
        if rel_path not in self.current_state["workspace_state"]["files_modified"]:
            self.current_state["workspace_state"]["files_modified"].append(rel_path)
            asyncio.create_task(self.save_state_async())

    def set_last_edit_position(self, file_path: str, position: str) -> None:
        """Track the last edit position in a file"""
        self.current_state["last_file_edited"] = os.path.relpath(file_path, self.workspace_root)
        self.current_state["last_edit_position"] = position
        asyncio.create_task(self.save_state_async())

    def add_pending_change(self, change: Dict[str, Any]) -> None:
        """Add a pending change that needs to be applied"""
        self.current_state["workspace_state"]["pending_changes"].append(change)
        asyncio.create_task(self.save_state_async())

    def clear_pending_changes(self) -> None:
        """Clear all pending changes after they've been applied"""
        self.current_state["workspace_state"]["pending_changes"] = []
        asyncio.create_task(self.save_state_async())

    def log_error(self, error_context: str) -> None:
        """Log an error context for debugging"""
        self.current_state["error_context"] = error_context
        asyncio.create_task(self.save_state_async())

    def get_resume_point(self) -> Dict[str, Any]:
        """Get information needed to resume work"""
        return {
            "current_task": self.current_state["current_task"],
            "last_file": self.current_state["last_file_edited"],
            "last_position": self.current_state["last_edit_position"],
            "pending_changes": self.current_state["workspace_state"]["pending_changes"],
            "remaining_tasks": self.current_state["tasks"]
        }

    def clear_state(self) -> None:
        """Reset the progress tracking state"""
        self.current_state = self._create_initial_state()
        asyncio.create_task(self.save_state_async())

    def get_task_context(self, task: str) -> Optional[Dict[str, Any]]:
        """Get the context for a specific task"""
        return self.current_state["task_context"].get(task)

    def get_modified_files(self) -> List[str]:
        """Get list of modified files"""
        return self.current_state["workspace_state"]["files_modified"]