import os
import json
import logging

class ConfigManager:
    """Manages application configuration settings"""
    
    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.config_file = os.path.join(app_dir, "config.json")
        
        # Default configuration values
        self.window_width = 900
        self.window_height = 700
        self.window_x = None
        self.window_y = None
        self.theme = "default"
        self.ffmpeg_path = None
        
        # Load configuration if exists
        self.load_config()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Update instance attributes from loaded config
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                logging.info("Configuration loaded successfully")
            else:
                logging.info("No configuration file found, using defaults")
                self.save_config()  # Save default configuration
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            config_data = {
                'window_width': self.window_width,
                'window_height': self.window_height,
                'window_x': self.window_x,
                'window_y': self.window_y,
                'theme': self.theme,
                'ffmpeg_path': self.ffmpeg_path,
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            
            logging.info("Configuration saved successfully")
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
