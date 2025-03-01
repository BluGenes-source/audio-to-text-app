import os
import json
import logging

class ConfigManager:
    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.config_file = os.path.join(app_dir, "config.json")
        self.theme = "light"
        self.voice = None
        self.queue_delay = 0.5
        self.window_width = None
        self.window_height = None
        self.window_x = None
        self.window_y = None
        
        try:
            self.load_config()
        except Exception as e:
            logging.error(f"Failed to load config: {e}", exc_info=True)
            self._set_defaults()
            try:
                self.save_config()
            except Exception as save_error:
                logging.error(f"Failed to save default config: {save_error}", exc_info=True)

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.theme = config.get('theme', self.theme)
                    self.voice = config.get('voice', self.voice)
                    self.queue_delay = config.get('queue_delay', self.queue_delay)
                    self.window_width = config.get('window_width', self.window_width)
                    self.window_height = config.get('window_height', self.window_height)
                    self.window_x = config.get('window_x', self.window_x)
                    self.window_y = config.get('window_y', self.window_y)
                    logging.info("Configuration loaded successfully")
            else:
                self._set_defaults()
                self.save_config()
        except Exception as e:
            logging.error(f"Error loading config file: {e}", exc_info=True)
            raise

    def save_config(self):
        try:
            config = {
                'theme': self.theme,
                'voice': self.voice,
                'queue_delay': self.queue_delay,
                'window_width': self.window_width,
                'window_height': self.window_height,
                'window_x': self.window_x,
                'window_y': self.window_y
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            logging.info("Configuration saved successfully")
        except Exception as e:
            logging.error(f"Error saving config file: {e}", exc_info=True)
            raise

    def _set_defaults(self):
        logging.info("Setting default configuration values")
        self.theme = "light"
        self.voice = None
        self.queue_delay = 0.5
        self.window_width = None
        self.window_height = None
        self.window_x = None
        self.window_y = None