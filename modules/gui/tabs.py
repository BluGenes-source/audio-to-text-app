import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES
import os
import logging
import threading
from datetime import datetime
from .styles import ThemeColors
from .queue_manager import QueueManager
from .conversion_handler import ConversionHandler
from .audio_player import AudioPlayer

class SpeechToTextTab:
    def __init__(self, parent, config, audio_processor, terminal_callback, root):
        self.parent = parent
        self.config = config
        self.audio_processor = audio_processor
        self.terminal_callback = terminal_callback
        self.root = root
        self.cancel_flag = False
        self.current_process = None
        self.tts_tab = None  # Will be set by main app
        self.current_audio_file = None  # Store the selected audio file path
        self.current_filename_var = tk.StringVar(value="-Empty-")  # Add filename variable
        self.conversion_in_progress = False
        self.failed_files = []  # Store failed conversion files
        self.errors_log_path = os.path.join(config.app_dir, "conversion_errors.log")
        self.current_font_size = 10  # Add default font size tracking
        self.error_log_window = None  # Track error log window
        self._queue_lock = threading.Lock()
        self._pending_updates = []
        
        # Create the queue_manager first and store a direct reference to its audio_queue
        self.queue_manager = QueueManager(parent, config, terminal_callback, audio_processor, root)
        
        # CRITICAL FIX: Use queue_manager's audio_queue directly instead of our own
        # This ensures both classes operate on exactly the same list object
        self.audio_queue = self.queue_manager.audio_queue
        
        # Initialize other helpers
        self.conversion_handler = ConversionHandler(config, audio_processor, terminal_callback, root)
        self.audio_player = AudioPlayer(audio_processor, terminal_callback, root)
        
        self.setup_tab()
        # Start update checker after UI is fully setup
        self.root.after(100, self._check_updates)

    def setup_tab(self):
        # Split main frame into left and right sections
        left_frame = ttk.Frame(self.parent, padding="10")
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        right_frame = ttk.Frame(self.parent, padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Configure column weights
        self.parent.columnconfigure(0, weight=3)  # Left side gets more space
        self.parent.columnconfigure(1, weight=1)  # Right side gets less space

        # Main container with padding
        main_frame = left_frame

        # Folder settings frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Settings", 
                                    style="Group.TLabelframe", padding="10")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Create two groups within folder frame
        input_group = ttk.Frame(folder_frame)
        input_group.grid(row=0, column=0, padx=5)
        output_group = ttk.Frame(folder_frame)
        output_group.grid(row=0, column=1, padx=5)

        # Input group
        ttk.Label(input_group, text="Input Options:", 
                 style="Subtitle.TLabel").grid(row=0, column=0, pady=(0, 5))
        ttk.Button(input_group, text="Select Input Folder", 
                  command=self.select_input_folder).grid(row=1, column=0)
        ttk.Button(input_group, text="Load File from Input", 
                  command=self.load_from_input_folder).grid(row=2, column=0, pady=5)

        # Output group
        ttk.Label(output_group, text="Output Options:", 
                 style="Subtitle.TLabel").grid(row=0, column=0, pady=(0, 5))
        ttk.Button(output_group, text="Select Output Folder", 
                  command=self.select_output_folder).grid(row=1, column=0)

        # Conversion controls and file info frame
        conversion_frame = ttk.Frame(main_frame)
        conversion_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        conversion_frame.columnconfigure(0, weight=1)
        conversion_frame.columnconfigure(4, weight=1)

        # File info label
        ttk.Label(conversion_frame, text="Current File:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        ttk.Label(conversion_frame, textvariable=self.current_filename_var).grid(row=0, column=1, sticky='w')
        
        # Clear file button
        ttk.Button(conversion_frame, text="Clear File", 
                  command=self.clear_selected_file).grid(row=0, column=2, padx=5)

        # Start conversion button - rename and disable initially
        self.start_button = ttk.Button(conversion_frame, text="Load File", 
                                     command=self.load_single_file,
                                     style='Action.Inactive.TButton',
                                     state=tk.NORMAL)  # Changed to NORMAL since it's a load button
        self.start_button.grid(row=0, column=3, padx=10)
        
        # Remove hover bindings since this is now just a load button

        self.cancel_button = ttk.Button(conversion_frame, text="Cancel", 
                                      command=self.cancel_conversion,
                                      style='Cancel.TButton',
                                      state=tk.DISABLED)
        self.cancel_button.grid(row=0, column=4, padx=10)

        # Progress bar frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        progress_frame.grid_propagate(False)
        progress_frame.configure(height=25)
        progress_frame.grid_remove()
        self.progress_frame = progress_frame

        # Terminal output area - Moved up
        terminal_frame = ttk.LabelFrame(main_frame, text="Process Output", 
                                      style="Group.TLabelframe", padding="10")
        terminal_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # Apply theme colors to text area
        is_dark = self.config.theme == "dark"
        theme = ThemeColors(is_dark)

        self.terminal_area = scrolledtext.ScrolledText(terminal_frame, height=6, wrap=tk.WORD,
                                                     font=('Helvetica', 10))
        self.terminal_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.terminal_area.configure(
            background=theme.input_bg,
            foreground=theme.input_fg,
            insertbackground=theme.input_fg,
            selectbackground=theme.selection_bg,
            selectforeground=theme.selection_fg,
            state='disabled'
        )

        # Text display area with drop zone functionality - Moved down
        text_frame = ttk.LabelFrame(main_frame, text="Transcribed Text", 
                                  style="Group.TLabelframe", padding="10")
        text_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # Add control buttons to text frame
        button_frame = ttk.Frame(text_frame)
        button_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.E), pady=(0, 5))

        clear_text_btn = ttk.Button(button_frame, text="Clear Text",
                                  command=self.clear_text)
        clear_text_btn.grid(row=0, column=0, padx=5)

        self.save_text_button = ttk.Button(button_frame, text="Save Text", 
                                         command=self.save_transcribed_text,
                                         state=tk.DISABLED)
        self.save_text_button.grid(row=0, column=1, padx=5)

        self.send_to_tts_button = ttk.Button(button_frame, text="Send to TTS", 
                                           command=self.send_to_tts,
                                           state=tk.DISABLED)
        self.send_to_tts_button.grid(row=0, column=2, padx=5)

        # Debug load button
        debug_load_btn = ttk.Button(button_frame, text="[Debug] Load Text",
                                  command=self.debug_load_text)
        debug_load_btn.grid(row=0, column=3, padx=5)

        # Add view error log button next to clear text button in button_frame
        self.view_errors_btn = ttk.Button(button_frame, text="View Error Log",
                                      command=self.show_error_log)
        self.view_errors_btn.grid(row=0, column=4, padx=5)

        # Add drag-drop instruction label
        drop_label = ttk.Label(text_frame, text="Drop audio file here or use the input options above",
                             font=('Helvetica', 9, 'italic'))
        drop_label.grid(row=1, column=0, pady=(0, 5), sticky='w')  # Changed to row 1

        # Make text area 25% smaller by reducing height from 15 to 11
        self.text_area = scrolledtext.ScrolledText(text_frame, height=12, wrap=tk.WORD,
                                                 font=('Helvetica', self.current_font_size))
        self.text_area.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.text_area.configure(
            background=theme.input_bg,
            foreground=theme.input_fg,
            insertbackground=theme.input_fg,
            selectbackground=theme.selection_bg,
            selectforeground=theme.selection_fg
        )
        self.text_area.drop_target_register(DND_FILES)
        self.text_area.dnd_bind('<<Drop>>', self.handle_drop)
        self.text_area.bind('<Control-MouseWheel>', self.handle_font_size_change)  # Windows
        self.text_area.bind('<Control-Button-4>', self.handle_font_size_change)    # Linux up
        self.text_area.bind('<Control-Button-5>', self.handle_font_size_change)    # Linux down
        
        # Bind text change event to update button states
        self.text_area.bind('<<Modified>>', self.check_text_content)

        # Add play/stop audio controls
        audio_control_frame = ttk.Frame(text_frame)
        audio_control_frame.grid(row=3, column=0, sticky=(tk.E), pady=5)

        self.play_button = ttk.Button(audio_control_frame, text="▶ Play Audio", 
                                    command=self.play_audio,
                                    style='Audio.Play.TButton',
                                    state=tk.DISABLED)
        self.play_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(audio_control_frame, text="⏹ Stop", 
                                    command=self.stop_audio,
                                    style='Audio.Stop.TButton',
                                    state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)

        # Configure grid weights
        self.parent.columnconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)
        terminal_frame.columnconfigure(0, weight=1)
        terminal_frame.rowconfigure(0, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(3, weight=1)

        # Queue frame in right section
        self.queue_frame = ttk.LabelFrame(right_frame, text="Audio Queue", 
                                   style="Group.TLabelframe", padding="10")
        self.queue_frame.grid(row=0, column=0, sticky="nsew")
        
        # Setup queue UI elements with the queue manager
        self.queue_listbox, self.process_queue_button = self.queue_manager.setup_queue_ui(
            self.queue_frame,
            self.process_next_in_queue,
            self.update_queue_button_state
        )
        
        # Setup conversion handler with progress elements
        self.conversion_handler.setup_handlers(self.progress_frame, self.progress_bar)
        
        # Setup audio player with control buttons
        self.audio_player.setup_playback_controls(self.play_button, self.stop_button)
        
        # Configure weights for queue frame
        self.queue_frame.columnconfigure(0, weight=1)
        self.queue_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

    def show_progress(self):
        """Show and start the progress bar"""
        self.progress_frame.grid()
        self.progress_bar.start(10)

    def hide_progress(self):
        """Hide and stop the progress bar"""
        self.progress_bar.stop()
        self.progress_frame.grid_remove()

    def send_to_tts(self):
        """Send transcribed text to Text-to-Speech tab"""
        if self.tts_tab:
            text = self.text_area.get(1.0, tk.END).strip()
            if text:
                self.tts_tab.set_text(text)
                self.terminal_callback("Text sent to Text-to-Speech tab")
                self.send_to_tts_button.configure(style='Action.Success.TButton')  # Show success state
            else:
                messagebox.showwarning("Warning", "No text to send")
                self.send_to_tts_button.configure(state=tk.DISABLED)
        else:
            messagebox.showerror("Error", "Text-to-Speech tab not available")

    def _save_text_to_file(self, text):
        os.makedirs(self.config.transcribes_folder, exist_ok=True)
        base_name = "transcription"
        output_file = self.get_next_filename(base_name)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        
        logging.info(f"Saved transcription to: {output_file}")
        self.update_status(f"Saved: {os.path.basename(output_file)}")

    def save_transcribed_text(self):
        text = self.text_area.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "No text to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            initialdir=self.config.transcribes_folder,
            title="Save Transcription As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.update_status(f"Saved text to: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save text: {str(e)}")

    def get_next_filename(self, base_name):
        counter = 1
        base_path = os.path.join(self.config.transcribes_folder, base_name)
        while True:
            if counter == 1:
                filename = f"{base_path}.txt"
            else:
                filename = f"{base_path}_{counter}.txt"
            
            if not os.path.exists(filename):
                return filename
            counter += 1

    def update_status(self, message):
        """Update the application status"""
        # This should be implemented by the main application and passed as a callback
        pass

    def handle_drop(self, event):
        """Handle dropped audio files"""
        if self.conversion_in_progress:
            self.terminal_callback("Conversion in progress. Please wait.")
            return

        file_path = event.data
        if file_path:
            file_path = file_path.strip('{}')
            if file_path.lower().endswith(('.wav', '.mp3', '.flac')):
                try:
                    # Validate audio length
                    self.audio_processor.check_audio_length(file_path)
                    # Add file to queue
                    if file_path not in self.audio_queue:
                        self.audio_queue.append(file_path)
                        self.queue_listbox.insert(tk.END, os.path.basename(file_path))
                        self.update_queue_button_state()
                        self.terminal_callback(f"Added to queue: {os.path.basename(file_path)}")
                except ValueError as e:
                    self.terminal_callback(f"Error: {str(e)}")
                except Exception as e:
                    self.terminal_callback(f"Error checking file: {str(e)}")
            else:
                self.terminal_callback("Error: Please drop an audio file (WAV, MP3, or FLAC)")

    def select_input_folder(self):
        """Select input folder for audio files"""
        initial_dir = self.config.input_folder if self.config.input_folder and os.path.exists(self.config.input_folder) else os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Select Input Folder", initialdir=initial_dir)
        if folder:
            self.config.input_folder = folder
            self.terminal_callback(f"Input folder set: {os.path.basename(folder)}")

    def select_output_folder(self):
        """Select output folder for transcribed files"""
        initial_dir = self.config.output_folder if self.config.output_folder and os.path.exists(self.config.output_folder) else os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Select Output Folder", initialdir=initial_dir)
        if folder:
            self.config.output_folder = folder
            self.terminal_callback(f"Output folder set: {os.path.basename(folder)}")

    def load_from_input_folder(self):
        """Load audio file(s) from input folder"""
        if not self.config.input_folder:
            messagebox.showwarning("Warning", "Please select an input folder first")
            return
        
        files = filedialog.askopenfilenames(
            initialdir=self.config.input_folder,
            title="Select Audio File(s)",
            filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
        )
        
        if files:
            added_count = 0
            rejected_files = []
            
            for file_path in files:
                try:
                    # Validate audio length
                    self.audio_processor.check_audio_length(file_path)
                    
                    if file_path not in self.audio_queue:
                        self.audio_queue.append(file_path)
                        self.queue_listbox.insert(tk.END, os.path.basename(file_path))
                        added_count += 1
                except ValueError as e:
                    # Length validation failed
                    rejected_files.append((os.path.basename(file_path), str(e)))
                except Exception as e:
                    rejected_files.append((os.path.basename(file_path), f"Error checking file: {str(e)}"))
            
            # Update UI with results
            if added_count > 0:
                self.update_queue_button_state()
                self.terminal_callback(f"Added {added_count} file(s) to queue")
            
            # Report any rejected files
            if rejected_files:
                self.terminal_callback("\nThe following files were rejected:")
                for filename, reason in rejected_files:
                    self.terminal_callback(f"- {filename}: {reason}")

    def update_queue_button_state(self):
        """Update the process queue button state based on queue contents"""
        try:
            if self.audio_queue and not self.conversion_in_progress:
                self.process_queue_button.configure(
                    state=tk.NORMAL,
                    style='Action.Ready.TButton',
                    text=f"Process Queue ({len(self.audio_queue)} files)"
                )
            else:
                self.process_queue_button.configure(
                    state=tk.DISABLED,
                    style='Action.Inactive.TButton',
                    text="Process Queue"
                )
        except Exception as e:
            logging.error(f"Error updating queue button: {e}", exc_info=True)

    def start_conversion(self, file_path=None, queue_mode=False):
        """Start audio to text conversion"""
        print(f"DEBUG: start_conversion called at {datetime.now().strftime('%H:%M:%S.%f')} with file_path={file_path}, queue_mode={queue_mode}")
        
        if self.conversion_in_progress:
            print("DEBUG: Conversion already in progress, returning False")
            return False

        if not self.audio_processor.ffmpeg_path:
            print("DEBUG: FFmpeg not configured")
            messagebox.showerror("Error", "FFmpeg is not properly configured. Please check the setup.")
            return False

        # Use provided file_path or the stored current_audio_file
        file_path = file_path or self.current_audio_file
        
        print(f"DEBUG: Using file_path: {file_path}")

        if file_path:
            try:
                if not os.path.exists(file_path):
                    print(f"DEBUG: File not found: {file_path}")
                    messagebox.showerror("Error", f"File not found: {file_path}")
                    if queue_mode:
                        print("DEBUG: Queue mode, proceeding to next file")
                        self.process_next_in_queue()
                    return False
                
                if os.path.getsize(file_path) == 0:
                    print(f"DEBUG: File is empty: {file_path}")
                    messagebox.showerror("Error", "Selected file is empty")
                    if queue_mode:
                        print("DEBUG: Queue mode, proceeding to next file")
                        self.process_next_in_queue()
                    return False
                
                print(f"DEBUG: Setting conversion_in_progress to True")
                self.conversion_in_progress = True
                self.disable_controls()
                self.start_button.state(['disabled'])
                self.cancel_button.state(['!disabled'])
                self.terminal_callback(f"Converting audio to text: {os.path.basename(file_path)}")
                self.cancel_flag = False
                self.show_progress()

                # Store current file before starting thread
                self.current_audio_file = file_path
                
                print(f"DEBUG: Starting conversion thread for {os.path.basename(file_path)}")
                # Create and start the conversion thread
                self.current_process = threading.Thread(
                    target=self._conversion_thread,
                    args=(file_path,),
                    daemon=True  # Make thread daemon so it exits when app closes
                )
                self.current_process.start()

                # Start a timer to check thread status
                self.root.after(100, self._check_conversion_thread)
                return True
                
            except Exception as e:
                print(f"DEBUG: Error in start_conversion: {e}")
                import traceback
                print(traceback.format_exc())
                logging.error(f"Error starting conversion: {e}", exc_info=True)
                messagebox.showerror("Error", f"Failed to start conversion: {str(e)}")
                self._reset_buttons()
                self.hide_progress()
                self.conversion_in_progress = False
                if queue_mode:
                    print("DEBUG: Queue mode, proceeding to next file after error")
                    self.process_next_in_queue()
                return False
        else:
            print("DEBUG: No file path provided")
            return False

    def _check_conversion_thread(self):
        """Check the status of the conversion thread"""
        if self.current_process and self.current_process.is_alive():
            # Thread still running, check again in 100ms
            self.root.after(100, self._check_conversion_thread)
        else:
            # Thread finished or died
            if self.conversion_in_progress and not self.cancel_flag:
                # Something went wrong - thread died without completing
                self._conversion_error("Conversion process terminated unexpectedly")

    def _conversion_thread(self, file_path):
        """Thread for audio to text conversion"""
        try:
            def progress_callback(msg):
                self._queue_gui_update(lambda: self.terminal_callback(msg))
            
            text = self.audio_processor.convert_audio_to_text(file_path, progress_callback)
            
            if not self.cancel_flag and text:
                self._queue_gui_update(lambda: self._conversion_complete(text))
            elif self.cancel_flag:
                self._queue_gui_update(lambda: self.terminal_callback("Conversion cancelled"))
        except Exception as e:
            self._queue_gui_update(lambda: self._conversion_error(str(e)))

    def cancel_conversion(self):
        """Cancel ongoing conversion"""
        self.cancel_flag = True
        self.terminal_callback("Canceling...")
        
        # Wait for thread to finish but don't block GUI
        if self.current_process and self.current_process.is_alive():
            self.terminal_callback("Waiting for process to terminate...")
            self.root.after(100, self._check_cancel_complete)
        else:
            self._reset_buttons()
            self.hide_progress()

    def _check_cancel_complete(self):
        """Check if the cancellation is complete"""
        if self.current_process and self.current_process.is_alive():
            # Still running, check again in 100ms
            self.root.after(100, self._check_cancel_complete)
        else:
            # Thread finished
            self._reset_buttons()
            self.hide_progress()
            self.conversion_in_progress = False
            self.terminal_callback("Conversion cancelled")

    def _conversion_complete(self, text):
        """Handle conversion completion"""
        if text:
            # Generate output filename based on audio filename
            base_name = os.path.splitext(os.path.basename(self.current_audio_file))[0]
            transcription_file = os.path.join(self.config.transcribes_folder, f"{base_name}.txt")
            
            # Save transcription
            try:
                with open(transcription_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.terminal_callback(f"Saved transcription to: {os.path.basename(transcription_file)}")
            except Exception as e:
                error_msg = f"Error saving transcription: {str(e)}"
                if self.audio_queue and self.current_audio_file == self.audio_queue[0]:
                    self.failed_files.append((self.current_audio_file, error_msg))
                    self._log_conversion_error(self.current_audio_file, error_msg)
                else:
                    messagebox.showerror("Error", error_msg)
            
            # Update text area
            self.text_area.insert(tk.END, f"\n\n[{os.path.basename(self.current_audio_file)}]\n")
            self.text_area.insert(tk.END, text)
            self.text_area.see(tk.END)  # Scroll to show the new text
            
            # Update UI based on mode
            if self.audio_queue and self.current_audio_file == self.audio_queue[0]:
                self.queue_progress_bar['value'] += 1
                self.audio_queue.pop(0)
                self.queue_listbox.delete(0)
                self.root.after(self.config.queue_delay * 1000, self.process_next_in_queue)
            else:
                self.terminal_callback("Single file conversion completed successfully")
                self._reset_buttons()
                self.save_text_button.configure(state=tk.NORMAL)
                self.send_to_tts_button.configure(state=tk.NORMAL)
                self.play_button.configure(state=tk.NORMAL)
        
        self.hide_progress()
        self.start_button.configure(style='Action.Ready.TButton')  # Reset to ready style
        self.current_filename_var.set("-Empty-")
        self.current_audio_file = None
        self.conversion_in_progress = False

    def _conversion_error(self, error_msg):
        """Handle conversion error"""
        if self.audio_queue and self.current_audio_file == self.audio_queue[0]:
            # In queue mode, log error and continue
            self.failed_files.append((self.current_audio_file, error_msg))
            self._log_conversion_error(self.current_audio_file, error_msg)
            self.terminal_callback(f"Failed to convert: {os.path.basename(self.current_audio_file)}")
            self.queue_progress_bar['value'] += 1
            self.audio_queue.pop(0)
            self.queue_listbox.delete(0)
            self.conversion_in_progress = False
            self.root.after(self.config.queue_delay * 1000, self.process_next_in_queue)
        else:
            # In single file mode, show error
            messagebox.showerror("Error", f"Conversion failed: {error_msg}")
            self.terminal_callback("Conversion failed")
            self._reset_buttons()
            self.hide_progress()
            self.enable_controls()
            self.conversion_in_progress = False

    def _log_conversion_error(self, file_path, error_msg):
        """Log conversion error to file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.errors_log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {os.path.basename(file_path)}: {error_msg}\n")
        except Exception as e:
            self.terminal_callback(f"Failed to log error: {str(e)}")

    def cancel_conversion(self):
        """Cancel ongoing conversion"""
        self.cancel_flag = True
        self.terminal_callback("Canceling...")
        self._reset_buttons()
        self.hide_progress()

    def _reset_buttons(self):
        """Reset button states"""
        self.start_button.state(['!disabled'])
        if self.current_audio_file:
            self.start_button.configure(style='Action.Ready.TButton')
        else:
            self.start_button.configure(style='Action.Inactive.TButton')
            self.current_filename_var.set("-Empty-")
        self.cancel_button.state(['disabled'])

    def clear_text(self):
        """Clear the text area after confirmation"""
        if self.text_area.get(1.0, tk.END).strip():
            if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all text?"):
                self.text_area.delete(1.0, tk.END)
                self.terminal_callback("Text cleared")
                self.check_text_content()  # Update button states

    def clear_selected_file(self):
        """Clear the selected audio file"""
        if self.conversion_in_progress:
            messagebox.showwarning("Warning", "Conversion in progress. Please wait.")
            return

        self.current_audio_file = None
        self.current_filename_var.set("-Empty-")
        self.start_button.configure(state=tk.DISABLED, style='Action.Inactive.TButton')
        self.play_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.DISABLED)
        self.terminal_callback("Audio file cleared")

    def debug_load_text(self):
        """Debug function to load text file directly into transcribed text area"""
        file_path = filedialog.askopenfilename(
            initialdir=self.config.transcribes_folder,
            title="Debug: Load Transcribed Text",
            filetypes=[("Text Files", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, f.read())
                self.terminal_callback(f"[Debug] Loaded text from: {os.path.basename(file_path)}")
                self.save_text_button.configure(state=tk.NORMAL)
                self.send_to_tts_button.configure(state=tk.NORMAL)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load text file: {str(e)}")

    def play_audio(self):
        """Play current audio file"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            self.play_button.configure(state=tk.DISABLED)
            return

        try:
            self.audio_processor.play_audio(self.current_audio_file)
            self.play_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.terminal_callback("Playing audio file...")
            
            # Start checking playback status
            self.check_playback_status()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {str(e)}")
            self._reset_audio_buttons()
            self.terminal_callback("Error playing audio file")

    def check_playback_status(self):
        """Check if audio is still playing"""
        try:
            if self.audio_processor.is_playing():
                self.root.after(100, self.check_playback_status)
            else:
                self._reset_audio_buttons()
                self.terminal_callback("Audio playback completed")
        except Exception as e:
            logging.error(f"Error checking playback status: {e}")
            self._reset_audio_buttons()

    def stop_audio(self):
        """Stop audio playback"""
        try:
            self.audio_processor.stop_audio()
            self._reset_audio_buttons()
            self.terminal_callback("Audio playback stopped")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop audio: {str(e)}")
            self._reset_audio_buttons()

    def _reset_audio_buttons(self):
        """Reset audio control buttons"""
        self.play_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def disable_controls(self):
        """Disable controls during conversion"""
        self.play_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.DISABLED)
        self.save_text_button.configure(state=tk.DISABLED)
        self.send_to_tts_button.configure(state=tk.DISABLED)

    def enable_controls(self):
        """Enable controls after conversion"""
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            self.play_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def remove_from_queue(self):
        """Remove selected file from queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No file selected in queue")
            return
            
        index = selection[0]
        self.audio_queue.pop(index)
        self.queue_listbox.delete(index)

    def clear_queue(self):
        """Clear entire queue"""
        if self.queue_listbox.size() > 0:
            if messagebox.askyesno("Confirm", "Clear entire queue?"):
                self.audio_queue.clear()
                self.queue_listbox.delete(0, tk.END)

    def process_queue(self):
        """Process all files in the queue"""
        print(f"DEBUG: process_queue called in tabs.py at {datetime.now().strftime('%H:%M:%S.%f')}")
        if not self.audio_queue:
            print("DEBUG: Cannot process queue - queue is empty")
            messagebox.showwarning("Warning", "Queue is empty")
            return
        
        if self.conversion_in_progress:
            print("DEBUG: Cannot process queue - conversion already in progress")
            messagebox.showwarning("Warning", "Conversion already in progress")
            return

        # Create and setup progress frame
        if hasattr(self, 'queue_progress_frame'):
            self.queue_progress_frame.destroy()
            
        self.queue_progress_frame = ttk.Frame(self.queue_frame)
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
        
        # Update status message
        self.terminal_callback(f"Starting to process {len(self.audio_queue)} files in queue...")
        
        # Disable queue controls while processing
        self.process_queue_button.configure(state=tk.DISABLED)
        self.start_button.configure(state=tk.DISABLED)
        
        # Set flag and start processing
        self.conversion_in_progress = True
        print(f"DEBUG: Queue setup complete, calling process_next_in_queue")
        
        # Use a brief delay to ensure UI updates before processing starts
        self.root.after(500, self.process_next_in_queue)

    def process_next_in_queue(self):
        """Process next file in the queue"""
        print(f"DEBUG: process_next_in_queue called at {datetime.now().strftime('%H:%M:%S.%f')}")
        logging.info("Processing next file in queue")
        
        # Important: Fix the file source - use our internal queue, not the queue manager's
        if not self.audio_queue or self.cancel_flag:
            print("DEBUG: No more files to process or processing canceled, finishing queue")
            self.finish_queue_processing()
            return
        
        next_file = self.audio_queue[0]
        self.current_audio_file = next_file
        self.current_filename_var.set(os.path.basename(next_file))
        
        # Update status with progress
        if hasattr(self, 'queue_progress_bar'):
            total = self.queue_progress_bar['maximum']
            current = self.queue_progress_bar['value']
            print(f"DEBUG: Processing file {current + 1} of {total}: {os.path.basename(next_file)}")
            self.terminal_callback(f"\nProcessing {current + 1}/{total}: {os.path.basename(next_file)}")
        else:
            print(f"DEBUG: Processing file: {os.path.basename(next_file)}")
            self.terminal_callback(f"\nProcessing: {os.path.basename(next_file)}")
        
        # Start conversion after delay
        self.conversion_in_progress = True
        print(f"DEBUG: Scheduling conversion to start after {self.config.queue_delay} seconds")
        self.root.after(self.config.queue_delay * 1000, lambda: self._queue_conversion_starter(next_file))
        
    def _queue_conversion_starter(self, file_path):
        """Helper to start the conversion with proper logging"""
        print(f"DEBUG: _queue_conversion_starter called at {datetime.now().strftime('%H:%M:%S.%f')} for {os.path.basename(file_path)}")
        success = self.start_conversion(file_path, queue_mode=True)
        print(f"DEBUG: start_conversion returned {success}")
        if not success:
            print(f"DEBUG: Conversion failed to start for {os.path.basename(file_path)}, attempting next file")
            # If conversion didn't start properly, try the next file
            self.process_next_in_queue()

    def finish_queue_processing(self):
        """Clean up after queue processing is complete"""
        if hasattr(self, 'queue_progress_frame'):
            self.queue_progress_frame.destroy()
        
        self.conversion_in_progress = False
        self.cancel_flag = False
        self.current_audio_file = None
        self.current_filename_var.set("-Empty-")
        self.start_button.configure(state=tk.NORMAL)
        
        # Report any failures
        if self.failed_files:
            failed_count = len(self.failed_files)
            self.terminal_callback(f"\nQueue processing completed with {failed_count} failures:")
            for file_path, error in self.failed_files:
                self.terminal_callback(f"- {os.path.basename(file_path)}")
            self.terminal_callback(f"\nDetailed error log saved to: {os.path.basename(self.errors_log_path)}")
            self.failed_files = []  # Reset for next queue
        else:
            self.terminal_callback("Queue processing completed successfully")
        
        self.update_queue_button_state()

    def cancel_queue(self):
        """Cancel queue processing"""
        self.cancel_flag = True
        self.terminal_callback("Canceling queue processing...")
        if self.current_process:
            self.cancel_conversion()

    def check_text_content(self, event=None):
        """Check if text area has content and update button states"""
        text = self.text_area.get(1.0, tk.END).strip()
        
        if text:
            self.send_to_tts_button.configure(state=tk.NORMAL)
            self.save_text_button.configure(state=tk.NORMAL)
        else:
            self.send_to_tts_button.configure(state=tk.DISABLED)
            self.save_text_button.configure(state=tk.DISABLED)
        
        # Reset the modified flag
        self.text_area.edit_modified(False)

    def handle_font_size_change(self, event):
        """Handle font size changes with Control + mouse wheel"""
        try:
            # Determine direction based on event type
            if hasattr(event, 'delta'):  # Windows
                increase = event.delta > 0
            elif hasattr(event, 'num'):  # Linux
                increase = event.num == 4  # Button-4 is scroll up
            else:
                return

            # Adjust font size
            if increase:
                self.current_font_size = min(self.current_font_size + 1, 24)
            else:
                self.current_font_size = max(self.current_font_size - 1, 8)
            
            # Update font size
            current_font = self.text_area['font']
            if isinstance(current_font, str):
                font_family = 'Helvetica'
            else:
                font_family = current_font[0]
            
            self.text_area.configure(font=(font_family, self.current_font_size))
            self.terminal_callback(f"Font size: {self.current_font_size}")
        except Exception as e:
            self.terminal_callback(f"Error adjusting font size: {str(e)}")

    def show_error_log(self):
        """Show error log in a popup window"""
        # If window already exists, bring it to front
        if self.error_log_window and self.error_log_window.winfo_exists():
            self.error_log_window.lift()
            self.error_log_window.focus_force()
            return

        # Create new window
        self.error_log_window = tk.Toplevel(self.root)
        self.error_log_window.title("Conversion Error Log")
        self.error_log_window.geometry("600x400")
        self.error_log_window.minsize(400, 300)

        # Apply theme colors
        is_dark = self.config.theme == "dark"
        theme = ThemeColors(is_dark)

        # Create text area for log content
        log_text = scrolledtext.ScrolledText(
            self.error_log_window,
            wrap=tk.WORD,
            font=('Helvetica', 10)
        )
        log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        log_text.configure(
            background=theme.input_bg,
            foreground=theme.input_fg,
            insertbackground=theme.input_fg,
            selectbackground=theme.selection_bg,
            selectforeground=theme.selection_fg
        )

        # Load and display log content
        try:
            if os.path.exists(self.errors_log_path):
                with open(self.errors_log_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        log_text.insert('1.0', content)
                    else:
                        log_text.insert('1.0', 'No errors logged yet.')
            else:
                log_text.insert('1.0', 'No error log file exists yet.')
        except Exception as e:
            log_text.insert('1.0', f'Error reading log file: {str(e)}')

        # Make text read-only
        log_text.configure(state='disabled')

        # Add control buttons
        button_frame = ttk.Frame(self.error_log_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Refresh button
        refresh_btn = ttk.Button(
            button_frame,
            text="Refresh",
            command=lambda: self.refresh_error_log(log_text)
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Clear log button
        clear_btn = ttk.Button(
            button_frame,
            text="Clear Log",
            command=lambda: self.clear_error_log(log_text)
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=self.error_log_window.destroy
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

    def refresh_error_log(self, log_text):
        """Refresh the content of the error log window"""
        try:
            log_text.configure(state='normal')
            log_text.delete('1.0', tk.END)
            
            if os.path.exists(self.errors_log_path):
                with open(self.errors_log_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        log_text.insert('1.0', content)
                    else:
                        log_text.insert('1.0', 'No errors logged yet.')
            else:
                log_text.insert('1.0', 'No error log file exists yet.')
            
            log_text.configure(state='disabled')
        except Exception as e:
            log_text.configure(state='normal')
            log_text.delete('1.0', tk.END)
            log_text.insert('1.0', f'Error refreshing log: {str(e)}')
            log_text.configure(state='disabled')

    def clear_error_log(self, log_text):
        """Clear the error log file"""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the error log?"):
            try:
                # Clear file content
                with open(self.errors_log_path, 'w', encoding='utf-8') as f:
                    f.write('')
                
                # Update display
                log_text.configure(state='normal')
                log_text.delete('1.0', tk.END)
                log_text.insert('1.0', 'No errors logged yet.')
                log_text.configure(state='disabled')
                
                self.terminal_callback("Error log cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear error log: {str(e)}")
                self.terminal_callback(f"Failed to clear error log: {str(e)}")

    def load_single_file(self):
        """Load a single file and add it to the queue"""
        print(f"DEBUG: Starting load_single_file - Thread ID: {threading.get_ident()}")
        logging.info("Starting load_single_file function")
        
        try:
            # Use simple file dialog without threading
            print("DEBUG: Opening file dialog...")
            file_path = filedialog.askopenfilename(
                title="Select Audio File",
                filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
            )
            
            print(f"DEBUG: Dialog closed, file path: '{file_path}'")
            logging.info(f"File dialog returned: {file_path}")
            
            if not file_path:
                print("DEBUG: No file selected, returning")
                return
                
            # Do length check directly (no threading)
            try:
                print(f"DEBUG: Checking file exists: {os.path.exists(file_path)}")
                print(f"DEBUG: Starting audio length validation")
                self.audio_processor.check_audio_length(file_path)
                print(f"DEBUG: Audio length validation passed")
                
                # Add file to queue directly using the queue manager
                print(f"DEBUG: Adding file to queue using queue manager")
                
                # Add to internal list first (needed for button state update)
                if file_path not in self.audio_queue:
                    self.audio_queue.append(file_path)
                    
                # Then update the UI through queue manager
                added = self.queue_manager.add_file_to_queue(file_path)
                print(f"DEBUG: File added successfully: {added}")
                
                # Explicitly update button state after adding file
                print(f"DEBUG: Explicitly enabling Process Queue button")
                self.process_queue_button.configure(
                    state=tk.NORMAL,
                    style='Action.Ready.TButton',
                    text=f"Process Queue ({len(self.audio_queue)} files)"
                )
                
                # Force update the UI
                self.root.update_idletasks()
                print(f"DEBUG: Process Queue button state is now: {self.process_queue_button['state']}")
                
            except ValueError as e:
                print(f"DEBUG: Value error: {e}")
                self.terminal_callback(f"Error: {str(e)}")
            except Exception as e:
                print(f"DEBUG: Unexpected error: {e}")
                import traceback
                print(traceback.format_exc())
                self.terminal_callback(f"Error processing file: {str(e)}")
                
        except Exception as e:
            import traceback
            print(f"DEBUG: Critical error in load_single_file: {e}")
            print(traceback.format_exc())
            logging.error(f"Error in load_single_file: {e}\n{traceback.format_exc()}")
            self.terminal_callback(f"Error loading file: {str(e)}")
        
        print(f"DEBUG: Exiting load_single_file successfully")
        logging.info("Exiting load_single_file function")

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