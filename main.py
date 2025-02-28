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
from modules.gui import setup_styles, AppDimensions
from modules.gui.text_to_speech_tab import TextToSpeechTab
from modules.gui.settings_tab import SettingsTab
from modules.gui.tabs import SpeechToTextTab

# Global exception handler
def show_error_and_exit(error_type, value, tb):
    """Global error handler to show error dialog and exit gracefully"""
    error_msg = ''.join(traceback.format_exception(error_type, value, tb))
    logging.critical(f"Unhandled exception:\n{error_msg}")
    
    try:
        if tk._default_root and tk._default_root.winfo_exists():
            root = tk._default_root
            # Try to clean up audio if playing
            try:
                if hasattr(root, 'audio_processor'):
                    root.audio_processor.stop_audio()
            except:
                pass
            # Show error dialog
            messagebox.showerror(
                "Fatal Error",
                "A fatal error has occurred. The application will close.\n\n"
                f"Error: {str(value)}\n\n"
                "Check the log file for more details."
            )
            root.quit()
        else:
            print(f"Fatal error: {error_msg}", file=sys.stderr)
    except:
        print(f"Fatal error: {error_msg}", file=sys.stderr)
    finally:
        sys.exit(1)

class AudioToTextConverter:
    def __init__(self):
        # Create root window first - no styling or theme yet
        self.root = TkinterDnD.Tk()
        self.root.withdraw()  # Hide window during initialization
        self.root.title("Audio/Text Converter")
        
        # Basic configuration to prevent early theme errors
        self.style = ttk.Style()

        # Set up file paths and directories
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.dialogs_folder = os.path.join(self.app_dir, "Dialogs")
        self.transcribes_folder = os.path.join(self.app_dir, "Transcribes")
        os.makedirs(self.dialogs_folder, exist_ok=True)
        os.makedirs(self.transcribes_folder, exist_ok=True)
        
        # Create output folder for temporary files
        self.output_folder = os.path.join(self.app_dir, "output")
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Basic initialization first
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.dimensions = AppDimensions()
        self.config = ConfigManager(self.app_dir)
        self.audio_processor = None
        
        # Set up window size
        self.setup_window_geometry()
        
        # Now set up global exception handler
        sys.excepthook = show_error_and_exit
        
        # Continue with the rest of initialization safely
        self.root.after(100, self._delayed_init)

    def _delayed_init(self):
        """Complete initialization after window is fully created"""
        try:
            # Set up logging
            self.log_queue = queue.Queue()
            self.logger = setup_logging(self.log_queue)
            
            # Initialize audio processor
            self._setup_ffmpeg()
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
            logging.critical(f"Failed to complete initialization: {e}")
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize application: {str(e)}\n\nThe application will exit."
            )
            self.on_closing()

    def _setup_ffmpeg(self):
        """Set up FFmpeg configuration"""
        try:
            from pydub import AudioSegment
            ffmpeg_dir = os.path.join(self.app_dir, 'tools')
            ffmpeg_path = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
            ffprobe_path = os.path.join(ffmpeg_dir, 'ffprobe.exe')

            if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
                AudioSegment.converter = ffmpeg_path
                AudioSegment.ffmpeg = ffmpeg_path
                AudioSegment.ffprobe = ffprobe_path
                os.environ['PATH'] = os.pathsep.join([ffmpeg_dir, os.environ.get('PATH', '')])
                os.environ['FFMPEG_BINARY'] = ffmpeg_path
                os.environ['FFPROBE_BINARY'] = ffprobe_path
                logging.info(f"FFmpeg configured at: {ffmpeg_path}")
            else:
                self._show_ffmpeg_instructions()
        except Exception as e:
            logging.error(f"Error configuring FFmpeg: {e}")
            self._show_ffmpeg_instructions()

    def on_closing(self):
        """Handle application closing"""
        try:
            # Set a flag to indicate shutdown is in progress
            self.shutting_down = True
            
            # Stop any audio playback
            if hasattr(self, 'audio_processor') and self.audio_processor:
                try:
                    self.audio_processor.stop_audio()
                except Exception as e:
                    logging.error(f"Error stopping audio during shutdown: {e}")
                    pass
            
            # Save configuration
            if hasattr(self, 'config') and self.config:
                try:
                    self.config.save_config()
                except Exception as e:
                    logging.error(f"Error saving config during shutdown: {e}")
                    pass
            
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
                logging.error(f"Error cancelling pending callbacks: {e}")
            
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
            self.root.mainloop()
        except Exception as e:
            logging.critical(f"Fatal error in main loop: {e}")
            raise
        finally:
            self.on_closing()

if __name__ == "__main__":
    try:
        print("Starting application initialization...")
        # Initialize application
        app = AudioToTextConverter()
        print("Application initialized successfully")
        
        # Start the application
        print("Starting mainloop...")
        app.run()
    except Exception as e:
        import traceback
        print(f"\nCRITICAL ERROR: {e}")
        print("\nStacktrace:")
        traceback.print_exc()
        print("\nApplication will now exit.")
        sys.exit(1)