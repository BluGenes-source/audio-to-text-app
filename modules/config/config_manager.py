import os
import json
import logging
from dataclasses import dataclass, asdict

@dataclass
class Config:
    # Window settings
    window_width: int = 1000
    window_height: int = 700
    window_x: int = 0
    window_y: int = 0
    
    # Theme settings
    theme: str = 'light'
    
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
        self._config = self._load_config()
        # Ensure folders are set
        self._ensure_folders_exist()
        
    def _load_config(self) -> Config:
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    return Config(**config_data)
            else:
                config = Config()
                self._set_default_paths(config)
                self.save_config()
                return config
                
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            config = Config()
            self._set_default_paths(config)
            return config
            
    def _set_default_paths(self, config: Config):
        """Set default paths relative to app directory"""
        config.input_folder = os.path.join(self.app_dir, "Audio-Input")
        config.transcribes_folder = os.path.join(self.app_dir, "Transcribes")
        config.dialogs_folder = os.path.join(self.app_dir, "Dialogs")
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
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self._config), f, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            
    def __getattr__(self, name):
        """Allow direct access to config properties"""
        if hasattr(self._config, name):
            return getattr(self._config, name)
        raise AttributeError(f"'ConfigManager' has no attribute '{name}'")
        
    def __setattr__(self, name, value):
        """Allow setting config properties directly"""
        if name in ['app_dir', 'config_file', '_config']:
            super().__setattr__(name, value)
        elif hasattr(Config, name):
            if not hasattr(self, '_config'):
                super().__setattr__('_config', Config())
            setattr(self._config, name, value)
        else:
            super().__setattr__(name, value)