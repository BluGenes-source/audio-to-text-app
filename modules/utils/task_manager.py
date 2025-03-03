import os
import asyncio
from typing import List, Dict, Any, Optional, Callable
from .progress_tracker import AsyncProgressTracker, TaskProgress, TaskStatus

class TaskManager:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.progress = AsyncProgressTracker(workspace_root)
        self._status_callback: Optional[Callable[[str], None]] = None
        
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for status updates"""
        self._status_callback = callback
        
    async def start_task_sequence(self, tasks: List[Dict[str, Any]]) -> None:
        """Initialize a sequence of tasks to be completed"""
        for task in tasks:
            await self.progress.add_task(
                task["name"],
                context=task.get("context", {})
            )
            self._update_status(f"Added task: {task['name']}")
            
    def _update_status(self, message: str) -> None:
        """Update status via callback if set"""
        if self._status_callback:
            self._status_callback(message)
    
    async def process_task(self, task_name: str) -> None:
        """Process a single task with progress tracking"""
        try:
            context = await self.progress.get_task_context(task_name)
            if context:
                await self.progress.update_task_progress(
                    task_name,
                    0.0,
                    "Starting task...",
                    TaskStatus.IN_PROGRESS
                )
                await self._process_task_with_context(task_name, context)
            else:
                await self.progress.update_task_progress(
                    task_name,
                    0.0,
                    "No context found for task",
                    TaskStatus.FAILED
                )
                
        except Exception as e:
            await self.progress.update_task_progress(
                task_name,
                0.0,
                f"Task failed: {str(e)}",
                TaskStatus.FAILED
            )
            raise
    
    async def _process_task_with_context(self, task_name: str, context: Dict[str, Any]) -> None:
        """Process a task based on its context"""
        try:
            # Update task progress
            await self.progress.update_task_progress(
                task_name,
                50.0,
                "Processing task...",
                TaskStatus.IN_PROGRESS
            )
            
            # Handle different task types based on context
            task_type = context.get("type", "unknown")
            
            if task_type == "file_edit":
                await self.progress.save_checkpoint({
                    "file": context["file"],
                    "position": context.get("position", ""),
                    "changes": context.get("changes", {})
                })
            
            # Mark task as complete
            await self.progress.update_task_progress(
                task_name,
                100.0,
                "Task completed",
                TaskStatus.COMPLETED
            )
            
        except Exception as e:
            await self.progress.update_task_progress(
                task_name,
                0.0,
                f"Task processing failed: {str(e)}",
                TaskStatus.FAILED
            )
            raise
    
    async def resume_from_checkpoint(self) -> Dict[str, Any]:
        """Resume tasks from last checkpoint"""
        return await self.progress.load_progress()
    
    async def save_edit_checkpoint(self, file_path: str, position: str, 
                                 pending_changes: Optional[Dict[str, Any]] = None) -> None:
        """Save a checkpoint for file editing progress"""
        await self.progress.save_checkpoint({
            'file': file_path,
            'position': position,
            'pending_changes': pending_changes or {}
        })
    
    async def mark_task_complete(self, task_name: str) -> None:
        """Mark a task as complete"""
        await self.progress.update_task_progress(
            task_name,
            100.0,
            "Task completed",
            TaskStatus.COMPLETED
        )
    
    def get_remaining_tasks(self) -> List[str]:
        """Get list of remaining tasks"""
        return self.progress.get_pending_tasks()
    
    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get list of pending changes"""
        return self.progress.get_pending_changes()
    
    async def reset_progress(self) -> None:
        """Reset all progress"""
        await self.progress.reset()

    def create_example_task_sequence(self) -> None:
        """Create an example task sequence for demonstration"""
        example_tasks = [
            {
                "name": "setup_project",
                "context": {
                    "type": "setup",
                    "steps": ["create_dirs", "init_config"]
                }
            },
            {
                "name": "process_files",
                "context": {
                    "type": "file_edit",
                    "file": "example.py",
                    "changes": {"add_function": True}
                }
            }
        ]
        asyncio.create_task(self.start_task_sequence(example_tasks))