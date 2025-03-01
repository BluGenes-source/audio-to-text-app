import os
import logging
import queue
import sys
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import TkinterDnD
from modules.config import ConfigManager
from modules.audio import AudioProcessor, find_ffmpeg
from modules.utils import setup_logging
from modules.utils.error_handler import ErrorHandler, with_retry, RetryConfig
from modules.gui import setup_styles, AppDimensions
from modules.gui.text_to_speech_tab import TextToSpeechTab
from modules.gui.settings_tab import SettingsTab
from modules.gui.tabs import SpeechToTextTab

def show_error_and_exit(error_type, value, tb):
    """Global error handler to show error dialog and exit gracefully"""
    error_msg = f"An unhandled error occurred:\n\n{value}\n\nThe application will exit."
    try:
        error_details = f"Fatal error: {error_type.__name__}: {value}\n{''.join(traceback.format_tb(tb))}"
        logging.critical(error_details)
        if hasattr(sys, '_app_error_handler'):
            sys._app_error_handler.handle_error(value, {
                'error_type': str(error_type.__name__),
                'traceback': ''.join(traceback.format_tb(tb)),
                'component': 'global_handler'
            })
    except Exception as inner_error:
        logging.critical(f"Error in error handler: {inner_error}")
        print(f"Error in error handler: {inner_error}")
    
    messagebox.showerror("Fatal Error", error_msg)
    sys.exit(1)

