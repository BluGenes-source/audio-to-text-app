from tkinter import ttk
from dataclasses import dataclass

@dataclass
class ThemeColors:
    # Light theme colors
    LIGHT_BG = "#f0f0f0"
    LIGHT_FG = "#000000"
    LIGHT_INPUT_BG = "#ffffff"
    LIGHT_INPUT_FG = "#000000"
    LIGHT_ACCENT = "#0078d7"
    LIGHT_ACCENT_HOVER = "#1982d7"
    LIGHT_DISABLED = "#e0e0e0"
    LIGHT_SELECTION_BG = "#cce8ff"
    LIGHT_SELECTION_FG = "#000000"
    
    # Dark theme colors
    DARK_BG = "#2d2d2d"
    DARK_FG = "#ffffff"
    DARK_INPUT_BG = "#3d3d3d"
    DARK_INPUT_FG = "#ffffff"
    DARK_ACCENT = "#0078d7"
    DARK_ACCENT_HOVER = "#1982d7"
    DARK_DISABLED = "#404040"
    DARK_SELECTION_BG = "#094771"
    DARK_SELECTION_FG = "#ffffff"
    
    def __init__(self, is_dark: bool = False):
        self.bg = self.DARK_BG if is_dark else self.LIGHT_BG
        self.fg = self.DARK_FG if is_dark else self.LIGHT_FG
        self.input_bg = self.DARK_INPUT_BG if is_dark else self.LIGHT_INPUT_BG
        self.input_fg = self.DARK_INPUT_FG if is_dark else self.LIGHT_INPUT_FG
        self.accent = self.DARK_ACCENT if is_dark else self.LIGHT_ACCENT
        self.accent_hover = self.DARK_ACCENT_HOVER if is_dark else self.LIGHT_ACCENT_HOVER
        self.disabled = self.DARK_DISABLED if is_dark else self.LIGHT_DISABLED
        self.selection_bg = self.DARK_SELECTION_BG if is_dark else self.LIGHT_SELECTION_BG
        self.selection_fg = self.DARK_SELECTION_FG if is_dark else self.LIGHT_SELECTION_FG

class AppDimensions:
    def __init__(self):
        self.default_width = 1000
        self.default_height = 700
        self.min_width = 800
        self.min_height = 500
        
def setup_styles(config):
    """Configure application styles"""
    style = ttk.Style()
    
    # Determine if dark theme is enabled
    is_dark = getattr(config, 'theme', 'light') == 'dark'
    theme = ThemeColors(is_dark)
    
    # Configure basic styles
    style.configure('TFrame', background=theme.bg)
    style.configure('TLabelframe', background=theme.bg)
    style.configure('TLabelframe.Label', background=theme.bg, foreground=theme.fg)
    style.configure('TLabel', background=theme.bg, foreground=theme.fg)
    style.configure('TButton', padding=5)
    
    # Title styles
    style.configure('Title.TLabel',
                   font=('Helvetica', 16, 'bold'),
                   background=theme.bg,
                   foreground=theme.fg)
    
    style.configure('Subtitle.TLabel',
                   font=('Helvetica', 10),
                   background=theme.bg,
                   foreground=theme.fg)
    
    # Group styles
    style.configure('Group.TLabelframe',
                   background=theme.bg,
                   foreground=theme.fg)
    
    style.configure('Group.TLabelframe.Label',
                   font=('Helvetica', 10),
                   background=theme.bg,
                   foreground=theme.fg)
    
    # Path label style
    style.configure('Path.TLabel',
                   background=theme.input_bg,
                   foreground=theme.input_fg,
                   padding=5)
    
    # Status bar style
    style.configure('Status.TFrame',
                   background=theme.bg)
    style.configure('Status.TLabel',
                   background=theme.bg,
                   foreground=theme.fg,
                   padding=5)
    
    # Action button styles
    style.configure('Action.TButton',
                   background=theme.accent,
                   padding=5)
    
    style.configure('Action.Ready.TButton',
                   background=theme.accent,
                   foreground=theme.fg)
    
    style.configure('Action.Inactive.TButton',
                   background=theme.disabled,
                   foreground=theme.fg)
    
    style.configure('Cancel.TButton',
                   padding=5,
                   background='#d32f2f')
    
    # Queue-specific button styles
    style.configure('Queue.Control.TButton',
                   padding=5,
                   background=theme.accent,
                   foreground=theme.fg)
                   
    style.configure('Queue.Process.TButton',
                   padding=5,
                   background=theme.accent,
                   foreground=theme.fg)
                   
    style.configure('Queue.Process.Inactive.TButton',
                   background=theme.disabled,
                   foreground=theme.fg)
                   
    style.configure('Queue.Process.Ready.TButton',
                   background=theme.accent,
                   foreground=theme.fg)
    
    # Map styles for button states
    style.map('Queue.Control.TButton',
             background=[('active', theme.accent_hover),
                        ('disabled', theme.disabled)],
             foreground=[('disabled', theme.fg)])
             
    style.map('Queue.Process.TButton',
             background=[('active', theme.accent_hover),
                        ('disabled', theme.disabled)],
             foreground=[('disabled', theme.fg)])
    
    return style