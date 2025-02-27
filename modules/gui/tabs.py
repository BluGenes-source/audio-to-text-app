import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES
import os
import logging
import threading
from .styles import ThemeColors

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
        self.audio_queue = []  # Store queued audio files
        self.current_font_size = 10  # Add default font size tracking
        self.setup_tab()

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

        # Start conversion button
        self.start_button = ttk.Button(conversion_frame, text="Start Conversion", 
                                     command=self.start_conversion,
                                     style='Action.Inactive.TButton')
        self.start_button.grid(row=0, column=3, padx=10)

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
        self.text_area.bind('<Control-Button-2>', self.handle_font_size_change)
        
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
        queue_frame = ttk.LabelFrame(right_frame, text="Audio Queue", 
                                   style="Group.TLabelframe", padding="10")
        queue_frame.grid(row=0, column=0, sticky="nsew")
        
        # Queue controls
        queue_controls = ttk.Frame(queue_frame)
        queue_controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Button(queue_controls, text="Add to Queue",
                  command=self.add_to_queue).grid(row=0, column=0, padx=2)
        ttk.Button(queue_controls, text="Remove Selected",
                  command=self.remove_from_queue).grid(row=0, column=1, padx=2)
        ttk.Button(queue_controls, text="Clear Queue",
                  command=self.clear_queue).grid(row=0, column=2, padx=2)
        
        # Queue listbox
        self.queue_listbox = tk.Listbox(queue_frame, height=15,
                                      selectmode=tk.SINGLE)
        self.queue_listbox.grid(row=1, column=0, sticky="nsew")
        
        # Queue scrollbar
        queue_scrollbar = ttk.Scrollbar(queue_frame,
                                      orient="vertical",
                                      command=self.queue_listbox.yview)
        queue_scrollbar.grid(row=1, column=1, sticky="ns")
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)
        
        # Process queue button
        ttk.Button(queue_frame, text="Process Queue",
                  command=self.process_queue,
                  style='Action.Ready.TButton').grid(row=2, column=0,
                                                   columnspan=2,
                                                   sticky="ew",
                                                   pady=(5, 0))

        # Configure weights for queue frame
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(1, weight=1)
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
            messagebox.showwarning("Warning", "Conversion in progress. Please wait.")
            return

        file_path = event.data
        if file_path:
            file_path = file_path.strip('{}')
            if file_path.lower().endswith(('.wav', '.mp3', '.flac')):
                self.current_audio_file = file_path
                self.current_filename_var.set(os.path.basename(file_path))
                self.terminal_callback(f"Audio file ready: {os.path.basename(file_path)}")
                self.start_button.configure(style='Action.Ready.TButton')  # Change to ready style
            else:
                messagebox.showerror("Error", "Please drop an audio file (WAV, MP3, or FLAC)")

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
        """Load audio file from input folder"""
        if not self.config.input_folder:
            messagebox.showwarning("Warning", "Please select an input folder first")
            return
        
        file_path = filedialog.askopenfilename(
            initialdir=self.config.input_folder,
            title="Select Audio File",
            filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
        )
        
        if file_path:
            self.current_audio_file = file_path
            self.current_filename_var.set(os.path.basename(file_path))
            self.terminal_callback(f"Audio file ready: {os.path.basename(file_path)}")
            self.start_button.configure(style='Action.Ready.TButton')  # Change to ready style

    def start_conversion(self, file_path=None, queue_mode=False):
        """Start audio to text conversion"""
        if self.conversion_in_progress:
            return

        if not self.audio_processor.ffmpeg_path:
            messagebox.showerror("Error", "FFmpeg is not properly configured. Please check the setup.")
            return

        # Use provided file_path or the stored current_audio_file
        file_path = file_path or self.current_audio_file

        # If no file is selected, show file dialog
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
            )
            if file_path:
                self.current_audio_file = file_path
        
        if file_path:
            try:
                if not os.path.exists(file_path):
                    messagebox.showerror("Error", f"File not found: {file_path}")
                    return
                
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    messagebox.showerror("Error", "Selected file is empty")
                    return
                
                if file_size > 100 * 1024 * 1024:  # 100MB limit
                    if not messagebox.askyesno("Warning", 
                        "The selected file is larger than 100MB. Processing may take a while. Continue?"):
                        return
                
                if not os.access(self.config.output_folder, os.W_OK):
                    messagebox.showerror("Error", 
                        f"Cannot write to output folder: {self.config.output_folder}\nPlease select a different output location.")
                    return
                
                self.conversion_in_progress = True
                self.disable_controls()
                self.start_button.state(['disabled'])
                self.cancel_button.state(['!disabled'])
                self.terminal_callback("Converting audio to text...")
                self.cancel_flag = False
                self.show_progress()
                
                self.current_process = threading.Thread(
                    target=self._conversion_thread,
                    args=(file_path,)
                )
                self.current_process.start()
                
            except Exception as e:
                logging.error(f"Error starting conversion: {e}", exc_info=True)
                messagebox.showerror("Error", f"Failed to start conversion: {str(e)}")
                self._reset_buttons()
                self.hide_progress()
                self.conversion_in_progress = False

    def _conversion_thread(self, file_path):
        """Thread for audio to text conversion"""
        try:
            def progress_callback(msg):
                self.parent.after(0, lambda: self.terminal_callback(msg))
            
            text = self.audio_processor.convert_audio_to_text(file_path, progress_callback)
            
            if not self.cancel_flag and text:
                self.parent.after(0, lambda: self._conversion_complete(text))
        except Exception as e:
            self.parent.after(0, lambda: self._conversion_error(str(e)))

    def _conversion_complete(self, text):
        """Handle successful conversion"""
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, text)
        self.terminal_callback("Conversion completed successfully")
        self._reset_buttons()
        self.enable_controls()
        self.play_button.configure(state=tk.NORMAL)  # Enable play button
        self.save_text_button.configure(state=tk.NORMAL)
        self.send_to_tts_button.configure(state=tk.NORMAL)
        self.hide_progress()
        self.start_button.configure(style='Action.Inactive.TButton')  # Reset to inactive style
        self.current_filename_var.set("-Empty-")
        self.current_audio_file = None  # Clear current file
        self.conversion_in_progress = False

        if text:
            self.text_area.insert(tk.END, f"\n\n[{os.path.basename(self.current_audio_file)}]\n")
            self.text_area.insert(tk.END, text)
            self.terminal_callback("Conversion completed successfully")
            self.save_text_button.configure(state=tk.NORMAL)
            self.send_to_tts_button.configure(state=tk.NORMAL)
            self.play_button.configure(state=tk.NORMAL)
            
            # If in queue mode, process next file
            if self.audio_queue and self.current_audio_file == self.audio_queue[0]:
                self.audio_queue.pop(0)
                self.queue_listbox.delete(0)
                self.process_next_in_queue()
            else:
                self._reset_buttons()
        
        self.hide_progress()
        self.start_button.configure(style='Action.Ready.TButton')  # Reset to ready style
        self.current_filename_var.set("-Empty-")
        self.current_audio_file = None
        self.conversion_in_progress = False

    def _conversion_error(self, error_msg):
        """Handle conversion error"""
        messagebox.showerror("Error", f"Conversion failed: {error_msg}")
        self.terminal_callback("Conversion failed")
        self._reset_buttons()
        self.hide_progress()
        self.enable_controls()
        self.conversion_in_progress = False

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
        self.start_button.configure(style='Action.Inactive.TButton')
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

    def add_to_queue(self):
        """Add current audio file to queue"""
        if not self.current_audio_file:
            messagebox.showwarning("Warning", "No audio file selected")
            return
            
        if self.current_audio_file in self.audio_queue:
            messagebox.showwarning("Warning", "File already in queue")
            return
            
        self.audio_queue.append(self.current_audio_file)
        self.queue_listbox.insert(tk.END, os.path.basename(self.current_audio_file))
        self.clear_selected_file()  # Clear current selection after adding to queue

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
        if not self.audio_queue:
            messagebox.showwarning("Warning", "Queue is empty")
            return
            
        if self.conversion_in_progress:
            messagebox.showwarning("Warning", "Conversion already in progress")
            return
            
        self.process_next_in_queue()

    def process_next_in_queue(self):
        """Process next file in the queue"""
        if not self.audio_queue:
            self.conversion_in_progress = False
            self.terminal_callback("Queue processing complete")
            return
            
        next_file = self.audio_queue[0]
        self.current_audio_file = next_file
        self.current_filename_var.set(os.path.basename(next_file))
        self.start_conversion(queue_mode=True)

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
        """Handle font size changes with Control + middle mouse button"""
        try:
            # Get the direction of scroll (up or down)
            if event.delta > 0 or (hasattr(event, 'num') and event.num == 4):
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