class AudioToTextConverter:
    def __init__(self):
        try:
            # Set up logging first, before anything else
            logging.basicConfig(
                filename='audio_converter.log',
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                encoding='utf-8'
            )
            logging.info("Starting application initialization...")

            # Create root window first - no styling or theme yet
            self.root = TkinterDnD.Tk()
            self.root.withdraw()  # Hide window during initialization
            self.root.title("Audio/Text Converter")
            
            # Basic configuration to prevent early theme errors
            self.style = ttk.Style()

            # Set up file paths and directories
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            logging.info(f"Application directory: {self.app_dir}")
            
            self.dialogs_folder = os.path.join(self.app_dir, "Dialogs")
            self.transcribes_folder = os.path.join(self.app_dir, "Transcribes")
            os.makedirs(self.dialogs_folder, exist_ok=True)
            os.makedirs(self.transcribes_folder, exist_ok=True)
            logging.info("Created required directories")
            
            # Create output folder for temporary files
            self.output_folder = os.path.join(self.app_dir, "output")
            os.makedirs(self.output_folder, exist_ok=True)
            
            # Initialize error handler
            self.error_handler = ErrorHandler(self.app_dir)
            sys._app_error_handler = self.error_handler  # Make available to global handler
            logging.info("Error handler initialized")
            
            # Basic initialization first
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.dimensions = AppDimensions()
            
            try:
                self.config = ConfigManager(self.app_dir)
                logging.info("Configuration manager initialized successfully")
            except Exception as config_error:
                error_details = f"Failed to initialize ConfigManager: {config_error}\n{traceback.format_exc()}"
                logging.error(error_details)
                self.error_handler.handle_error(config_error, {
                    'context': 'init_config',
                    'component': 'ConfigManager'
                })
                raise RuntimeError(f"Configuration initialization failed: {config_error}")
            
            self.audio_processor = None
            
            # Set up window size
            self.setup_window_geometry()
            
            # Now set up global exception handler
            sys.excepthook = show_error_and_exit
            
            # Continue with the rest of initialization safely
            self.root.after(100, self._delayed_init)
            
        except Exception as e:
            error_details = f"Failed to initialize application: {e}\n{traceback.format_exc()}"
            logging.critical(error_details)
            if hasattr(self, 'error_handler'):
                self.error_handler.handle_error(e, {
                    'context': 'application_init',
                    'component': '__init__'
                })
            raise

    @with_retry(RetryConfig(max_retries=2, delay=1.0))
    def _setup_ffmpeg(self):
        """Set up FFmpeg configuration with retry"""
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self._show_ffmpeg_instructions()
            raise RuntimeError("FFmpeg not found")
        return ffmpeg_path

    def _delayed_init(self):
        """Complete initialization after window is fully created"""
        try:
            # Set up logging
            self.log_queue = queue.Queue()
            self.logger = setup_logging(self.log_queue)
            
            # Initialize audio processor
            ffmpeg_path = self._setup_ffmpeg()
            self.audio_processor = AudioProcessor(self.output_folder)
            self.root.audio_processor = self.audio_processor
            
            # Set up styles and GUI
            self.setup_styles()
            self.setup_gui()
            
            # Bind window events
            self.root.bind('<Configure>', self._on_window_configure)
            
            # Show the window
            self.root.deiconify()
            
            # Start log queue checker
            self.check_log_queue()
            
            # Log startup
            logging.info("Application initialization complete")
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'context': 'application_init',
                'component': '_delayed_init'
            })
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize application: {str(e)}\n\nThe application will exit."
            )
            self.on_closing()

    def on_closing(self):
        """Handle application closing"""
        try:
            # Set a flag to indicate shutdown is in progress
            self.shutting_down = True
            
            # Stop any audio playback and cleanup
            if hasattr(self, 'audio_processor') and self.audio_processor:
                try:
                    self.audio_processor.stop_audio()
                    self.audio_processor.cleanup()
                except Exception as e:
                    self.error_handler.handle_error(e, {'context': 'shutdown_audio'})
            
            # Save configuration
            if hasattr(self, 'config') and self.config:
                try:
                    self.config.save_config()
                except Exception as e:
                    self.error_handler.handle_error(e, {'context': 'save_config'})
            
            # Clean up logging
            try:
                logging.info("Application shutting down normally")
                logging.shutdown()
            except Exception as e:
                print(f"Error shutting down logging: {e}")
            
            # Cancel any pending callbacks
            try:
                for after_id in self.root.tk.call('after', 'info'):
                    self.root.after_cancel(after_id)
            except Exception as e:
                self.error_handler.handle_error(e, {'context': 'cancel_callbacks'})
                
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            # Destroy the window and exit
            try:
                self.root.quit()
                self.root.destroy()
            except Exception as e:
                print(f"Error destroying window: {e}")
            sys.exit(0)

    def setup_styles(self):
        """Configure application styles"""
        # Use a try/except block to catch theme errors
        try:
            self.style = setup_styles(self.config)
        except Exception as e:
            logging.error(f"Error setting up styles: {e}")
            # Fall back to default style
            self.style = ttk.Style()

    def setup_window_geometry(self):
        """Set up initial window size and position"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = self.config.window_width or self.dimensions.default_width
        window_height = self.config.window_height or self.dimensions.default_height
        
        # Ensure window fits on screen
        window_width = min(window_width, screen_width - 100)
        window_height = min(window_height, screen_height - 100)
        
        # Center window if no position saved
        if (self.config.window_x is not None and self.config.window_y is not None):
            x = max(0, min(self.config.window_x, screen_width - window_width))
            y = max(0, min(self.config.window_y, screen_height - window_height))
        else:
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(self.dimensions.min_width, window_height - 150)

    def setup_gui(self):
        """Set up the main GUI components"""
        # Main container
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Title section
        self._setup_title(main_frame)
        
        # Tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky="nsew")
        
        # Create tabs
        try:
            self.tts_tab = TextToSpeechTab(
                ttk.Frame(self.notebook),
                self.config,
                self.audio_processor,
                self._update_status,
                self.root
            )
            self.stt_tab = SpeechToTextTab(
                ttk.Frame(self.notebook),
                self.config,
                self.audio_processor,
                self._append_terminal,
                self.root
            )
            self.settings_tab = SettingsTab(
                ttk.Frame(self.notebook),
                self.config,
                self.update_styles
            )

            # Connect STT tab to TTS tab
            self.stt_tab.tts_tab = self.tts_tab
            
            # Add tabs to notebook
            self.notebook.add(self.stt_tab.parent, text="Speech to Text")
            self.notebook.add(self.tts_tab.parent, text="Text to Speech")
            self.notebook.add(self.settings_tab.parent, text="Settings")
        except Exception as e:
            logging.critical(f"Failed to create tabs: {e}")
            raise
        
        # Status bar
        self._setup_status_bar()
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

    def update_styles(self):
        """Update application styles based on current configuration"""
        try:
            self.style = setup_styles(self.config)
            self._update_status("Theme updated")
            self.config.save_config()
        except Exception as e:
            logging.error(f"Error updating styles: {e}")
            self._update_status("Failed to update theme")

    def _setup_title(self, parent):
        """Set up the title section"""
        title_frame = ttk.Frame(parent)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="ew")
        title_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(title_frame, text="Audio/Text Converter", 
                              style="Title.TLabel")
        title_label.grid(row=0, column=0)
        
        subtitle_label = ttk.Label(title_frame, 
                                 text="Convert between audio and text using speech recognition",
                                 style="Subtitle.TLabel")
        subtitle_label.grid(row=1, column=0, pady=(0, 5))

    def _setup_status_bar(self):
        """Set up the status bar"""
        self.status_frame = ttk.Frame(self.root, style="Status.TFrame")
        self.status_frame.grid(row=1, column=0, sticky="ew")
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var,
                                    style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.status_frame.columnconfigure(0, weight=1)

    def _update_status(self, message):
        """Update status bar message"""
        try:
            self.status_var.set(message)
        except Exception as e:
            logging.error(f"Error updating status: {e}")

    def _append_terminal(self, message):
        """Append message to terminal area"""
        try:
            terminal = self.stt_tab.terminal_area
            terminal.configure(state='normal')
            terminal.insert(tk.END, message + '\n')
            terminal.see(tk.END)
            terminal.configure(state='disabled')
        except Exception as e:
            logging.error(f"Error appending to terminal: {e}")

    def check_log_queue(self):
        """Check for new log messages"""
        try:
            while True:
                try:
                    record = self.log_queue.get_nowait()
                    self._append_terminal(record)
                except queue.Empty:
                    break
            self.root.after(100, self.check_log_queue)
        except Exception as e:
            logging.error(f"Error in log queue checker: {e}")
            # Try to reschedule
            self.root.after(1000, self.check_log_queue)

    def _on_window_configure(self, event):
        """Handle window configuration changes"""
        if event.widget == self.root:
            try:
                geometry = self.root.geometry()
                try:
                    size_pos = geometry.replace('x', '+').split('+')
                    self.config.window_width = int(size_pos[0])
                    self.config.window_height = int(size_pos[1])
                    self.config.window_x = int(size_pos[2])
                    self.config.window_y = int(size_pos[3])
                    
                    if hasattr(self, '_save_config_id'):
                        self.root.after_cancel(self._save_config_id)
                    self._save_config_id = self.root.after(1000, self.config.save_config)
                except (ValueError, IndexError):
                    pass
            except Exception as e:
                logging.error(f"Error handling window configuration: {e}")

    def _show_ffmpeg_instructions(self):
        """Show FFmpeg installation instructions"""
        try:
            from tkinter import messagebox
            import webbrowser
            
            msg = """FFmpeg tools are required but not found. Please install them:

1. Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z
2. Extract the archive
3. Copy BOTH ffmpeg.exe AND ffprobe.exe from the bin folder to:
   - The 'tools' folder in this app's directory
   
Note: Both executables are required for proper audio processing.
Would you like to open the download page now?"""
            
            if messagebox.askyesno("FFmpeg Required", msg):
                webbrowser.open("https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z")
        except Exception as e:
            logging.error(f"Error showing FFmpeg instructions: {e}")

    def run(self):
        """Start the application"""
        try:
            logging.info("Starting main application loop")
            self.root.mainloop()
        except Exception as e:
            logging.critical(f"Fatal error in main loop: {e}\n{traceback.format_exc()}")
            raise
        finally:
            logging.info("Application shutting down")
            self.on_closing()

if __name__ == "__main__":
    try:
        logging.basicConfig(
            filename='audio_converter.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Starting application initialization...")
        app = AudioToTextConverter()
        logging.info("Application initialized successfully")
        app.run()
    except Exception as e:
        logging.critical(f"CRITICAL ERROR: {e}\n{traceback.format_exc()}")
        print(f"\nCRITICAL ERROR: {e}")
        print("\nStacktrace:")
        traceback.print_exc()
        print("\nApplication will now exit.")
        
        # Try to show error dialog if possible
        try:
            messagebox.showerror("Fatal Error", 
                               f"Failed to initialize application: {str(e)}\n\nCheck audio_converter.log for details.")
        except:
            pass
            
        sys.exit(1)