import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional

@dataclass
class Config:
    # Window settings
    window_width: int = 1000
    window_height: int = 700
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    
    # Theme settings
    theme: str = 'light'
    font_family: str = "Arial"
    accent_color: str = "#0078d7"
    
    # Color settings
    text_color: str = "#000000"  # Default black text color
    bg_color: str = "#f0f0f0"    # Default light background
    color: str = "#0078d7"       # Default accent color (same as accent_color)
    button_inactive: str = "#e0e0e0"  # Color for inactive buttons
    button_inactive_color: str = "#e0e0e0"  # Another reference to inactive button color
    button_ready_color: str = "#0078d7"  # Color for ready buttons
    button_success_color: str = "#4caf50"  # Color for success buttons
    disabled_color: str = "#cccccc"  # Color for disabled elements
    
    # Font sizes
    title_font_size: int = 16
    subtitle_font_size: int = 10
    text_font_size: int = 10
    font_size: int = 10  # Default font size for general text
    
    # Audio settings
    default_voice: str = ""
    short_pause_length: str = "400"
    long_pause_length: str = "800"
    pause_marker: str = "|"
    queue_delay: int = 1  # Delay between processing queue items (seconds)
    
    # Folders
    input_folder: str = ""
    transcribes_folder: str = ""
    dialogs_folder: str = ""
    output_folder: str = ""

class ConfigManager:
    def __init__(self, app_dir: str):
        self.app_dir = app_dir
        self.config_file = os.path.join(app_dir, 'config.json')
        # Initialize config before setting attributes to avoid initialization errors
        self._config = None
        self._config = self._load_config()
        # Ensure folders are set
        self._ensure_folders_exist()
        logging.info(f"Configuration loaded from {self.config_file}")
    
    # Explicitly define properties for all Config attributes to ensure proper access
    @property
    def theme(self):
        return self._config.theme
    
    @theme.setter
    def theme(self, value):
        self._config.theme = value
    
    @property
    def font_family(self):
        return self._config.font_family
    
    @font_family.setter
    def font_family(self, value):
        self._config.font_family = value
    
    @property
    def accent_color(self):
        return self._config.accent_color
    
    @accent_color.setter
    def accent_color(self, value):
        self._config.accent_color = value
    
    @property
    def text_color(self):
        return self._config.text_color
    
    @text_color.setter
    def text_color(self, value):
        self._config.text_color = value
    
    @property
    def bg_color(self):
        return self._config.bg_color
    
    @bg_color.setter
    def bg_color(self, value):
        self._config.bg_color = value
    
    @property
    def button_inactive_color(self):
        return self._config.button_inactive_color
    
    @button_inactive_color.setter
    def button_inactive_color(self, value):
        self._config.button_inactive_color = value
    
    @property
    def button_ready_color(self):
        return self._config.button_ready_color
    
    @button_ready_color.setter
    def button_ready_color(self, value):
        self._config.button_ready_color = value
    
    @property
    def button_success_color(self):
        return self._config.button_success_color
    
    @button_success_color.setter
    def button_success_color(self, value):
        self._config.button_success_color = value
    
    @property
    def disabled_color(self):
        return self._config.disabled_color
        
    @disabled_color.setter
    def disabled_color(self, value):
        self._config.disabled_color = value
    
    @property
    def title_font_size(self):
        return self._config.title_font_size
    
    @title_font_size.setter
    def title_font_size(self, value):
        self._config.title_font_size = value
    
    @property
    def subtitle_font_size(self):
        return self._config.subtitle_font_size
    
    @subtitle_font_size.setter
    def subtitle_font_size(self, value):
        self._config.subtitle_font_size = value
    
    @property
    def text_font_size(self):
        return self._config.text_font_size
    
    @text_font_size.setter
    def text_font_size(self, value):
        self._config.text_font_size = value
    
    @property
    def font_size(self):
        return self._config.font_size
    
    @font_size.setter
    def font_size(self, value):
        self._config.font_size = value
    
    @property
    def input_folder(self):
        return self._config.input_folder
    
    @input_folder.setter
    def input_folder(self, value):
        self._config.input_folder = value
    
    @property
    def transcribes_folder(self):
        return self._config.transcribes_folder
    
    @transcribes_folder.setter
    def transcribes_folder(self, value):
        self._config.transcribes_folder = value
    
    @property
    def dialogs_folder(self):
        return self._config.dialogs_folder
    
    @dialogs_folder.setter
    def dialogs_folder(self, value):
        self._config.dialogs_folder = value
    
    @property
    def output_folder(self):
        return self._config.output_folder
    
    @output_folder.setter
    def output_folder(self, value):
        self._config.output_folder = value
    
    @property
    def window_width(self):
        return self._config.window_width
    
    @window_width.setter
    def window_width(self, value):
        self._config.window_width = value
    
    @property
    def window_height(self):
        return self._config.window_height
    
    @window_height.setter
    def window_height(self, value):
        self._config.window_height = value
    
    @property
    def window_x(self):
        return self._config.window_x
    
    @window_x.setter
    def window_x(self, value):
        self._config.window_x = value
    
    @property
    def window_y(self):
        return self._config.window_y
    
    @window_y.setter
    def window_y(self, value):
        self._config.window_y = value
    
    @property
    def queue_delay(self):
        return self._config.queue_delay
    
    @queue_delay.setter
    def queue_delay(self, value):
        self._config.queue_delay = value
    
    def _load_config(self) -> Config:
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    # Create config with defaults first, then update with loaded values
                    # This ensures any new attributes added to Config class are initialized
                    config = Config()
                    for key, value in config_data.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                    logging.debug(f"Loaded config from file: {self.config_file}")
                    self._set_default_paths(config)
                    return config
            else:
                logging.info(f"Config file not found, creating default at: {self.config_file}")
                config = Config()
                self._set_default_paths(config)
                self.save_config(config)
                return config
                
        except Exception as e:
            logging.error(f"Error loading config: {e}", exc_info=True)
            logging.info("Falling back to default configuration")
            config = Config()
            self._set_default_paths(config)
            return config
            
    def _set_default_paths(self, config: Config):
        """Set default paths relative to app directory"""
        # Only set paths if they're empty
        if not config.input_folder:
            config.input_folder = os.path.join(self.app_dir, "Audio-Input")
        if not config.transcribes_folder:
            config.transcribes_folder = os.path.join(self.app_dir, "Transcribes")
        if not config.dialogs_folder:
            config.dialogs_folder = os.path.join(self.app_dir, "Dialogs")
        if not config.output_folder:
            config.output_folder = os.path.join(self.app_dir, "output")
        
    def _ensure_folders_exist(self):
        """Ensure all required folders exist"""
        folders = [
            self._config.input_folder,
            self._config.transcribes_folder,
            self._config.dialogs_folder,
            self._config.output_folder
        ]
        for folder in folders:
            if folder and not os.path.exists(folder):
                try:
                    os.makedirs(folder)
                    logging.info(f"Created directory: {folder}")
                except Exception as e:
                    logging.error(f"Error creating directory {folder}: {e}")
    
    def save_config(self, config=None):
        """Save current configuration to file"""
        if config is None:
            config = self._config
            
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(config), f, indent=4)
                logging.debug(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logging.error(f"Error saving config: {e}")