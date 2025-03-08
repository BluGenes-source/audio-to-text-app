import os
import logging
import queue
import sys
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
import asyncio

def init_tkinter_dnd():
    """Initialize TkinterDnD safely"""
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except ImportError:
        logging.error("TkinterDnD2 not found. Falling back to standard Tkinter")
        return tk.Tk()
    except Exception as e:
        logging.error(f"Error initializing TkinterDnD: {e}")
        return tk.Tk()

from modules.config import ConfigManager
from modules.audio import AudioProcessor, find_ffmpeg
from modules.utils import setup_logging
from modules.utils.error_handler import ErrorHandler, with_retry, RetryConfig
from modules.gui import setup_styles, AppDimensions
from modules.gui.text_to_speech_tab import TextToSpeechTab
from modules.gui.settings_tab import SettingsTab

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

# Create a new asyncio event loop for the main thread
def setup_asyncio_event_loop():
    try:
        # Use the new recommended approach to get or create event loops
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # If no running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except Exception as e:
        logging.error(f"Error setting up asyncio event loop: {e}")
        # Fallback to new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# Initialize asyncio for tkinter
setup_asyncio_event_loop()

class TextToSpeechConverter:
    def __init__(self):
        try:
            # Basic initialization first
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Initialize configuration first to get logs folder
            try:
                self.config = ConfigManager(self.app_dir)
                logging.info("Configuration manager initialized successfully")
            except Exception as config_error:
                # If config fails, use default logs folder
                logging.error(f"Failed to initialize ConfigManager: {config_error}")
                raise RuntimeError(f"Configuration initialization failed: {config_error}")

            # Set up logging to use config's logs folder
            log_file = os.path.join(self.config.logs_folder, 'text_to_speech.log')
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'))
            logging.root.addHandler(file_handler)
            logging.root.setLevel(logging.INFO)
            
            logging.info(f"Application directory: {self.app_dir}")
            
            # Initialize directories
            self._init_directories()
            
            # Initialize error handler before GUI
            self.error_handler = ErrorHandler(self.app_dir, self.config)
            sys._app_error_handler = self.error_handler
            logging.info("Error handler initialized")
            
            # Initialize GUI components
            self._init_gui()
            
            # Set up global exception handler
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

    def _init_directories(self):
        """Initialize required directories"""
        try:
            # We only need the output and audio output folders now
            self.output_folder = os.path.join(self.app_dir, "output")
            self.audio_output_folder = os.path.join(self.app_dir, "Audio-Output")
            
            for folder in [self.output_folder, self.audio_output_folder]:
                os.makedirs(folder, exist_ok=True)
            logging.info("Created required directories")
        except Exception as e:
            logging.error(f"Error creating directories: {e}")
            raise

    def _init_gui(self):
        """Initialize GUI components"""
        try:
            # Create root window with safe TkinterDnD initialization
            self.root = init_tkinter_dnd()
            self.root.withdraw()  # Hide window during initialization
            self.root.title(f"Text to Speech Converter v{self.config.version}")
            
            # Initialize status var early to prevent errors during startup
            self.status_var = tk.StringVar(value="Ready")
            
            # Basic configuration to prevent early theme errors
            self.style = ttk.Style()
            self.dimensions = AppDimensions()
            
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Initialize audio processor as None - will be set up in delayed init
            self.audio_processor = None
            
            # Set up initial window geometry
            self.setup_window_geometry()
            
            logging.info("GUI initialization complete")
        except Exception as e:
            logging.error(f"Error initializing GUI: {e}")
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
            self.logger = setup_logging(self.log_queue, self.config)
            
            # Initialize audio processor
            ffmpeg_path = self._setup_ffmpeg()
            self.audio_processor = AudioProcessor(self.output_folder)
            self.root.audio_processor = self.audio_processor
            
            # Ensure asyncio has a running event loop
            try:
                # Use the setup function defined above
                loop = setup_asyncio_event_loop()
                self.root.async_loop = loop  # Store reference
                logging.info("Asyncio event loop initialized")
            except Exception as e:
                logging.error(f"Failed to initialize asyncio event loop: {e}", exc_info=True)
                
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
            # Safely destroy the window and exit
            try:
                # Check if root window still exists and is not in destroyed state
                if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    self.root.quit()
                    self.root.destroy()
            except Exception as e:
                # Suppress errors during final cleanup
                pass
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
            # Text to Speech tab is now the main tab
            self.tts_frame = ttk.Frame(self.notebook)
            self.tts_tab = TextToSpeechTab(
                self.tts_frame,
                self.config,
                self.audio_processor,
                self._update_status,
                self.root
            )
            
            # Settings tab remains
            self.settings_frame = ttk.Frame(self.notebook)
            self.settings_tab = SettingsTab(
                self.settings_frame,
                self.config,
                self.update_styles
            )

            # Add tabs to notebook
            self.notebook.add(self.tts_frame, text="Text to Speech")
            self.notebook.add(self.settings_frame, text="Settings")
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
        
        title_label = ttk.Label(title_frame, text="Text to Speech Converter", 
                              style="Title.TLabel")
        title_label.grid(row=0, column=0)
        
        version_label = ttk.Label(title_frame,
                                text=f"Version {self.config.version}",
                                style="Version.TLabel")
        version_label.grid(row=0, column=1, padx=10)
        
        subtitle_label = ttk.Label(title_frame, 
                                 text="Convert text to speech using multiple engines",
                                 style="Subtitle.TLabel")
        subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 5))

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

    def _log_message(self, message):
        """Log a message to the application log"""
        logging.info(message)

    def check_log_queue(self):
        """Check for new log messages"""
        try:
            while True:
                try:
                    record = self.log_queue.get_nowait()
                    # Log to the status bar for important messages
                    self._update_status(record)
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
        # Initialize basic config manager to get logs folder
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config = ConfigManager(app_dir)
        
        # Set up logging to the logs folder
        log_file = os.path.join(config.logs_folder, 'text_to_speech.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Starting application initialization...")
        app = TextToSpeechConverter()
        logging.info("Application initialized successfully")
        app.run()
    except Exception as e:
        log_file = os.path.join(app_dir, 'logs', 'text_to_speech.log')  # Fallback to default logs folder
        logging.critical(f"CRITICAL ERROR: {e}\n{traceback.format_exc()}")
        print(f"\nCRITICAL ERROR: {e}")
        print("\nStacktrace:")
        traceback.print_exc()
        print("\nApplication will now exit.")
        
        # Try to show error dialog if possible
        try:
            messagebox.showerror("Fatal Error", 
                               f"Failed to initialize application: {str(e)}\n\nCheck {log_file} for details.")
        except:
            pass
            
        sys.exit(1)