from .styles import setup_styles, AppDimensions
from .settings_tab import SettingsTab
from tkinter import ttk

def setup_styles(config):
    """Set up ttk styles for the application"""
    style = ttk.Style()
    
    # Use system theme as a base
    if hasattr(config, 'theme') and config.theme != "default":
        try:
            style.theme_use(config.theme)
        except:
            # Fall back to default if theme not available
            pass
    
    # Configure styles for various elements
    style.configure("Title.TLabel", font=("Arial", 16, "bold"))
    style.configure("Subtitle.TLabel", font=("Arial", 10))
    style.configure("Status.TLabel", font=("Arial", 9))
    style.configure("Status.TFrame", relief="sunken")
    
    return style

class AppDimensions:
    """Store application dimension defaults"""
    def __init__(self):
        self.default_width = 900
        self.default_height = 650
        self.min_width = 600
        self.min_height = 400