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
        self.setup_tab()

    def setup_tab(self):
        # Main container with padding
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

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

        # Text display area with drop zone functionality
        text_frame = ttk.LabelFrame(main_frame, text="Transcribed Text", 
                                  style="Group.TLabelframe", padding="10")
        text_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # Add drag-drop instruction label
        drop_label = ttk.Label(text_frame, text="Drop audio file here or use the input options above",
                             font=('Helvetica', 9, 'italic'))
        drop_label.grid(row=0, column=0, pady=(0, 5))

        # Add clear button to text frame
        clear_text_btn = ttk.Button(text_frame, text="Clear Text",
                                  command=self.clear_text)
        clear_text_btn.grid(row=0, column=1, pady=(0, 5), padx=5)

        # Apply theme colors to text area
        is_dark = self.config.theme == "dark"
        theme = ThemeColors(is_dark)

        # Make text area 25% smaller by reducing height from 15 to 11
        self.text_area = scrolledtext.ScrolledText(text_frame, height=11, wrap=tk.WORD,
                                                 font=('Helvetica', 10))
        self.text_area.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.text_area.configure(
            background=theme.input_bg,
            foreground=theme.input_fg,
            insertbackground=theme.input_fg,
            selectbackground=theme.selection_bg,
            selectforeground=theme.selection_fg
        )
        self.text_area.drop_target_register(DND_FILES)
        self.text_area.dnd_bind('<<Drop>>', self.handle_drop)

        # Conversion controls frame
        conversion_frame = ttk.Frame(main_frame)
        conversion_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        conversion_frame.columnconfigure(0, weight=1)
        conversion_frame.columnconfigure(3, weight=1)

        # Start conversion button in its own frame
        self.start_button = ttk.Button(conversion_frame, text="Start Conversion", 
                                     command=self.start_conversion,
                                     style='Action.Inactive.TButton')  # Start with inactive style
        self.start_button.grid(row=0, column=1, padx=10)

        self.cancel_button = ttk.Button(conversion_frame, text="Cancel", 
                                      command=self.cancel_conversion,
                                      style='Cancel.TButton',
                                      state=tk.DISABLED)
        self.cancel_button.grid(row=0, column=2, padx=10)

        # Progress bar frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        progress_frame.grid_propagate(False)
        progress_frame.configure(height=25)
        progress_frame.grid_remove()
        self.progress_frame = progress_frame

        # Terminal output area
        terminal_frame = ttk.LabelFrame(main_frame, text="Process Output", 
                                      style="Group.TLabelframe", padding="10")
        terminal_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        self.terminal_area = scrolledtext.ScrolledText(terminal_frame, height=8, wrap=tk.WORD,
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

        # Control buttons in a labeled frame
        control_frame = ttk.LabelFrame(main_frame, text="File Controls", 
                                     style="Group.TLabelframe", padding="10")
        control_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # Center the buttons in the control frame
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(3, weight=1)

        self.save_text_button = ttk.Button(control_frame, text="Save Text", 
                                         command=self.save_transcribed_text,
                                         state=tk.DISABLED)
        self.save_text_button.grid(row=0, column=1, padx=10)

        self.send_to_tts_button = ttk.Button(control_frame, text="Send to TTS", 
                                           command=self.send_to_tts,
                                           state=tk.DISABLED)
        self.send_to_tts_button.grid(row=0, column=2, padx=10)

        # Configure grid weights
        self.parent.columnconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)
        terminal_frame.columnconfigure(0, weight=1)
        terminal_frame.rowconfigure(0, weight=1)
        progress_frame.columnconfigure(0, weight=1)

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
            else:
                messagebox.showwarning("Warning", "No text to send")
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
        file_path = event.data
        if file_path:
            file_path = file_path.strip('{}')
            if file_path.lower().endswith(('.wav', '.mp3', '.flac')):
                self.current_audio_file = file_path
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
            self.terminal_callback(f"Audio file ready: {os.path.basename(file_path)}")
            self.start_button.configure(style='Action.Ready.TButton')  # Change to ready style

    def start_conversion(self, file_path=None):
        """Start audio to text conversion"""
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
        self.save_text_button.configure(state=tk.NORMAL)
        self.send_to_tts_button.configure(state=tk.NORMAL)
        self.hide_progress()
        self.start_button.configure(style='Action.Inactive.TButton')  # Reset to inactive style
        self.current_audio_file = None  # Clear current file

    def _conversion_error(self, error_msg):
        """Handle conversion error"""
        messagebox.showerror("Error", f"Conversion failed: {error_msg}")
        self.terminal_callback("Conversion failed")
        self._reset_buttons()
        self.hide_progress()

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
        self.cancel_button.state(['disabled'])

    def clear_text(self):
        """Clear the text area after confirmation"""
        if self.text_area.get(1.0, tk.END).strip():
            if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all text?"):
                self.text_area.delete(1.0, tk.END)
                self.terminal_callback("Text cleared")
                self.save_text_button.configure(state=tk.DISABLED)
                self.send_to_tts_button.configure(state=tk.DISABLED)
                self.start_button.configure(style='Action.Inactive.TButton')