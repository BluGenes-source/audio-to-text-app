import os
from modules.utils.task_manager import TaskManager

def main():
    # Initialize the task manager with the workspace root
    workspace_root = os.path.dirname(os.path.abspath(__file__))
    task_manager = TaskManager(workspace_root)
    
    # Check if there are any pending tasks from a previous session
    resume_point = task_manager.resume_from_checkpoint()
    
    if resume_point["remaining_tasks"]:
        print("Resuming from previous session...")
        print(f"Current task: {resume_point['current_task']}")
        print(f"Last edited file: {resume_point['last_file']}")
        print(f"Last edit position: {resume_point['last_position']}")
        print(f"Pending changes: {len(resume_point['pending_changes'])}")
    else:
        print("Starting new task sequence...")
        # Create example tasks for demonstration
        task_manager.create_example_task_sequence()
    
    # Example of working with tasks
    remaining_tasks = task_manager.get_remaining_tasks()
    for task in remaining_tasks:
        print(f"\nProcessing task: {task}")
        
        # Get task-specific context
        context = task_manager.progress.get_task_context(task)
        if context:
            print(f"Task context: {context}")
        
        # Example: Save a checkpoint during file editing
        if "file" in context:
            task_manager.save_edit_checkpoint(
                context["file"],
                "function_name:line_number",
                {"type": "modification", "details": "Added new function"}
            )
        
        # Mark task as complete
        task_manager.mark_task_complete(task)
        print(f"Completed task: {task}")
    
    print("\nAll tasks completed!")

if __name__ == "__main__":
    main()