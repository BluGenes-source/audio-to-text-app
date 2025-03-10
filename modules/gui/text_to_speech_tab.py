import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES
import os
import logging
import threading
import re
import asyncio
from datetime import datetime
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
        self.auto_insert_enabled = False
        self.current_font_size = 10
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
        
        # TTS Source frame
        source_frame = ttk.Frame(options_frame)
        source_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,10))
        
        ttk.Label(source_frame, text="TTS Source:").grid(row=0, column=0, padx=5)
        self.tts_engine = tk.StringVar(value="huggingface")  # Changed default to Hugging Face
        ttk.Radiobutton(source_frame, text="Google TTS (Online)", 
                       variable=self.tts_engine, value="google",
                       command=self.update_voice_options).grid(row=0, column=1, padx=5)
        ttk.Radiobutton(source_frame, text="Local TTS (Offline)", 
                       variable=self.tts_engine, value="local",
                       command=self.update_voice_options).grid(row=0, column=2, padx=5)
        ttk.Radiobutton(source_frame, text="AI Models", 
                       variable=self.tts_engine, value="huggingface",
                       command=self.update_voice_options).grid(row=0, column=3, padx=5)
        
        # AI API Selection frame
        api_frame = ttk.Frame(options_frame)
        api_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0,10))
        
        ttk.Label(api_frame, text="AI API:").grid(row=0, column=0, padx=5)
        self.api_var = tk.StringVar(value="huggingface")
        api_dropdown = ttk.Combobox(api_frame, textvariable=self.api_var, state="readonly")
        api_dropdown['values'] = ["Hugging Face"]  # For now, only Hugging Face is available
        api_dropdown.grid(row=0, column=1, padx=5, sticky="ew")
        api_dropdown.bind('<<ComboboxSelected>>', lambda e: self.update_voice_options())
        
        # Create container frames for different engine options
        self.google_frame = ttk.Frame(options_frame)
        self.local_frame = ttk.Frame(options_frame)
        self.huggingface_frame = ttk.Frame(options_frame)
        
        # Google voice options
        self.google_lang = tk.StringVar(value="en")
        ttk.Label(self.google_frame, text="Google Voice:").grid(row=0, column=0, padx=5)
        ttk.Radiobutton(self.google_frame, text="US English", 
                       variable=self.google_lang, value="en").grid(row=0, column=1, padx=5)
        ttk.Radiobutton(self.google_frame, text="British English", 
                       variable=self.google_lang, value="en-gb").grid(row=0, column=2, padx=5)
        
        # Local voice options
        ttk.Label(self.local_frame, text="Local Voice:").grid(row=0, column=0, padx=5)
        self.voice_selector = ttk.Combobox(self.local_frame, state="readonly")
        self.voice_selector.grid(row=0, column=1, columnspan=2, padx=5, sticky="ew")
        
        # Hugging Face options
        ttk.Label(self.huggingface_frame, text="Model:").grid(row=0, column=0, padx=5)
        self.hf_model_selector = ttk.Combobox(self.huggingface_frame, state="readonly")
        self.hf_model_selector.grid(row=0, column=1, columnspan=2, padx=5, sticky="ew")
        
        # Replace download button with instructions button
        self.instructions_button = ttk.Button(self.huggingface_frame, text="Installation Instructions",
                  command=self.show_model_instructions)
        self.instructions_button.grid(row=0, column=3, padx=5)
        
        # Recommended models frame
        recommended_frame = ttk.LabelFrame(self.huggingface_frame, text="Recommended Models",
                                         style="Group.TLabelframe", padding="5")
        recommended_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)
        
        # Get recommended models with error handling - FIX: Safer method to get models
        try:
            if hasattr(self.audio_processor, 'get_huggingface_recommended_models'):
                recommended_models = self.audio_processor.get_huggingface_recommended_models() or []
            else:
                # Use default models if the method isn't available
                recommended_models = [
                    {"id": "microsoft/speecht5_tts", "name": "SpeechT5 TTS"},
                    {"id": "espnet/kan-bayashi_ljspeech_vits", "name": "LJSpeech VITS"},
                    {"id": "suno/bark-small", "name": "Bark Small"}
                ]
                logging.warning("AudioProcessor doesn't have get_huggingface_recommended_models method, using defaults")
        except Exception as e:
            logging.error(f"Error getting recommended models: {e}")
            recommended_models = []
        
        if recommended_models:
            # Modified to only select model in dropdown without starting download
            for i, model in enumerate(recommended_models):
                ttk.Button(recommended_frame, text=model['name'],
                          command=lambda m=model['id']: self.select_model_only(m)).grid(
                              row=i//2, column=i%2, padx=5, pady=2, sticky="ew")
        else:
            ttk.Label(recommended_frame, text="No recommended models available").grid(
                row=0, column=0, padx=5, pady=2)
        
        # Update voice lists
        self.update_voice_list()
        self.update_hf_model_list()
        
        # Show initial frame based on default engine
        self.update_voice_options()

    def update_voice_options(self, event=None):
        """Update visible voice options based on selected engine"""
        # Hide all frames first
        self.google_frame.grid_remove()
        self.local_frame.grid_remove()
        self.huggingface_frame.grid_remove()
        
        # Show relevant frame based on selection
        if self.tts_engine.get() == "google":
            self.google_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        elif self.tts_engine.get() == "local":
            self.local_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
            self.update_voice_list()
        else:  # huggingface
            self.huggingface_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
            # Initialize HF model manager if needed
            self._ensure_hf_model_manager_initialized()
            # Update model list
            self.update_hf_model_list()

    def _ensure_hf_model_manager_initialized(self):
        """Ensures the Hugging Face model manager is initialized"""
        try:
            # Check if initialization is needed
            if not hasattr(self.audio_processor, 'hf_manager') or self.audio_processor.hf_manager is None:
                self.update_status("Initializing Hugging Face model manager...")
                from modules.audio.huggingface_models import HuggingFaceModelManager
                
                # Make sure the app_dir path exists, use a fallback if not
                if not hasattr(self.audio_processor, 'app_dir'):
                    # Create a fallback path for models
                    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Models")
                else:
                    models_dir = os.path.join(self.audio_processor.app_dir, "Models")
                    
                os.makedirs(models_dir, exist_ok=True)
                self.audio_processor.hf_manager = HuggingFaceModelManager(models_dir)
                
                # Start async initialization
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    # Create a new event loop if there isn't one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Schedule initialization in background
                asyncio.run_coroutine_threadsafe(
                    self._initialize_hf_model_manager_async(),
                    loop
                )
                return False
            return True
        except Exception as e:
            logging.error(f"Error ensuring HF model manager: {e}")
            self.update_status("Failed to initialize models")
            return False

    async def _initialize_hf_model_manager_async(self):
        """Initialize the HF model manager asynchronously"""
        try:
            self.root.after(0, lambda: self.update_status("Initializing AI models..."))
            await self.audio_processor.hf_manager.initialize()
            self.audio_processor._hf_initialized = True
            self.root.after(0, lambda: self.update_status("AI models initialized"))
            
            # Update the model list after initialization
            self.root.after(0, self.update_hf_model_list)
        except Exception as e:
            logging.error(f"Error initializing HF model manager: {e}")
            self.root.after(0, lambda: self.update_status("Failed to initialize models"))

    def update_hf_model_list(self):
        """Update the list of available Hugging Face models"""
        try:
            # Check if the hf_manager exists before accessing it
            if not hasattr(self.audio_processor, 'hf_manager') or self.audio_processor.hf_manager is None:
                self.hf_model_selector['values'] = ['No models available']
                self.hf_model_selector.current(0)
                self.update_status("Hugging Face models not initialized")
                return

            # Set temporary loading state
            self.hf_model_selector['values'] = ['Loading models...']
            self.hf_model_selector.current(0)
            self.update_status("Loading model list...")

            # Run in async to avoid blocking
            try:
                # Get the current event loop or create a new one
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Set a timeout to ensure we don't hang forever if the async operation fails
                self.root.after(10000, self._model_loading_timeout)
                
                # Run the async task
                asyncio.run_coroutine_threadsafe(
                    self._update_hf_model_list_async(),
                    loop
                )
            except Exception as e:
                logging.error(f"Error updating HF model list: {e}")
                self.update_status("Failed to update model list")
                # Fallback to default models in case of error
                self._use_default_model_list()
        except Exception as e:
            logging.error(f"Error in update_hf_model_list: {e}")
            self.update_status("Failed to update model list")
            # Fallback to default models in case of error
            self._use_default_model_list()
    
    def _model_loading_timeout(self):
        """Handle timeout for model loading"""
        current = self.hf_model_selector.get()
        if current == 'Loading models...':
            self.update_status("Model loading timed out. Using default models.")
            self._use_default_model_list()
    
    def _use_default_model_list(self):
        """Fallback to display default models when loading fails"""
        try:
            default_models = [
                {"id": "microsoft/speecht5_tts", "name": "SpeechT5 TTS", "is_local": False},
                {"id": "facebook/mms-tts-eng", "name": "MMS TTS English", "is_local": False},
                {"id": "espnet/kan-bayashi_ljspeech_vits", "name": "LJSpeech VITS", "is_local": False}
            ]
            
            # If we can get models from the audio processor, use those instead
            if hasattr(self.audio_processor, 'get_huggingface_recommended_models'):
                recommended = self.audio_processor.get_huggingface_recommended_models()
                if recommended:
                    default_models = [{"id": m["id"], "name": m["id"], "is_local": False} for m in recommended]
            
            self._update_hf_model_selector(default_models)
        except Exception as e:
            logging.error(f"Error setting default model list: {e}")
            # Set some basic values directly to ensure the dropdown is usable
            self.hf_model_selector['values'] = [
                'microsoft/speecht5_tts (Available)',
                'facebook/mms-tts-eng (Available)',
                'espnet/kan-bayashi_ljspeech_vits (Available)'
            ]
            self.hf_model_selector.current(0)

    async def _update_hf_model_list_async(self):
        """Asynchronously update Hugging Face model list"""
        try:
            # Check if audio_processor has required methods and properties
            if (not hasattr(self.audio_processor, 'hf_manager') or 
                self.audio_processor.hf_manager is None):
                self.root.after(0, lambda: self.update_status("Hugging Face models not available"))
                self.root.after(0, self._use_default_model_list)
                return
                
            try:
                # First ensure manager is initialized
                if not getattr(self.audio_processor, '_hf_initialized', False):
                    try:
                        await self.audio_processor.hf_manager.initialize()
                        self.audio_processor._hf_initialized = True
                        self.root.after(0, lambda: self.update_status("Models initialized"))
                    except Exception as init_error:
                        logging.error(f"Failed to initialize model manager: {init_error}")
                        self.root.after(0, lambda: self.update_status("Failed to initialize models"))
                        self.root.after(0, self._use_default_model_list)
                        return

                # Get available voices/models
                try:
                    voices = await self.audio_processor.get_huggingface_voices()
                except Exception as voice_error:
                    logging.error(f"Error getting Hugging Face voices: {voice_error}")
                    voices = []
                
                # If no voices returned but manager initialized, try scanning local models
                if not voices and self.audio_processor._hf_initialized:
                    try:
                        await self.audio_processor.hf_manager.scan_local_models()
                        voices = await self.audio_processor.get_huggingface_voices()
                    except Exception as scan_error:
                        logging.error(f"Error scanning local models: {scan_error}")
                        voices = []
                    
                # Update model list on main thread
                if voices:
                    self.root.after(0, lambda: self._update_hf_model_selector(voices))
                else:
                    # Populate with default models if no models found
                    default_models = self.audio_processor.get_huggingface_recommended_models()
                    if default_models:
                        model_info = [{"name": m["id"], "is_local": False} for m in default_models]
                        self.root.after(0, lambda: self._update_hf_model_selector(model_info))
                    else:
                        # If we couldn't get any models, use fallback
                        self.root.after(0, self._use_default_model_list)
                    
            except AttributeError as ae:
                logging.error(f"Attribute error getting HF voices: {ae}")
                self.root.after(0, lambda: self.update_status("Failed to get voice attributes"))
                self.root.after(0, self._use_default_model_list)
            except Exception as e:
                logging.error(f"Error getting HF voices: {e}")
                self.root.after(0, lambda: self.update_status("Failed to get voices"))
                self.root.after(0, self._use_default_model_list)
        except Exception as e:
            logging.error(f"Error in async HF model update: {e}")
            self.root.after(0, lambda: self.update_status("Failed to get models"))
            self.root.after(0, self._use_default_model_list)

    def _update_hf_model_selector(self, voices):
        """Update the Hugging Face model selector with available models"""
        try:
            current = self.hf_model_selector.get()
            values = []
            
            if not voices or len(voices) == 0:
                self.hf_model_selector['values'] = ['No models available locally']
                self.hf_model_selector.current(0)
                self.update_status("No models found locally")
                return
            
            for voice in voices:
                try:
                    # Handle both full objects and simple dicts
                    name = voice.get('name', voice.get('id', 'Unknown Model'))
                    is_local = voice.get('is_local', False)
                    display_name = f"{name} ({'Local' if is_local else 'Not installed'})"
                    values.append(display_name)
                except Exception as e:
                    logging.error(f"Error processing voice entry: {e}")
                    # Skip this voice and continue
                    continue
            
            if not values:
                self.hf_model_selector['values'] = ['No models available locally']
                self.hf_model_selector.current(0)
                self.update_status("No valid models found locally")
                return
                
            # Update the dropdown values
            self.hf_model_selector['values'] = values
            
            # Select the current item or the first one
            if current and current in values:
                self.hf_model_selector.set(current)
            elif values:
                self.hf_model_selector.set(values[0])
                
            self.update_status(f"Model list updated - {len(values)} models available")
            
        except Exception as e:
            logging.error(f"Error updating model selector: {e}")
            self.update_status("Failed to update model selector")
            self._use_default_model_list()

    def download_hf_model(self):
        """No longer downloads models - shows installation instructions instead"""
        self.show_model_instructions()

    def show_model_instructions(self):
        """Show instructions for manually installing models"""
        try:
            selected = self.hf_model_selector.get()
            if not selected or selected in ['No models available', 'Loading models...', 'Error loading models']:
                messagebox.showwarning("No Model Selected", "Please select a model from the dropdown list.")
                return
            
            # Extract model ID from display name
            model_name = selected.split(" (")[0]  # Remove the status part
            
            if " (Local)" in selected:
                # Model is already local
                messagebox.showinfo("Already Installed", "This model is already available locally.")
                return
                
            # Check if the hf_manager exists
            if not hasattr(self.audio_processor, 'hf_manager') or self.audio_processor.hf_manager is None:
                messagebox.showerror("Error", "Hugging Face model manager not available")
                return
                
            # Get installation instructions
            instructions = self.audio_processor.hf_manager.get_model_installation_instructions(model_name)
            
            # Display instructions in a messagebox
            messagebox.showinfo(
                f"Installation Instructions for {model_name}", 
                instructions
            )
                
        except Exception as e:
            logging.error(f"Error showing model instructions: {e}")
            messagebox.showerror("Error", f"Failed to show model instructions: {e}")

    def _show_download_progress(self, show=True):
        """This method is no longer used since downloading is disabled"""
        pass

    def select_model_only(self, model_id):
        """Select a specific Hugging Face model"""
        try:
            # First ensure model manager is initialized
            if not self._ensure_hf_model_manager_initialized():
                self.update_status(f"Please wait for model manager to initialize... Will select {model_id} when ready.")
                self.root.after(1000, lambda mid=model_id: self.select_model_only(mid))
                return
                
            # First update the model list if needed
            if not self.hf_model_selector['values'] or self.hf_model_selector['values'][0] in ['No models available', 'Loading models...', 'Error loading models']:
                self.update_status(f"Refreshing model list before selecting {model_id}")
                self._use_default_model_list()
                # Try again after a delay
                self.root.after(500, lambda mid=model_id: self.select_model_only(mid))
                return
                
            # Find the display name for this model ID
            found = False
            for item in self.hf_model_selector['values']:
                # Check if the model_id is part of this item
                if model_id in item:
                    self.hf_model_selector.set(item)
                    found = True
                    self.update_status(f"Selected model: {model_id}")
                    break
                    
            if not found:
                # If not found in dropdowns, add it to the dropdown
                new_item = f"{model_id} (Available)"
                values = list(self.hf_model_selector['values']) + [new_item]
                self.hf_model_selector['values'] = values
                self.hf_model_selector.set(new_item)
                self.update_status(f"Added and selected model: {model_id}")
            
        except Exception as e:
            logging.error(f"Error selecting model: {e}")
            self.update_status(f"Failed to select model: {str(e)}")
            # Try to recover by using default models
            self._use_default_model_list()

    def select_hf_model(self, model_id):
        """Select a specific Hugging Face model"""
        # This method is kept for compatibility but now just calls select_model_only
        self.select_model_only(model_id)

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

    def handle_text_drop(self, event):
        try:
            # Remove curly braces and decode
            filepath = event.data.strip('{}')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    # Fix: using tts_text_area instead of text_area
                    self.tts_text_area.delete('1.0', tk.END)
                    self.tts_text_area.insert('1.0', f.read())
        except Exception as e:
            logging.error(f"Error handling text drop: {e}")
            self.update_status(f"Error loading dropped file: {e}")

    def load_text_file(self):
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filepath:
                with open(filepath, 'r', encoding='utf-8') as f:
                    # Fix: using tts_text_area instead of text_area
                    self.tts_text_area.delete('1.0', tk.END)
                    self.tts_text_area.insert('1.0', f.read())
                    self.update_status("Text file loaded")
        except Exception as e:
            logging.error(f"Error loading text file: {e}")
            messagebox.showerror("Error", f"Failed to load text file: {e}")

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

    async def start_text_to_speech(self):
        """Start text-to-speech conversion"""
        try:
            text = self.tts_text_area.get('1.0', tk.END).strip()
            if not text:
                messagebox.showwarning("Warning", "Please enter some text to convert")
                return

            # Get engine-specific settings
            engine_type = self.tts_engine.get()
            if engine_type == "local":
                voice_name = self.voice_selector.get()
            elif engine_type == "huggingface":
                voice_name = self.hf_model_selector.get()
                voices = await self.audio_processor.get_huggingface_voices()
                voice_name = next((v['id'] for v in voices if v['name'] == voice_name), None)
            else:  # google
                voice_name = None
                
            # Create output folder if it doesn't exist
            os.makedirs("Audio-Output", exist_ok=True)
            
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join("Audio-Output", f"tts_output_{timestamp}.wav")

            self.update_status("Converting text to speech...")
            self.preview_audio_path = output_path
            
            # Disable buttons during conversion
            self.tts_start_button.configure(state=tk.DISABLED)
            self.tts_cancel_button.configure(state=tk.NORMAL)
            
            # Start conversion in a thread
            self.cancel_flag = False
            threading.Thread(target=self._tts_thread,
                           args=(text, output_path, engine_type, voice_name)).start()

        except Exception as e:
            logging.error(f"Error starting text-to-speech conversion: {e}")
            self._tts_error(str(e))

    def _tts_thread(self, text, output_path, engine_type, voice_name):
        """Thread function for text-to-speech conversion"""
        try:
            # Get language setting for Google TTS
            lang = self.google_lang.get() if engine_type == "google" else None
            
            # Create async function for conversion
            async def convert():
                return await self.audio_processor.text_to_speech_async(
                    text, output_path, engine_type, voice_name, lang,
                    progress_callback=self.update_status
                )
            
            # Run conversion
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(convert())
            loop.close()
            
            if success and not self.cancel_flag:
                self.preview_audio_path = output_path
                self.root.after(0, self._tts_complete)
            else:
                self.root.after(0, lambda: self._tts_error("Conversion failed or was cancelled"))
                
        except Exception as e:
            logging.error(f"Error in TTS thread: {e}")
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
        try:
            if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
                messagebox.showwarning("Warning", "No audio file available to play")
                return

            if not self.audio_playing:
                self.audio_processor.play_audio(self.preview_audio_path)
                self.audio_playing = True
                self.play_button.configure(text="Stop")
                self.root.after(100, self._check_audio_playing)
            else:
                self.stop_audio()
                
        except Exception as e:
            logging.error(f"Error during audio playback: {e}", exc_info=True)
            messagebox.showerror("Playback Error", f"Failed to play audio: {e}")
            self._reset_play_button()

    def _check_audio_playing(self):
        if self.audio_playing and not self.audio_processor.is_playing():
            self._reset_play_button()
        elif self.audio_playing:
            self.root.after(100, self._check_audio_playing)

    def stop_audio(self):
        try:
            if self.audio_playing:
                self.audio_processor.stop_audio()
                self._reset_play_button()
        except Exception as e:
            logging.error(f"Error stopping audio: {e}")
            self._reset_play_button()

    def _reset_play_button(self):
        self.audio_playing = False
        self.play_button.configure(text="▶ Play")
        self.stop_button.configure(state=tk.DISABLED)

    def save_generated_audio(self):
        try:
            if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
                messagebox.showwarning("Warning", "No audio file available to save")
                return

            output_path = filedialog.asksaveasfilename(
                defaultextension=".wav",
                filetypes=[("Wave files", "*.wav")]
            )
            
            if output_path:
                import shutil
                shutil.copy2(self.preview_audio_path, output_path)
                self.update_status("Audio file saved successfully")
                
        except Exception as e:
            logging.error(f"Error saving audio file: {e}")
            messagebox.showerror("Save Error", f"Failed to save audio file: {e}")

    def clear_text(self):
        try:
            if messagebox.askyesno("Confirm", "Clear all text?"):
                # Fix: using tts_text_area instead of text_area
                self.tts_text_area.delete('1.0', tk.END)
                self.update_status("Text cleared")
        except Exception as e:
            logging.error(f"Error clearing text: {e}")

    def set_text(self, text):
        try:
            # Fix: using tts_text_area instead of text_area
            self.tts_text_area.delete('1.0', tk.END)
            self.tts_text_area.insert('1.0', text)
        except Exception as e:
            logging.error(f"Error setting text: {e}")
            messagebox.showerror("Error", f"Failed to set text: {e}")

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
        try:
            # Get current font properties
            # Fix: using tts_text_area instead of text_area
            current_font = self.tts_text_area.cget("font")
            if isinstance(current_font, str):
                font_family = current_font
                new_size = 10
            else:
                font_family = current_font[0]
                current_size = int(current_font[1])
                new_size = current_size

            # Adjust size based on event
            if event.delta > 0:
                new_size = min(new_size + 2, 24)  # Maximum size
            else:
                new_size = max(new_size - 2, 8)   # Minimum size

            # Apply new font size
            # Fix: using tts_text_area instead of text_area
            self.tts_text_area.configure(font=(font_family, new_size))
            self.current_font_size = new_size

        except Exception as e:
            logging.error(f"Error changing font size: {e}")

    def _show_model_selection(self):
        """Show dialog for model selection"""
        try:
            if not self.audio_processor._hf_initialized:
                messagebox.showinfo(
                    "Initialization Required",
                    "Hugging Face model manager is initializing. Please wait and try again."
                )
                return
                
            # Get recommended models
            recommended_models = self.audio_processor.get_huggingface_recommended_models()
            if not recommended_models:
                messagebox.showerror(
                    "Error",
                    "Failed to get recommended models. Please check your internet connection."
                )
                return
                
            # Create model selection dialog
            # ... rest of the existing dialog code ...
        except Exception as e:
            logging.error(f"Error showing model selection: {e}")
            messagebox.showerror("Error", f"Failed to show model selection: {e}")

    def update_voice_list(self):
        """Update the list of available voices for local TTS"""
        try:
            if not hasattr(self.audio_processor, 'get_available_voices'):
                self.voice_selector['values'] = ['No voices available']
                self.voice_selector.current(0)
                return
                
            voices = self.audio_processor.get_available_voices()
            
            if not voices:
                self.voice_selector['values'] = ['No voices available']
                self.voice_selector.current(0)
                return
                
            voice_names = []
            for voice in voices:
                if hasattr(voice, 'name'):
                    voice_names.append(voice.name)
                elif hasattr(voice, 'id'):
                    voice_names.append(voice.id)
                else:
                    voice_names.append(str(voice))
                    
            self.voice_selector['values'] = voice_names
            
            # Select first voice if available
            if voice_names:
                self.voice_selector.current(0)
                
        except Exception as e:
            logging.error(f"Error updating voice list: {e}")
            self.voice_selector['values'] = ['Error loading voices']
            self.voice_selector.current(0)

    def _download_timeout(self, model_name):
        """Handle timeouts during download"""
        # If the download button is still disabled, assume we're still in progress
        if self.download_button['state'] == 'disabled':
            # Ask the user if they want to cancel
            if messagebox.askyesno("Download Taking Too Long", 
                                f"The download for {model_name} seems to be taking a long time.\nWould you like to cancel?"):
                self._show_download_progress(False)
                self.update_status("Download cancelled by user due to timeout")
