import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES
import os
import logging
import threading
import re
from .styles import ThemeColors

class TextToSpeechTab:
    def __init__(self, parent, config, audio_processor, update_status_callback, root):
        self.parent = parent
        self.config = config
        self.audio_processor = audio_processor
        self.update_status = update_status_callback
        self.root = root
        self.preview_audio_path = None
        self.audio_playing = False
        self.cancel_flag = False
        self.auto_insert_enabled = False  # Add this line
        self.current_font_size = 10  # Add default font size tracking
        self.setup_tab()

    def setup_tab(self):
        # Get theme colors
        is_dark = self.config.theme == "dark"
        theme = ThemeColors(is_dark)
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(self.parent, text="Folder Settings", 
                                    style="Group.TLabelframe", padding="10")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Create groups within folder frame
        input_group = ttk.Frame(folder_frame)
        input_group.grid(row=0, column=0, padx=5)
        
        # Input options
        ttk.Label(input_group, text="Text Input Options:", 
                 style="Subtitle.TLabel").grid(row=0, column=0, pady=(0, 5))
        ttk.Button(input_group, text="Load Text File", 
                  command=self.load_text_file).grid(row=1, column=0)
        
        # Text input area with format controls
        text_frame = ttk.LabelFrame(self.parent, text="Text Input", 
                                  style="Group.TLabelframe", padding="10")
        text_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Format frame
        format_frame = ttk.Frame(text_frame)
        format_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        format_frame.columnconfigure(14, weight=1)  # Add weight to last column
        
        # Drop label
        drop_label = ttk.Label(format_frame, 
                             text="Drop text file here or paste text directly",
                             font=('Helvetica', 9, 'italic'))
        drop_label.grid(row=0, column=0, pady=(0, 5))
        
        # Format controls
        self.short_pause_length = tk.StringVar(value="300")
        self.long_pause_length = tk.StringVar(value="800")
        self.pause_marker = tk.StringVar(value="|")
        
        # Controls layout - now in two rows
        # First row - pause controls
        ttk.Label(format_frame, text="Short Pause (ms):").grid(row=0, column=0, padx=(5, 2))
        short_pause_entry = ttk.Entry(format_frame, textvariable=self.short_pause_length, width=6)
        short_pause_entry.grid(row=0, column=1, padx=2)
        
        ttk.Label(format_frame, text="Long Pause (ms):").grid(row=0, column=2, padx=(5, 2))
        long_pause_entry = ttk.Entry(format_frame, textvariable=self.long_pause_length, width=6)
        long_pause_entry.grid(row=0, column=3, padx=2)
        
        ttk.Label(format_frame, text="Pause Marker:").grid(row=0, column=4, padx=(5, 2))
        marker_entry = ttk.Entry(format_frame, textvariable=self.pause_marker, width=3)
        marker_entry.grid(row=0, column=5, padx=2)

        # Add auto-insert toggle button
        self.auto_insert_button = ttk.Button(format_frame, text="Auto-Insert: OFF",
                                          command=self.toggle_auto_insert,
                                          style='Action.Inactive.TButton')
        self.auto_insert_button.grid(row=0, column=6, padx=5)
        
        # Second row - action buttons
        insert_short_btn = ttk.Button(format_frame, text="Insert Short Pause",
                                   command=lambda: self.insert_pause_marker(True))
        insert_short_btn.grid(row=1, column=0, columnspan=2, padx=2, pady=(5,0))

        insert_long_btn = ttk.Button(format_frame, text="Insert Long Pause",
                                  command=lambda: self.insert_pause_marker(False))
        insert_long_btn.grid(row=1, column=2, columnspan=2, padx=2, pady=(5,0))

        auto_pause_btn = ttk.Button(format_frame, text="Auto-Add Pauses",
                                 command=self.auto_add_pauses)
        auto_pause_btn.grid(row=1, column=4, columnspan=2, padx=2, pady=(5,0))
        
        save_text_btn = ttk.Button(format_frame, text="Save Text",
                                command=self.save_tts_text)
        save_text_btn.grid(row=1, column=6, columnspan=2, padx=2, pady=(5,0))

        clear_text_btn = ttk.Button(format_frame, text="Clear Text",
                                 command=self.clear_text)
        clear_text_btn.grid(row=1, column=8, columnspan=2, padx=2, pady=(5,0))
        
        # Text area with mouse bindings
        self.tts_text_area = scrolledtext.ScrolledText(text_frame, height=15, wrap=tk.WORD,
                                                     font=('Helvetica', self.current_font_size))
        self.tts_text_area.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.tts_text_area.configure(
            background=theme.input_bg,
            foreground=theme.input_fg,
            insertbackground=theme.input_fg,
            selectbackground=theme.selection_bg,
            selectforeground=theme.selection_fg
        )
        self.tts_text_area.drop_target_register(DND_FILES)
        self.tts_text_area.dnd_bind('<<Drop>>', self.handle_text_drop)
        # Add click bindings for auto-insert and mouse wheel binding for font size
        self.tts_text_area.bind('<Button-1>', self.handle_text_click)  # Left click
        self.tts_text_area.bind('<Button-3>', self.handle_text_click)  # Right click
        self.tts_text_area.bind('<Control-MouseWheel>', self.handle_font_size_change)  # Windows
        self.tts_text_area.bind('<Control-Button-4>', self.handle_font_size_change)    # Linux up
        self.tts_text_area.bind('<Control-Button-5>', self.handle_font_size_change)    # Linux down
        
        # Voice options
        self.setup_voice_options()
        
        # Controls
        self.setup_control_buttons()
        
        # Configure grid weights
        self.parent.columnconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)

    def setup_voice_options(self):
        # Options frame
        options_frame = ttk.LabelFrame(self.parent, text="Voice Options", 
                                     style="Group.TLabelframe", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Engine frame
        engine_frame = ttk.Frame(options_frame)
        engine_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        
        ttk.Label(engine_frame, text="Engine:").grid(row=0, column=0, padx=5)
        self.tts_engine = tk.StringVar(value="google")
        ttk.Radiobutton(engine_frame, text="Google TTS (Online)", 
                       variable=self.tts_engine, value="google").grid(row=0, column=1, padx=5)
        ttk.Radiobutton(engine_frame, text="Local TTS (Offline)", 
                       variable=self.tts_engine, value="local").grid(row=0, column=2, padx=5)
        
        # Google voice options
        self.google_lang = tk.StringVar(value="en")
        ttk.Label(options_frame, text="Google Voice:").grid(row=1, column=0, padx=5)
        ttk.Radiobutton(options_frame, text="US English", 
                       variable=self.google_lang, value="en").grid(row=1, column=1, padx=5)
        ttk.Radiobutton(options_frame, text="British English", 
                       variable=self.google_lang, value="en-gb").grid(row=1, column=2, padx=5)
        
        # Local voice options
        ttk.Label(options_frame, text="Local Voice:").grid(row=2, column=0, padx=5, pady=5)
        self.voice_selector = ttk.Combobox(options_frame, state="readonly")
        self.voice_selector.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.update_voice_list()

    def setup_control_buttons(self):
        control_frame = ttk.LabelFrame(self.parent, text="Controls", 
                                     style="Group.TLabelframe", padding="10")
        control_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(7, weight=1)
        
        # TTS generate button with inactive style initially
        self.tts_start_button = ttk.Button(control_frame, text="Generate Speech", 
                                         command=self.start_text_to_speech,
                                         style='Action.Inactive.TButton')
        self.tts_start_button.grid(row=0, column=1, padx=10)
        
        self.tts_cancel_button = ttk.Button(control_frame, text="Cancel", 
                                          command=self.cancel_text_to_speech,
                                          style='Cancel.TButton',
                                          state=tk.DISABLED)
        self.tts_cancel_button.grid(row=0, column=2, padx=10)

        self.play_button = ttk.Button(control_frame, text="▶ Play", 
                                    command=self.play_audio,
                                    state=tk.DISABLED)
        self.play_button.grid(row=0, column=3, padx=10)
        
        self.stop_button = ttk.Button(control_frame, text="⏹ Stop", 
                                    command=self.stop_audio,
                                    state=tk.DISABLED)
        self.stop_button.grid(row=0, column=4, padx=10)

        self.save_audio_button = ttk.Button(control_frame, text="Save Audio", 
                                          command=self.save_generated_audio,
                                          state=tk.DISABLED)
        self.save_audio_button.grid(row=0, column=5, padx=10)

    def update_voice_list(self):
        try:
            voices = self.audio_processor.get_available_voices()
            voice_names = [voice.name for voice in voices]
            self.voice_selector['values'] = voice_names
            if voice_names:
                self.voice_selector.set(voice_names[0])
        except Exception as e:
            logging.error(f"Failed to update voice list: {e}")
            messagebox.showerror("Error", "Failed to initialize voice list")

    def handle_text_drop(self, event):
        """Handle dropped text files"""
        file_path = event.data.strip('{}')
        if file_path.lower().endswith('.txt'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.tts_text_area.delete(1.0, tk.END)
                    self.tts_text_area.insert(tk.END, f.read())
                self.update_status(f"Loaded text file: {os.path.basename(file_path)}")
                self.tts_start_button.configure(style='Action.Ready.TButton')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load text file: {str(e)}")
        else:
            messagebox.showerror("Error", "Please drop a text (.txt) file")

    def load_text_file(self):
        """Load text from a file"""
        initial_dir = self.config.transcribes_folder
        os.makedirs(initial_dir, exist_ok=True)
        
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select Text File",
            filetypes=[("Text Files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.tts_text_area.delete(1.0, tk.END)
                    self.tts_text_area.insert(tk.END, f.read())
                self.update_status(f"Loaded text file: {os.path.basename(file_path)}")
                self.tts_start_button.configure(style='Action.Ready.TButton')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load text file: {str(e)}")

    def insert_pause_marker(self, is_short=True):
        """Insert pause marker at current cursor position"""
        try:
            current_pos = self.tts_text_area.index(tk.INSERT)
            pause_ms = self.short_pause_length.get() if is_short else self.long_pause_length.get()
            marker = f"<break time=\"{int(pause_ms)/1000}s\"/>"
            self.tts_text_area.insert(current_pos, marker)
            self.update_status(f"Inserted {'short' if is_short else 'long'} pause marker")
        except ValueError:
            messagebox.showerror("Error", "Invalid pause length value")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert pause marker: {str(e)}")

    def auto_add_pauses(self):
        """Automatically add pause markers after periods"""
        try:
            text = self.tts_text_area.get(1.0, tk.END).strip()
            if not text:
                messagebox.showwarning("Warning", "No text to process")
                return
            
            # Check if there are any periods in the text
            if '.' not in text:
                messagebox.showwarning("Warning", "No periods found in text. Cannot add pauses.")
                return

            # Get current cursor position
            current_pos = self.tts_text_area.index(tk.INSERT)
            
            # Add pause markers after periods
            short_pause = f"<break time=\"{int(self.short_pause_length.get())/1000}s\"/>"
            long_pause = f"<break time=\"{int(self.long_pause_length.get())/1000}s\"/>"
            
            # Add long pauses after periods and short pauses after commas
            modified_text = text.replace('. ', f'. {long_pause} ')
            modified_text = modified_text.replace(', ', f', {short_pause} ')
            
            # Update text area
            self.tts_text_area.delete(1.0, tk.END)
            self.tts_text_area.insert(1.0, modified_text)
            
            # Restore cursor position
            try:
                self.tts_text_area.mark_set(tk.INSERT, current_pos)
            except:
                pass

            self.update_status("Added pause markers after periods and commas")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid pause length value")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add pause markers: {str(e)}")

    def save_tts_text(self):
        """Save text to file"""
        text = self.tts_text_area.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "No text to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            initialdir=self.config.transcribes_folder,
            title="Save Text As",
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

    def start_text_to_speech(self):
        text = self.tts_text_area.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter or load some text first")
            return
        
        self.tts_start_button.state(['disabled'])
        self.tts_cancel_button.state(['!disabled'])
        self.update_status("Converting text to speech...")
        
        # Generate output filename
        base_name = "speech"
        counter = 1
        while True:
            filename = f"{base_name}{'_' + str(counter) if counter > 1 else ''}.wav"
            output_path = os.path.join(self.config.dialogs_folder, filename)
            if not os.path.exists(output_path):
                break
            counter += 1
        
        self.cancel_flag = False
        self.current_process = threading.Thread(
            target=self._tts_thread,
            args=(text, output_path)
        )
        self.current_process.start()

    def _tts_thread(self, text, output_path):
        try:
            engine_type = self.tts_engine.get()
            voice_name = self.voice_selector.get() if engine_type == "local" else None
            lang = self.google_lang.get() if engine_type == "google" else None
            
            success = self.audio_processor.text_to_speech(
                text, output_path, engine_type, voice_name, lang,
                progress_callback=self.update_status
            )
            
            if success and not self.cancel_flag:
                self.preview_audio_path = output_path
                self.root.after(0, self._tts_complete)
        except Exception as e:
            self.root.after(0, lambda: self._tts_error(str(e)))

    def _tts_complete(self):
        self.update_status("Audio generated - ready for preview")
        self._reset_tts_buttons()
        self.play_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL)
        self.save_audio_button.configure(state=tk.NORMAL)

    def _tts_error(self, error_msg):
        messagebox.showerror("Error", f"Failed to convert text to speech: {error_msg}")
        self.update_status("Ready")
        self._reset_tts_buttons()

    def _reset_tts_buttons(self):
        self.tts_start_button.state(['!disabled'])
        self.tts_cancel_button.state(['disabled'])
        self.audio_playing = False
        self.play_button.configure(text="▶ Play")

    def cancel_text_to_speech(self):
        self.cancel_flag = True
        self.update_status("Canceling...")
        self._reset_tts_buttons()

    def play_audio(self):
        if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
            messagebox.showerror("Error", "No audio file to play")
            return
        
        try:
            if not self.audio_playing:
                self.audio_processor.play_audio(self.preview_audio_path)
                self.audio_playing = True
                self.play_button.configure(text="⏸ Stop")
                self.stop_button.configure(state=tk.NORMAL)
                self.update_status("Playing audio...")
                self.root.after(100, self._check_audio_playing)
            else:
                self.stop_audio()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._reset_play_button()

    def _check_audio_playing(self):
        if self.audio_playing and not self.audio_processor.is_playing():
            self._reset_play_button()
        elif self.audio_playing:
            self.root.after(100, self._check_audio_playing)

    def stop_audio(self):
        if self.audio_playing:
            self.audio_processor.stop_audio()
            self._reset_play_button()

    def _reset_play_button(self):
        self.audio_playing = False
        self.play_button.configure(text="▶ Play")
        self.stop_button.configure(state=tk.DISABLED)

    def save_generated_audio(self):
        if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
            messagebox.showerror("Error", "No audio file to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            initialdir=self.config.dialogs_folder,
            title="Save Audio As",
            defaultextension=".wav",
            filetypes=[("Wave Files", "*.wav")]
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.preview_audio_path, file_path)
                self.update_status(f"Saved audio to: {os.path.basename(file_path)}")
                
                try:
                    os.remove(self.preview_audio_path)
                    self.preview_audio_path = file_path
                except:
                    pass
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save audio: {str(e)}")

    def clear_text(self):
        """Clear the text area after confirmation"""
        if self.tts_text_area.get(1.0, tk.END).strip():
            if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all text?"):
                self.tts_text_area.delete(1.0, tk.END)
                self.update_status("Text cleared")
                self.tts_start_button.configure(style='Action.Inactive.TButton')

    def set_text(self, text):
        """Set the text in the text area and switch to this tab"""
        self.tts_text_area.delete(1.0, tk.END)
        self.tts_text_area.insert(tk.END, text)
        self.update_status("Text received from Speech-to-Text tab")
        self.tts_start_button.configure(style='Action.Ready.TButton')
        # Switch to this tab (notebook is parent's parent)
        self.parent.master.select(self.parent)

    def toggle_auto_insert(self):
        """Toggle auto-insert mode for periods and pauses"""
        self.auto_insert_enabled = not self.auto_insert_enabled
        if self.auto_insert_enabled:
            self.auto_insert_button.configure(
                text="Auto-Insert: ON",
                style='Action.Ready.TButton'
            )
            self.update_status("Auto-insert mode enabled")
        else:
            self.auto_insert_button.configure(
                text="Auto-Insert: OFF",
                style='Action.Inactive.TButton'
            )
            self.update_status("Auto-insert mode disabled")

    def handle_text_click(self, event):
        """Handle click in text area for auto-insert"""
        if self.auto_insert_enabled:
            try:
                # Get click position
                click_pos = self.tts_text_area.index(f"@{event.x},{event.y}")
                
                # Determine if it's left click (event.num = 1) or right click (event.num = 3)
                is_short = event.num == 1
                pause_ms = self.short_pause_length.get() if is_short else self.long_pause_length.get()
                
                # Insert period and appropriate pause
                pause_marker = f"<break time=\"{int(pause_ms)/1000}s\"/>"
                self.tts_text_area.insert(click_pos, f". {pause_marker} ")
                
                # Move cursor after inserted text
                self.tts_text_area.mark_set(tk.INSERT, f"{click_pos}+{len(pause_marker)+3}c")
                
                # Update status with feedback
                self.update_status(f"Inserted {'short' if is_short else 'long'} pause")
                
                return "break"  # Prevent default click behavior
            except Exception as e:
                self.update_status(f"Error in auto-insert: {str(e)}")

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
            current_font = self.tts_text_area['font']
            if isinstance(current_font, str):
                font_family = 'Helvetica'
            else:
                font_family = current_font[0]
            
            self.tts_text_area.configure(font=(font_family, self.current_font_size))
            self.update_status(f"Font size: {self.current_font_size}")
        except Exception as e:
            self.update_status(f"Error adjusting font size: {str(e)}")