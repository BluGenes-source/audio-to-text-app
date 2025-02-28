import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging
import threading
from datetime import datetime

class ConversionHandler:
    """Helper class to manage audio conversion functionality"""
    def __init__(self, config, audio_processor, terminal_callback, root):
        self.config = config
        self.audio_processor = audio_processor
        self.terminal_callback = terminal_callback
        self.root = root
        self.conversion_in_progress = False
        self.cancel_flag = False
        self.current_process = None
        self.current_audio_file = None
        self._pending_updates = []
        
    def setup_handlers(self, progress_frame, progress_bar):
        """Set up the progress UI elements"""
        self.progress_frame = progress_frame
        self.progress_bar = progress_bar
        self._check_updates()
    
    def _check_updates(self):
        """Process any pending GUI updates from background threads"""
        while self._pending_updates:
            callback = self._pending_updates.pop(0)
            try:
                callback()
            except Exception as e:
                logging.error(f"Error in GUI update: {e}")
        self.root.after(100, self._check_updates)

    def _queue_gui_update(self, callback):
        """Queue a GUI update to be processed in the main thread"""
        self._pending_updates.append(callback)
    
    def show_progress(self):
        """Show and start the progress bar"""
        self.progress_frame.grid()
        self.progress_bar.start(10)

    def hide_progress(self):
        """Hide and stop the progress bar"""
        self.progress_bar.stop()
        self.progress_frame.grid_remove()

    def start_conversion(self, file_path, on_complete, on_error, queue_mode=False):
        """Start audio to text conversion"""
        if self.conversion_in_progress:
            return False

        if not self.audio_processor.ffmpeg_path:
            messagebox.showerror("Error", "FFmpeg is not properly configured. Please check the setup.")
            return False

        if file_path:
            try:
                if not os.path.exists(file_path):
                    messagebox.showerror("Error", f"File not found: {file_path}")
                    return False
                
                if os.path.getsize(file_path) == 0:
                    messagebox.showerror("Error", "Selected file is empty")
                    return False
                
                self.conversion_in_progress = True
                self.terminal_callback("Converting audio to text...")
                self.cancel_flag = False
                self.show_progress()

                # Store current file before starting thread
                self.current_audio_file = file_path
                
                # Create and start the conversion thread
                self.current_process = threading.Thread(
                    target=self._conversion_thread,
                    args=(file_path, on_complete, on_error),
                    daemon=True  # Make thread daemon so it exits when app closes
                )
                self.current_process.start()

                # Start a timer to check thread status
                self.root.after(100, lambda: self._check_conversion_thread(on_error))
                return True
                
            except Exception as e:
                logging.error(f"Error starting conversion: {e}", exc_info=True)
                messagebox.showerror("Error", f"Failed to start conversion: {str(e)}")
                self.hide_progress()
                self.conversion_in_progress = False
                return False
        
        return False

    def _check_conversion_thread(self, on_error):
        """Check the status of the conversion thread"""
        if self.current_process and self.current_process.is_alive():
            # Thread still running, check again in 100ms
            self.root.after(100, lambda: self._check_conversion_thread(on_error))
        else:
            # Thread finished or died
            if self.conversion_in_progress and not self.cancel_flag:
                # Something went wrong - thread died without completing
                self._queue_gui_update(lambda: on_error("Conversion process terminated unexpectedly"))

    def _conversion_thread(self, file_path, on_complete, on_error):
        """Thread for audio to text conversion"""
        try:
            def progress_callback(msg):
                self._queue_gui_update(lambda: self.terminal_callback(msg))
            
            text = self.audio_processor.convert_audio_to_text(file_path, progress_callback)
            
            if not self.cancel_flag and text:
                self._queue_gui_update(lambda: on_complete(text))
            elif self.cancel_flag:
                self._queue_gui_update(lambda: self.terminal_callback("Conversion cancelled"))
        except Exception as e:
            self._queue_gui_update(lambda: on_error(str(e)))

    def cancel_conversion(self):
        """Cancel ongoing conversion"""
        self.cancel_flag = True
        self.terminal_callback("Canceling...")
        
        # Wait for thread to finish but don't block GUI
        if self.current_process and self.current_process.is_alive():
            self.terminal_callback("Waiting for process to terminate...")
            self.root.after(100, self._check_cancel_complete)
        else:
            self.hide_progress()
            self.conversion_in_progress = False

    def _check_cancel_complete(self):
        """Check if the cancellation is complete"""
        if self.current_process and self.current_process.is_alive():
            # Still running, check again in 100ms
            self.root.after(100, self._check_cancel_complete)
        else:
            # Thread finished
            self.hide_progress()
            self.conversion_in_progress = False
            self.terminal_callback("Conversion cancelled")
            
    def log_conversion_error(self, file_path, error_msg, errors_log_path):
        """Log conversion error to file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(errors_log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {os.path.basename(file_path)}: {error_msg}\n")
        except Exception as e:
            self.terminal_callback(f"Failed to log error: {str(e)}")
            
    def reset(self):
        """Reset conversion state"""
        self.conversion_in_progress = False
        self.cancel_flag = False
        self.current_audio_file = None