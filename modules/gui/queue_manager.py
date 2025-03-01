import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging
import threading
from datetime import datetime

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
        
        # Process queue button - directly configure with normal state to ensure it's clickable
        # when queue has items
        self.process_queue_button = ttk.Button(
            self.frame, 
            text="Process Queue",
            command=self.process_queue,
            style='Action.Inactive.TButton',
            state=tk.DISABLED
        )
        self.process_queue_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        logging.info("Queue UI elements initialized")
        return self.queue_listbox, self.process_queue_button

    def add_file_to_queue(self, file_path):
        """Add a file to the queue if it's not already there"""
        print(f"DEBUG: Adding file to queue: {file_path}")
        logging.info(f"Adding file to queue: {os.path.basename(file_path)}")
        
        if file_path not in self.audio_queue:
            self.audio_queue.append(file_path)
            self.queue_listbox.insert(tk.END, os.path.basename(file_path))
            
            # Force update the button state immediately
            print(f"DEBUG: Queue has {len(self.audio_queue)} files, updating button state")
            self.process_queue_button.configure(
                state=tk.NORMAL,
                style='Action.Ready.TButton',
                text=f"Process Queue ({len(self.audio_queue)} files)"
            )
            
            # Also call the update method for completeness
            self.update_queue_button_state()
            
            self.terminal_callback(f"Added to queue: {os.path.basename(file_path)}")
            print(f"DEBUG: File added to queue successfully")
            return True
        else:
            self.terminal_callback(f"File already in queue: {os.path.basename(file_path)}")
            print(f"DEBUG: File already in queue")
            return False

    def update_queue_button_state(self):
        """Update the process queue button state based on queue contents"""
        try:
            if len(self.audio_queue) > 0 and not self.conversion_in_progress:
                print(f"DEBUG: Enabling Process Queue button with {len(self.audio_queue)} files")
                logging.info(f"Enabling Process Queue button with {len(self.audio_queue)} files")
                
                # Explicitly set state to NORMAL to ensure it's clickable
                self.process_queue_button['state'] = tk.NORMAL
                self.process_queue_button.configure(
                    style='Action.Ready.TButton',
                    text=f"Process Queue ({len(self.audio_queue)} files)"
                )
                
                # Force update the UI
                self.root.update_idletasks()
            else:
                print(f"DEBUG: Disabling Process Queue button (queue empty or conversion in progress)")
                logging.info("Process Queue button disabled")
                self.process_queue_button.configure(
                    state=tk.DISABLED,
                    style='Action.Inactive.TButton',
                    text="Process Queue"
                )
        except Exception as e:
            error_msg = f"Error updating queue button: {e}"
            logging.error(error_msg, exc_info=True)
            print(f"DEBUG: {error_msg}")

    def remove_from_queue(self):
        """Remove selected file from queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No file selected in queue")
            return
            
        index = selection[0]
        file_path = self.audio_queue[index]
        print(f"DEBUG: Removing file from queue: {os.path.basename(file_path)}")
        logging.info(f"Removing file from queue: {os.path.basename(file_path)}")
        
        self.audio_queue.pop(index)
        self.queue_listbox.delete(index)
        
        # Update button state after removing file
        print(f"DEBUG: After removal, queue has {len(self.audio_queue)} files")
        if len(self.audio_queue) == 0:
            self.process_queue_button.configure(
                state=tk.DISABLED,
                style='Action.Inactive.TButton',
                text="Process Queue"
            )
            print(f"DEBUG: Process Queue button disabled (queue empty)")
        else:
            self.process_queue_button.configure(
                text=f"Process Queue ({len(self.audio_queue)} files)"
            )
            print(f"DEBUG: Process Queue button updated with file count")

    def clear_queue(self):
        """Clear entire queue"""
        if self.queue_listbox.size() > 0:
            if messagebox.askyesno("Confirm", "Clear entire queue?"):
                print(f"DEBUG: Clearing queue with {len(self.audio_queue)} files")
                logging.info(f"Clearing queue with {len(self.audio_queue)} files")
                
                self.audio_queue.clear()
                self.queue_listbox.delete(0, tk.END)
                self.update_queue_button_state()
                
                print(f"DEBUG: Queue cleared, button state updated")

    def process_queue(self):
        """Process all files in the queue"""
        print(f"DEBUG: process_queue called at {datetime.now().strftime('%H:%M:%S.%f')}")
        logging.info("Process Queue button clicked")
        
        if not self.audio_queue:
            print("DEBUG: Cannot process queue - queue is empty")
            messagebox.showwarning("Warning", "Queue is empty")
            return
        
        if self.conversion_in_progress:
            print("DEBUG: Cannot process queue - conversion already in progress")
            messagebox.showwarning("Warning", "Conversion already in progress")
            return

        print(f"DEBUG: Starting queue processing with {len(self.audio_queue)} files")
        logging.info(f"Starting queue processing with {len(self.audio_queue)} files")
        
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
        self.conversion_in_progress = True
        self.process_queue_button.configure(state=tk.DISABLED)
        self.cancel_flag = False
        
        # Update status message
        self.terminal_callback(f"Starting to process {len(self.audio_queue)} files in queue...")
        
        print(f"DEBUG: Queue setup complete, calling process_next_callback at {datetime.now().strftime('%H:%M:%S.%f')}")
        try:
            # Start processing the first file
            if self.process_next_callback:
                print("DEBUG: process_next_callback is not None, calling it")
                self.process_next_callback()
            else:
                print("ERROR: process_next_callback is None!")
                self.terminal_callback("Error: Process callback not configured properly")
        except Exception as e:
            print(f"ERROR: Exception calling process_next_callback: {e}")
            import traceback
            print(traceback.format_exc())
            self.terminal_callback(f"Error starting queue processing: {str(e)}")

    def cancel_queue(self):
        """Cancel queue processing"""
        print("DEBUG: Canceling queue processing")
        logging.info("Queue processing canceled by user")
        self.cancel_flag = True
        self.terminal_callback("Canceling queue processing...")

    def finish_queue_processing(self, errors_log_path):
        """Clean up after queue processing is complete"""
        print("DEBUG: Finishing queue processing")
        logging.info("Queue processing completed")
        
        if hasattr(self, 'queue_progress_frame') and self.queue_progress_frame:
            self.queue_progress_frame.destroy()
            self.queue_progress_frame = None
        
        self.conversion_in_progress = False
        self.cancel_flag = False
        
        # Report any failures
        if self.failed_files:
            failed_count = len(self.failed_files)
            print(f"DEBUG: Queue completed with {failed_count} failures")
            logging.warning(f"Queue completed with {failed_count} failures")
            
            self.terminal_callback(f"\nQueue processing completed with {failed_count} failures:")
            for file_path, error in self.failed_files:
                self.terminal_callback(f"- {os.path.basename(file_path)}")
            self.terminal_callback(f"\nDetailed error log saved to: {os.path.basename(errors_log_path)}")
            self.failed_files = []  # Reset for next queue
        else:
            print("DEBUG: Queue processing completed successfully")
            logging.info("Queue processing completed successfully")
            self.terminal_callback("Queue processing completed successfully")
        
        self.update_queue_button_state()
        
    def get_next_file(self):
        """Get the next file from the queue"""
        if not self.audio_queue or self.cancel_flag:
            print("DEBUG: No more files to process or processing canceled")
            return None
            
        next_file = self.audio_queue[0]
        print(f"DEBUG: Next file to process: {os.path.basename(next_file)}")
        return next_file
        
    def record_failure(self, file_path, error_msg):
        """Record a file conversion failure"""
        print(f"DEBUG: Recording failure for file: {os.path.basename(file_path)}")
        logging.error(f"File conversion failed: {os.path.basename(file_path)} - {error_msg}")
        self.failed_files.append((file_path, error_msg))
        
    def advance_queue(self):
        """Advance the queue to the next item"""
        if self.audio_queue:
            file_processed = self.audio_queue[0]
            print(f"DEBUG: Advancing queue after processing: {os.path.basename(file_processed)}")
            logging.info(f"Processed file: {os.path.basename(file_processed)}")
            
            if hasattr(self, 'queue_progress_bar') and self.queue_progress_bar:
                current_value = self.queue_progress_bar['value'] 
                self.queue_progress_bar['value'] = current_value + 1
                print(f"DEBUG: Progress updated: {current_value + 1}/{self.queue_progress_bar['maximum']}")
                
            self.audio_queue.pop(0)
            self.queue_listbox.delete(0)
            
            print(f"DEBUG: Queue advanced, {len(self.audio_queue)} files remaining")