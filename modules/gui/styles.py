from tkinter import ttk

class ThemeColors:
    def __init__(self, is_dark=False, config=None):
        # Colors for dark theme
        if is_dark:
            self.bg = "#2d2d2d"
            self.fg = "#e0e0e0"
            self.input_bg = "#3c3c3c"
            self.input_fg = "#ffffff"
            self.selection_bg = "#505050"
            self.selection_fg = "#ffffff"
            self.button_bg = "#505050"
            self.button_fg = "#e0e0e0"
            self.accent = config.accent_color if config else "#2962ff"
            # Button text color - always black for better readability on colored buttons
            self.button_text = "#000000"
        # Colors for light theme
        else:
            self.bg = "#f5f5f5"
            self.fg = "#333333"
            self.input_bg = "#ffffff"
            self.input_fg = "#000000"
            self.selection_bg = "#4a90e2"
            self.selection_fg = "#ffffff"
            self.button_bg = "#e0e0e0"
            self.button_fg = "#333333"
            self.accent = config.accent_color if config else "#2962ff"
            # Button text color - always black for better readability on colored buttons
            self.button_text = "#000000"

def setup_styles(config=None):
    """Configure custom ttk styles for the application"""
    try:
        style = ttk.Style()
        
        # Get theme colors based on current theme setting
        is_dark = config and config.theme == "dark"
        theme = ThemeColors(is_dark, config)
        
        # Use custom colors if provided in config
        accent_color = config.accent_color if config else "#2962ff"
        text_color = config.text_color if config else theme.fg
        
        # Use a safer approach to set theme
        try:
            style.theme_use('default')
        except Exception as e:
            import logging
            logging.warning(f"Could not set theme: {e}")
        
        # Configure general styles
        style.configure(".",
                       background=theme.bg,
                       foreground=text_color,
                       font=(config.font_family if config else 'Helvetica', 
                            config.font_size if config else 10))
        
        # Frame styles
        style.configure("TFrame", background=theme.bg)
        style.configure("Status.TFrame", background=theme.accent)
        
        # Label styles
        style.configure("TLabel", background=theme.bg, foreground=text_color)
        style.configure("Title.TLabel", 
                       font=(config.font_family if config else 'Helvetica', 
                             18, 'bold'), 
                       foreground=accent_color)
        style.configure("Subtitle.TLabel", 
                       font=(config.font_family if config else 'Helvetica', 
                             11, 'italic'))
        style.configure("Status.TLabel", 
                       background=theme.accent, 
                       foreground="#ffffff",
                       padding=5)
        
        # Button styles - Normal
        style.configure("TButton", 
                       background=theme.button_bg,
                       foreground=theme.button_fg,
                       padding=5)
        
        # Button styles - Action/State-specific
        button_inactive_color = config.button_inactive_color if config else "#cccccc"
        button_ready_color = config.button_ready_color if config else "#2962ff"
        button_success_color = config.button_success_color if config else "#4caf50"
        
        # Black text color for colored buttons to improve readability
        style.configure("Action.Inactive.TButton",
                       background=button_inactive_color,
                       foreground=theme.button_text)  # Black text
        style.map("Action.Inactive.TButton",
                 background=[('active', button_inactive_color)],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
        
        style.configure("Action.Ready.TButton",
                       background=button_ready_color,
                       foreground=theme.button_text)  # Black text
        style.map("Action.Ready.TButton",
                 background=[('active', button_ready_color)],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
        
        style.configure("Action.Success.TButton",
                       background=button_success_color,
                       foreground=theme.button_text)  # Black text
        style.map("Action.Success.TButton",
                 background=[('active', button_success_color)],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
                 
        style.configure("Action.TButton",
                       background=button_ready_color,
                       foreground=theme.button_text)  # Black text
        style.map("Action.TButton",
                 background=[('active', button_ready_color)],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
                 
        style.configure("Cancel.TButton",
                       background="#f44336",  # Red
                       foreground=theme.button_text)  # Black text
        style.map("Cancel.TButton",
                 background=[('active', "#f44336")],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
        
        # Audio control buttons
        style.configure("Audio.Play.TButton",
                       background="#4caf50",  # Green
                       foreground=theme.button_text)  # Black text
        style.map("Audio.Play.TButton",
                 background=[('active', "#4caf50")],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
        
        style.configure("Audio.Stop.TButton",
                       background="#f44336",  # Red
                       foreground=theme.button_text)  # Black text
        style.map("Audio.Stop.TButton",
                 background=[('active', "#f44336")],
                 foreground=[('active', theme.button_text)])  # Black text when hovering
        
        # Grouping frames
        style.configure("Group.TLabelframe",
                       background=theme.bg)
        style.configure("Group.TLabelframe.Label",
                       background=theme.bg,
                       foreground=accent_color,
                       font=(config.font_family if config else 'Helvetica', 
                             11, 'bold'))
        
        return style
    except Exception as e:
        import logging
        logging.error(f"Error setting up styles: {e}")
        # Return a basic style to prevent crashes
        return ttk.Style()


class AppDimensions:
    def __init__(self):
        self.default_width = 900
        self.default_height = 650
        self.min_width = 750
        self.min_height = 500