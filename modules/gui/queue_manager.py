import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import asyncio
from typing import List, Dict, Any, Optional
from queue import PriorityQueue
from dataclasses import dataclass
from datetime import datetime

@dataclass
class QueueItem:
    priority: int
    timestamp: float
    file_path: str
    status: str = "pending"
    error: Optional[str] = None
    
    def __lt__(self, other):
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority < other.priority

class QueueManager:
    """Helper class to manage the audio queue functionality"""
    def __init__(self, parent, config, terminal_callback, audio_processor, root):
        self.parent = parent
        self.config = config
        self.terminal_callback = terminal_callback
        self.audio_processor = audio_processor
        self.root = root
        self._queue_lock = threading.Lock()
        self.queue_tree = None
        self.queue_items = []  # Initialize as empty list
        self.current_index = 0
        self.conversion_in_progress = False
        self.cancel_flag = False
        
        # Set up logging
        logging.info("Initializing QueueManager")
        
        # Set up logging with proper file handler
        self.logger = logging.getLogger('QueueManager')
        fh = logging.FileHandler('conversion_errors.log')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.INFO)
        
        # Set up theme-based styles for buttons
        self.style = ttk.Style()
        self.setup_theme_styles()

    def setup_theme_styles(self):
        """Set up theme-specific styles for queue buttons"""
        # Queue control button styles
        self.style.configure('Queue.Control.TButton',
                           padding=5,
                           relief="raised")
        
        # Process queue button styles
        self.style.configure('Queue.Process.TButton',
                           padding=5,
                           relief="raised")
        self.style.configure('Queue.Process.Inactive.TButton',
                           background='gray75')
        self.style.configure('Queue.Process.Ready.TButton',
                           background='green')
                           
        # Make sure styles have valid foreground/background colors for all states
        self.style.map('Queue.Control.TButton',
                    background=[('active', 'lightblue'),
                               ('disabled', 'gray75')],
                    foreground=[('disabled', 'gray50')])
            
        self.style.map('Queue.Process.TButton',
                    background=[('active', 'lightblue'),
                               ('disabled', 'gray75')],
                    foreground=[('disabled', 'gray50')])

    def setup_queue_ui(self, frame, process_next_callback, update_queue_button_state_callback):
        """Set up the queue UI elements"""
        self.frame = frame
        self.process_next_callback = process_next_callback
        self.update_queue_button_state = update_queue_button_state_callback
        
        # Queue controls frame
        controls_frame = ttk.Frame(self.frame)
        controls_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        # Left side controls
        left_controls = ttk.Frame(controls_frame)
        left_controls.grid(row=0, column=0, sticky="w")
        
        ttk.Button(left_controls, text="Remove Selected",
                  command=self.remove_from_queue,
                  style='Queue.Control.TButton').grid(row=0, column=0, padx=2)
        ttk.Button(left_controls, text="Clear Queue",
                  command=self.clear_queue,
                  style='Queue.Control.TButton').grid(row=0, column=1, padx=2)
        
        # Configure controls frame columns
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        
        # Queue listbox with status column
        self.queue_frame = ttk.Frame(self.frame)
        self.queue_frame.grid(row=1, column=0, sticky="nsew")
        
        # Create Treeview for queue items
        self.queue_tree = ttk.Treeview(self.queue_frame, 
                                     columns=("Status", "Filename"),
                                     show="headings",
                                     selectmode="browse")
        
        self.queue_tree.heading("Status", text="Status")
        self.queue_tree.heading("Filename", text="File")
        
        self.queue_tree.column("Status", width=100)
        self.queue_tree.column("Filename", width=300)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(self.queue_frame, orient="vertical", 
                                  command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=y_scrollbar.set)
        
        # Grid queue elements
        self.queue_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Process queue button
        self.process_queue_button = ttk.Button(
            self.frame, 
            text="Process Queue",
            command=self.process_queue,
            style='Queue.Process.Inactive.TButton',
            state=tk.DISABLED
        )
        self.process_queue_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        # Configure frame weights
        self.frame.columnconfigure(0, weight=1)
        self.queue_frame.columnconfigure(0, weight=1)
        self.queue_frame.rowconfigure(0, weight=1)
        
        return self.queue_tree, self.process_queue_button

    def add_file_to_queue(self, file_path: str) -> bool:
        """Add a file to the queue"""
        try:
            with self._queue_lock:
                if file_path in [item["path"] for item in self.queue_items]:
                    logging.warning(f"File already in queue: {file_path}")
                    messagebox.showwarning("Warning", "File already in queue")
                    return False

                self.queue_items.append({
                    "path": file_path,
                    "status": "Pending"
                })
                
                # Add to treeview
                self.queue_tree.insert("", "end", values=(
                    "Pending",
                    os.path.basename(file_path)
                ))
                
                logging.info(f"Added file to queue: {file_path}")
                self.update_queue_button_state()
                return True

        except Exception as e:
            logging.error(f"Error adding file to queue: {e}")
            return False

    def process_queue(self) -> None:
        """Start processing the queue"""
        if self.conversion_in_progress or not self.queue_items:
            return
            
        logging.info("Starting queue processing")
        self.conversion_in_progress = True
        self.cancel_flag = False
        self.current_index = 0
        
        # Create progress frame
        self.setup_progress_frame()
        
        # Start processing
        self.process_next_file()

    def setup_progress_frame(self):
        """Set up progress tracking UI"""
        if hasattr(self, 'queue_progress_frame'):
            self.queue_progress_frame.destroy()
            
        self.queue_progress_frame = ttk.Frame(self.frame)
        self.queue_progress_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5,0))
        
        self.queue_progress_bar = ttk.Progressbar(
            self.queue_progress_frame, 
            mode='determinate',
            maximum=len(self.queue_items)
        )
        self.queue_progress_bar.grid(row=0, column=0, sticky="ew")
        
        self.queue_cancel_button = ttk.Button(
            self.queue_progress_frame, 
            text="Cancel Queue",
            command=self.cancel_queue,
            style='Cancel.TButton'
        )
        self.queue_cancel_button.grid(row=0, column=1, padx=(5,0))
        
        self.queue_progress_frame.columnconfigure(0, weight=1)

    def process_next_file(self):
        """Process the next file in queue"""
        if self.cancel_flag or self.current_index >= len(self.queue_items):
            self.finish_queue_processing()
            return
            
        current_item = self.queue_items[self.current_index]
        file_path = current_item["path"]
        
        try:
            # Update status
            self._update_item_status(self.current_index, "Processing")
            self.terminal_callback(f"\nProcessing {self.current_index + 1}/{len(self.queue_items)}: {os.path.basename(file_path)}")
            
            # Update progress bar
            if hasattr(self, 'queue_progress_bar'):
                self.queue_progress_bar['value'] = self.current_index
            
            # Start conversion after delay
            self.root.after(int(self.config.queue_delay * 1000), 
                          lambda: self.start_file_conversion(file_path))
                
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            self._handle_conversion_error(file_path, str(e))

    def start_file_conversion(self, file_path):
        """Start conversion of a single file"""
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Start async conversion
            asyncio.run_coroutine_threadsafe(
                self.audio_processor.convert_audio_to_text_async(
                    file_path,
                    lambda msg: self.terminal_callback(f"{os.path.basename(file_path)}: {msg}")
                ),
                loop
            ).add_done_callback(lambda future: self.handle_conversion_result(future, file_path))
            
        except Exception as e:
            error_msg = f"Error starting conversion for {file_path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.terminal_callback(error_msg)
            self._handle_conversion_error(file_path, str(e))

    def handle_conversion_result(self, future, file_path):
        """Handle the result of a file conversion"""
        try:
            text = future.result()
            if text:
                self._update_item_status(self.current_index, "Complete")
                self.logger.info(f"Successfully converted {file_path}")
            else:
                error_msg = "Conversion failed - no text generated"
                self.logger.error(f"{error_msg} for {file_path}")
                raise Exception(error_msg)
                
        except Exception as e:
            error_msg = f"Conversion failed for {file_path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.terminal_callback(error_msg)
            self._handle_conversion_error(file_path, str(e))
            
        finally:
            # Move to next file
            self.current_index += 1
            self.root.after(100, self.process_next_file)

    def _handle_conversion_error(self, file_path, error_msg):
        """Handle conversion error for a file"""
        self._update_item_status(self.current_index, "Failed")
        error_log = f"Error converting {os.path.basename(file_path)}: {error_msg}"
        self.logger.error(error_log, exc_info=True)
        self.terminal_callback(error_log)
        
        # Move to next file
        self.current_index += 1
        self.root.after(100, self.process_next_file)

    def _update_item_status(self, index: int, status: str) -> None:
        """Update the status of a queue item"""
        try:
            if self.queue_items is None or index >= len(self.queue_items):
                return
            self.queue_items[index]["status"] = status
            if self.queue_tree and self.queue_tree.get_children():
                try:
                    item_id = self.queue_tree.get_children()[index]
                    self.queue_tree.set(item_id, "Status", status)
                except (IndexError, tk.TclError) as e:
                    logging.error(f"Error updating tree item: {e}")
        except Exception as e:
            logging.error(f"Error updating item status: {e}")

    def cancel_queue(self) -> None:
        """Cancel queue processing"""
        self.cancel_flag = True
        self.terminal_callback("Canceling queue processing...")
        logging.info("Queue processing cancelled by user")

    def finish_queue_processing(self) -> None:
        """Clean up after queue processing is complete"""
        if hasattr(self, 'queue_progress_frame'):
            self.queue_progress_frame.destroy()
            
        self.conversion_in_progress = False
        self.cancel_flag = False
        
        # Remove completed items
        self.clear_completed_items()
        
        # Update UI
        self.process_queue_button.configure(state=tk.NORMAL)
        self.terminal_callback("\nQueue processing complete")
        logging.info("Queue processing finished")

    def clear_completed_items(self) -> None:
        """Remove completed items from the queue"""
        with self._queue_lock:
            # Remove completed items from internal list
            self.queue_items = [
                item for item in self.queue_items 
                if item["status"] not in ["Complete", "Failed"]
            ]
            
            # Remove from tree view
            for item in self.queue_tree.get_children():
                if self.queue_tree.set(item, "Status") in ["Complete", "Failed"]:
                    self.queue_tree.delete(item)

    def remove_from_queue(self) -> None:
        """Remove selected item from queue"""
        with self._queue_lock:
            selection = self.queue_tree.selection()
            if not selection:
                return
                
            item = selection[0]
            index = self.queue_tree.index(item)
            
            # Remove from internal list and tree
            if index < len(self.queue_items):
                del self.queue_items[index]
            self.queue_tree.delete(item)
            
            self.update_queue_button_state()
            logging.info("Removed item from queue")

    def clear_queue(self) -> None:
        """Clear entire queue"""
        with self._queue_lock:
            if not self.queue_items:
                return
                
            if messagebox.askyesno("Confirm Clear", "Clear entire queue?"):
                self.queue_items.clear()
                self.queue_tree.delete(*self.queue_tree.get_children())
                self.update_queue_button_state()
                logging.info("Queue cleared")

    def get_queue_items(self) -> List[str]:
        """Get list of files in queue"""
        if self.queue_items is None:
            self.queue_items = []
        return [item["path"] for item in self.queue_items]