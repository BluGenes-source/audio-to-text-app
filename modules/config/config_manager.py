import os
import json

class ConfigManager:
    def __init__(self, app_dir):
        self.config_file = os.path.join(app_dir, "config.json")
        self.app_dir = app_dir
        self.default_output = os.path.join(app_dir, "output")
        self.transcribes_folder = os.path.join(app_dir, "Transcribes")
        self.dialogs_folder = os.path.join(app_dir, "Dialogs")
        
        # Window settings
        self.window_width = None
        self.window_height = None
        self.window_x = None
        self.window_y = None
        
        # Folder settings
        self.input_folder = ""
        self.output_folder = self.default_output
        
        # Visual settings
        self.theme = "light"
        self.font_family = "Helvetica"
        self.font_size = 10
        self.accent_color = "#2962ff"
        self.text_color = "#000000"
        self.button_inactive_color = "#cccccc"
        self.button_ready_color = "#2962ff"
        self.button_success_color = "#4caf50"
        self.disabled_color = "#e0e0e0"
        
        self.load_config()

    def load_config(self):
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Window settings
                self.input_folder = config.get('input_folder', "")
                self.output_folder = config.get('output_folder', self.default_output)
                self.window_width = config.get('window_width', None)
                self.window_height = config.get('window_height', None)
                self.window_x = config.get('window_x', None)
                self.window_y = config.get('window_y', None)
                
                # Visual settings
                self.theme = config.get('theme', "light")
                self.font_family = config.get('font_family', "Helvetica")
                self.font_size = config.get('font_size', 10)
                self.accent_color = config.get('accent_color', "#2962ff")
                self.text_color = config.get('text_color', "#000000")
                self.button_inactive_color = config.get('button_inactive_color', '#cccccc')
                self.button_ready_color = config.get('button_ready_color', '#2962ff')
                self.button_success_color = config.get('button_success_color', '#4caf50')
                self.disabled_color = config.get('disabled_color', '#e0e0e0')
            except:
                self._set_defaults()
        else:
            self._set_defaults()
        
        # Ensure folders exist
        os.makedirs(self.transcribes_folder, exist_ok=True)
        os.makedirs(self.dialogs_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

    def save_config(self):
        """Save configuration to JSON file"""
        config = {
            'input_folder': self.input_folder,
            'output_folder': self.output_folder,
            'window_width': self.window_width,
            'window_height': self.window_height,
            'window_x': self.window_x,
            'window_y': self.window_y,
            'theme': self.theme,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'accent_color': self.accent_color,
            'text_color': self.text_color,
            'button_inactive_color': self.button_inactive_color,
            'button_ready_color': self.button_ready_color,
            'button_success_color': self.button_success_color,
            'disabled_color': self.disabled_color
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _set_defaults(self):
        """Set default configuration values"""
        self.input_folder = ""
        self.output_folder = self.default_output
        self.theme = "light"
        self.font_family = "Helvetica"
        self.font_size = 10
        self.accent_color = "#2962ff"
        self.text_color = "#000000"
        self.button_inactive_color = "#cccccc"
        self.button_ready_color = "#2962ff"
        self.button_success_color = "#4caf50"
        self.disabled_color = "#e0e0e0"