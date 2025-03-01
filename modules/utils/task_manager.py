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
            self.progress.add_task(
                task["name"],
                context=task.get("context", {})
            )
            await self.progress.start_task(task["name"])
            
    def _update_status(self, message: str) -> None:
        """Update status via callback if set"""
        if self._status_callback:
            self._status_callback(message)
    
    async def process_task(self, task_name: str) -> None:
        """Process a single task with progress tracking"""
        try:
            self._update_status(f"Starting task: {task_name}")
            await self.progress.start_task(task_name)
            
            # Get task context
            context = self.progress.get_task_context(task_name)
            if not context:
                raise ValueError(f"No context found for task: {task_name}")
            
            # Process the task
            await self._process_task_with_context(task_name, context)
            
            # Mark task as complete
            await self.progress.complete_task(task_name)
            self._update_status(f"Completed task: {task_name}")
            
        except Exception as e:
            await self.progress.fail_task(task_name, str(e))
            self._update_status(f"Failed task {task_name}: {str(e)}")
            raise
    
    async def _process_task_with_context(self, task_name: str, context: Dict[str, Any]) -> None:
        """Process a task based on its context"""
        # Update progress at key points
        await self.progress.update_task_progress(
            task_name, 25.0, "Processing...", TaskStatus.IN_PROGRESS
        )
        
        # Example task processing logic
        if 'file' in context:
            self.progress.set_last_edit_position(
                context['file'],
                "start_of_file"
            )
            
        await self.progress.update_task_progress(
            task_name, 50.0, "Applying changes...", TaskStatus.IN_PROGRESS
        )
        
        # Simulate task work
        await asyncio.sleep(0.1)
        
        await self.progress.update_task_progress(
            task_name, 75.0, "Finalizing...", TaskStatus.IN_PROGRESS
        )
    
    async def resume_from_checkpoint(self) -> Dict[str, Any]:
        """Get the information needed to resume work"""
        resume_point = self.progress.get_resume_point()
        
        # Check for any active tasks
        active_tasks = self.progress.get_active_tasks()
        if active_tasks:
            for task_id in active_tasks:
                progress = self.progress.get_task_progress(task_id)
                if progress:
                    self._update_status(
                        f"Resuming task {task_id} at {progress['progress']}%: {progress['message']}"
                    )
        
        return resume_point
    
    async def save_edit_checkpoint(self, file_path: str, position: str, 
                                 pending_changes: Optional[Dict[str, Any]] = None) -> None:
        """Save a checkpoint during file editing"""
        self.progress.set_last_edit_position(file_path, position)
        if pending_changes:
            self.progress.add_pending_change(pending_changes)
        await self.progress.save_state_async()
    
    async def mark_task_complete(self, task_name: str) -> None:
        """Mark a task as completed and save progress"""
        await self.progress.complete_task(task_name)
        self._update_status(f"Marked task as complete: {task_name}")
    
    def get_remaining_tasks(self) -> List[str]:
        """Get list of tasks that still need to be completed"""
        resume_point = self.progress.get_resume_point()
        return resume_point["remaining_tasks"]
    
    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get any pending changes that need to be applied"""
        resume_point = self.progress.get_resume_point()
        return resume_point["pending_changes"]
    
    async def reset_progress(self) -> None:
        """Reset all progress tracking"""
        self.progress.clear_state()
        await self.progress.cleanup()
        self._update_status("Progress tracking reset")

    def create_example_task_sequence(self) -> None:
        """Create an example task sequence for demonstration"""
        example_tasks = [
            {
                "name": "update_folder_structure",
                "context": {
                    "folders_to_create": ["Audio-Input", "Audio-Output"],
                    "files_to_move": {"old_path": "new_path"}
                }
            },
            {
                "name": "update_config_manager",
                "context": {
                    "file": "modules/config/config_manager.py",
                    "changes": ["Add new folder paths", "Update default settings"]
                }
            },
            {
                "name": "implement_error_handling",
                "context": {
                    "files": ["modules/audio/audio_processor.py"],
                    "error_types": ["FileNotFound", "PermissionError"]
                }
            }
        ]
        asyncio.create_task(self.start_task_sequence(example_tasks))