import os
import asyncio
from typing import List, Dict, Any, Optional, Callable
from .progress_tracker import AsyncProgressTracker, TaskProgress, TaskStatus
import logging
import traceback

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
            task_id = task.get('id', '') or task.get('name', f"task_{len(self.progress.tasks)}")
            await self.progress.add_task(task_id, task)
            self._update_status(f"Added task: {task_id}")
            
    def _update_status(self, message: str) -> None:
        """Update status via callback if set"""
        if self._status_callback:
            self._status_callback(message)
    
    async def process_task(self, task_name: str) -> None:
        """Process a single task with progress tracking"""
        try:
            self._update_status(f"Starting task: {task_name}")
            await self.progress.update_task_progress(
                task_name, 
                0.0, 
                "Task started", 
                TaskStatus.IN_PROGRESS
            )
            
            # Get task context
            context = await self.progress.get_task_context(task_name)
            if not context:
                raise ValueError(f"No context found for task: {task_name}")
            
            # Process task with context
            await self._process_task_with_context(task_name, context)
                
        except Exception as e:
            logging.error(f"Error processing task {task_name}: {e}")
            logging.debug(traceback.format_exc())
            await self.progress.update_task_progress(
                task_name,
                0.0,
                f"Error: {str(e)}",
                TaskStatus.FAILED
            )
            self._update_status(f"Task failed: {task_name} - {str(e)}")
    
    async def _process_task_with_context(self, task_name: str, context: Dict[str, Any]) -> None:
        """Process a task based on its context"""
        try:
            task_type = context.get('type', 'unknown')
            self._update_status(f"Processing {task_type} task: {task_name}")
            
            # Update progress
            await self.progress.update_task_progress(
                task_name,
                50.0,
                f"Executing {task_type} task",
                TaskStatus.IN_PROGRESS
            )
            
            # Handle different task types
            if task_type == 'file_edit':
                await self._handle_file_edit_task(task_name, context)
            elif task_type == 'conversion':
                await self._handle_conversion_task(task_name, context)
            elif task_type == 'download':
                await self._handle_download_task(task_name, context)
            else:
                # Generic task handling
                # Just mark as complete for now
                await self.progress.update_task_progress(
                    task_name,
                    100.0,
                    "Task completed",
                    TaskStatus.COMPLETED
                )
            
            self._update_status(f"Completed task: {task_name}")
            
        except Exception as e:
            logging.error(f"Error in task execution {task_name}: {e}")
            logging.debug(traceback.format_exc())
            await self.progress.update_task_progress(
                task_name,
                0.0,
                f"Execution error: {str(e)}",
                TaskStatus.FAILED
            )
            self._update_status(f"Task execution failed: {task_name}")
    
    async def _handle_file_edit_task(self, task_name: str, context: Dict[str, Any]) -> None:
        """Handle a file editing task"""
        file_path = context.get('file_path')
        if not file_path:
            raise ValueError("No file path specified for file edit task")
        
        # Here we would implement file editing functionality
        # For now, just simulate the task
        await asyncio.sleep(0.5)  # Simulate work
        
        await self.progress.update_task_progress(
            task_name,
            100.0,
            f"Edited file: {file_path}",
            TaskStatus.COMPLETED
        )
    
    async def _handle_conversion_task(self, task_name: str, context: Dict[str, Any]) -> None:
        """Handle an audio conversion task"""
        # Implementation would depend on your audio processor module
        file_path = context.get('file_path')
        if not file_path:
            raise ValueError("No file path specified for conversion task")
        
        # Simulate conversion work
        await asyncio.sleep(1.0)  # Simulate work
        
        await self.progress.update_task_progress(
            task_name,
            100.0,
            f"Converted file: {file_path}",
            TaskStatus.COMPLETED
        )
    
    async def _handle_download_task(self, task_name: str, context: Dict[str, Any]) -> None:
        """Handle a file download task"""
        url = context.get('url')
        if not url:
            raise ValueError("No URL specified for download task")
        
        # Simulate download work
        await asyncio.sleep(1.5)  # Simulate work
        
        await self.progress.update_task_progress(
            task_name,
            100.0,
            f"Downloaded from: {url}",
            TaskStatus.COMPLETED
        )
    
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
        # Create example tasks
        example_tasks = [
            {
                'id': 'download_model',
                'type': 'download',
                'name': 'Download Speech Recognition Model',
                'url': 'https://example.com/model',
                'target_path': 'Models/speech_model.bin'
            },
            {
                'id': 'convert_audio',
                'type': 'conversion',
                'name': 'Convert Sample Audio File',
                'file_path': 'Audio-Input/sample.mp3',
                'output_path': 'Audio-Output/sample.wav'
            },
            {
                'id': 'transcribe_audio',
                'type': 'conversion',
                'name': 'Transcribe Audio to Text',
                'file_path': 'Audio-Output/sample.wav',
                'output_path': 'Transcribes/sample.txt'
            }
        ]
        
        # Create task sequence
        asyncio.create_task(self.start_task_sequence(example_tasks))