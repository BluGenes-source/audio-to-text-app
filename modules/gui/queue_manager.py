import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging
import threading

class QueueManager:
    """Helper class to manage the audio queue functionality"""
    def __init__(self, parent, config, terminal_callback, audio_processor, root):
        self.parent = parent
        self.config = config
        self.terminal_callback = terminal_callback
        self.audio_processor = audio_processor
        self.root = root
        self.audio_queue = []
        self.failed_files = []
        self.conversion_in_progress = False
        self.cancel_flag = False
        self.queue_progress_frame = None
        self.queue_progress_bar = None
        self._queue_lock = threading.Lock()
        
    def setup_queue_ui(self, frame, process_next_callback, update_queue_button_state_callback):
        """Set up the queue UI elements"""
        self.frame = frame
        self.process_next_callback = process_next_callback
        self.update_queue_button_state = update_queue_button_state_callback
        
        # Queue controls
        queue_controls = ttk.Frame(self.frame)
        queue_controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Button(queue_controls, text="Remove Selected",
                  command=self.remove_from_queue).grid(row=0, column=0, padx=2)
        ttk.Button(queue_controls, text="Clear Queue",
                  command=self.clear_queue).grid(row=0, column=1, padx=2)
        
        # Queue listbox
        self.queue_listbox = tk.Listbox(self.frame, height=15, selectmode=tk.SINGLE)
        self.queue_listbox.grid(row=1, column=0, sticky="nsew")
        
        # Queue scrollbar
        queue_scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.queue_listbox.yview)
        queue_scrollbar.grid(row=1, column=1, sticky="ns")
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)
        
        # Process queue button
        self.process_queue_button = ttk.Button(self.frame, text="Process Queue",
                  command=self.process_queue,
                  style='Action.Inactive.TButton',
                  state=tk.DISABLED)
        self.process_queue_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        return self.queue_listbox, self.process_queue_button

    def add_file_to_queue(self, file_path):
        """Add a file to the queue if it's not already there"""
        if file_path not in self.audio_queue:
            self.audio_queue.append(file_path)
            self.queue_listbox.insert(tk.END, os.path.basename(file_path))
            # Enable process queue button if we have files and not currently processing
            self.process_queue_button.configure(
                state=tk.NORMAL,
                style='Action.Ready.TButton',
                text=f"Process Queue ({len(self.audio_queue)} files)"
            )
            self.terminal_callback(f"Added to queue: {os.path.basename(file_path)}")
            return True
        else:
            self.terminal_callback(f"File already in queue: {os.path.basename(file_path)}")
            return False

    def remove_from_queue(self):
        """Remove selected file from queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No file selected in queue")
            return
            
        index = selection[0]
        self.audio_queue.pop(index)
        self.queue_listbox.delete(index)
        # Update button state after removing file
        if len(self.audio_queue) == 0:
            self.process_queue_button.configure(
                state=tk.DISABLED,
                style='Action.Inactive.TButton',
                text="Process Queue"
            )
        else:
            self.process_queue_button.configure(
                text=f"Process Queue ({len(self.audio_queue)} files)"
            )

    def clear_queue(self):
        """Clear entire queue"""
        if self.queue_listbox.size() > 0:
            if messagebox.askyesno("Confirm", "Clear entire queue?"):
                self.audio_queue.clear()
                self.queue_listbox.delete(0, tk.END)
                self.update_queue_button_state()

    def process_queue(self):
        """Process all files in the queue"""
        if not self.audio_queue:
            messagebox.showwarning("Warning", "Queue is empty")
            return
        
        if self.conversion_in_progress:
            messagebox.showwarning("Warning", "Conversion already in progress")
            return

        # Create and setup progress frame
        if hasattr(self, 'queue_progress_frame') and self.queue_progress_frame:
            self.queue_progress_frame.destroy()
            
        self.queue_progress_frame = ttk.Frame(self.frame)
        self.queue_progress_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5,0))
        self.queue_progress_bar = ttk.Progressbar(self.queue_progress_frame, mode='determinate')
        self.queue_progress_bar.grid(row=0, column=0, sticky="ew")
        self.queue_progress_frame.columnconfigure(0, weight=1)
        
        # Add cancel button
        self.queue_cancel_button = ttk.Button(self.queue_progress_frame, 
                                            text="Cancel Queue",
                                            command=self.cancel_queue,
                                            style='Cancel.TButton')
        self.queue_cancel_button.grid(row=0, column=1, padx=(5,0))
        
        # Set up progress tracking
        total_files = len(self.audio_queue)
        self.queue_progress_bar['maximum'] = total_files
        self.queue_progress_bar['value'] = 0
        
        # Disable queue controls while processing
        self.process_queue_button.configure(state=tk.DISABLED)
        self.conversion_in_progress = True
        self.cancel_flag = False
        
        # Start processing
        self.process_next_callback()

    def cancel_queue(self):
        """Cancel queue processing"""
        self.cancel_flag = True
        self.terminal_callback("Canceling queue processing...")

    def finish_queue_processing(self, errors_log_path):
        """Clean up after queue processing is complete"""
        if hasattr(self, 'queue_progress_frame') and self.queue_progress_frame:
            self.queue_progress_frame.destroy()
            self.queue_progress_frame = None
        
        self.conversion_in_progress = False
        self.cancel_flag = False
        
        # Report any failures
        if self.failed_files:
            failed_count = len(self.failed_files)
            self.terminal_callback(f"\nQueue processing completed with {failed_count} failures:")
            for file_path, error in self.failed_files:
                self.terminal_callback(f"- {os.path.basename(file_path)}")
            self.terminal_callback(f"\nDetailed error log saved to: {os.path.basename(errors_log_path)}")
            self.failed_files = []  # Reset for next queue
        else:
            self.terminal_callback("Queue processing completed successfully")
        
        self.update_queue_button_state()
        
    def get_next_file(self):
        """Get the next file from the queue"""
        if not self.audio_queue or self.cancel_flag:
            return None
        return self.audio_queue[0]
        
    def record_failure(self, file_path, error_msg):
        """Record a file conversion failure"""
        self.failed_files.append((file_path, error_msg))
        
    def advance_queue(self):
        """Advance the queue to the next item"""
        if self.audio_queue:
            if hasattr(self, 'queue_progress_bar') and self.queue_progress_bar:
                self.queue_progress_bar['value'] += 1
            self.audio_queue.pop(0)
            self.queue_listbox.delete(0)