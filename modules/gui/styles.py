from tkinter import ttk

class ThemeColors:
    def __init__(self, is_dark=False):
        if is_dark:
            # Dark theme colors
            self.bg = "#2d2d2d"  # Main background
            self.fg = "#ffffff"  # Main text color
            self.bg_secondary = "#3d3d3d"  # Secondary background (text boxes, input areas)
            self.bg_tertiary = "#4d4d4d"  # Tertiary background (selected tabs, hover states)
            self.border = "#555555"  # Border color
            self.selection_bg = "#666666"  # Selection background
            self.selection_fg = "#ffffff"  # Selection text color
            self.button_fg = "#ffffff"  # Button text color
            self.tab_active = "#4d4d4d"  # Active tab
            self.tab_inactive = "#3d3d3d"  # Inactive tab
            self.input_bg = "#3d3d3d"  # Input background
            self.input_fg = "#ffffff"  # Input text color
        else:
            # Light theme colors
            self.bg = "#f5f5f5"  # Main background
            self.fg = "#000000"  # Main text color
            self.bg_secondary = "#ffffff"  # Secondary background
            self.bg_tertiary = "#e0e0e0"  # Tertiary background
            self.border = "#cccccc"  # Border color
            self.selection_bg = "#0078d7"  # Selection background
            self.selection_fg = "#ffffff"  # Selection text color
            self.button_fg = "#000000"  # Button text color
            self.tab_active = "#ffffff"  # Active tab
            self.tab_inactive = "#f0f0f0"  # Inactive tab
            self.input_bg = "#ffffff"  # Input background
            self.input_fg = "#000000"  # Input text color

def setup_styles(config=None):
    """Configure custom ttk styles for the application"""
    style = ttk.Style()
    
    # Get theme colors based on current theme setting
    is_dark = config and config.theme == "dark"
    theme = ThemeColors(is_dark)
    
    # Use custom colors if provided in config
    accent_color = config.accent_color if config else "#2962ff"
    text_color = config.text_color if config else theme.fg
    
    # Set the base theme
    style.theme_use('default')
    
    # Configure general styles
    style.configure(".",
                   background=theme.bg,
                   foreground=text_color,
                   font=(config.font_family if config else 'Helvetica', 
                        config.font_size if config else 10))
    
    # Frame styles
    style.configure("TFrame", background=theme.bg)
    style.configure("TLabelframe", 
                   background=theme.bg,
                   foreground=text_color)
    style.configure("TLabelframe.Label", 
                   background=theme.bg,
                   foreground=text_color,
                   font=(config.font_family if config else 'Helvetica', 
                        config.font_size if config else 10, 'bold'))
    
    # Label styles
    style.configure("TLabel",
                   background=theme.bg,
                   foreground=text_color)
    
    # Entry styles
    style.configure("TEntry",
                   fieldbackground=theme.input_bg,
                   foreground=theme.input_fg,
                   selectbackground=theme.selection_bg,
                   selectforeground=theme.selection_fg,
                   insertcolor=theme.input_fg)
    
    # Button styles
    style.configure("TButton",
                   background=theme.bg_secondary,
                   foreground=theme.button_fg,
                   padding=5)
    
    style.map("TButton",
             background=[("active", theme.bg_tertiary),
                        ("pressed", theme.bg_tertiary)],
             foreground=[("active", theme.button_fg),
                        ("pressed", theme.button_fg)])
    
    # Custom title style
    style.configure("Title.TLabel", 
                   font=(config.font_family if config else 'Helvetica',
                        24, 'bold'),
                   foreground=accent_color,
                   background=theme.bg)
    
    # Custom subtitle style
    style.configure("Subtitle.TLabel",
                   font=(config.font_family if config else 'Helvetica',
                        12),
                   foreground=accent_color,
                   background=theme.bg)
    
    # Custom button styles
    style.configure("Action.TButton",
                   font=(config.font_family if config else 'Helvetica',
                        config.font_size if config else 10, 'bold'),
                   background=accent_color,
                   foreground=theme.button_fg,
                   padding=5)
    
    style.map("Action.TButton",
             background=[("active", accent_color),
                        ("pressed", accent_color)],
             foreground=[("active", theme.button_fg),
                        ("pressed", theme.button_fg)])
    
    style.configure("Cancel.TButton",
                   padding=5)
    
    # Custom frame styles
    style.configure("Group.TLabelframe",
                   padding=10,
                   relief="solid")
    
    # Status bar style
    style.configure("Status.TFrame",
                   background=accent_color)
    style.configure("Status.TLabel",
                   background=accent_color,
                   foreground="white",
                   font=(config.font_family if config else 'Helvetica',
                        config.font_size if config else 10),
                   padding=5)
    
    # Notebook (tabs) style
    style.configure("TNotebook",
                   background=theme.bg,
                   borderwidth=0,
                   tabmargins=[2, 5, 2, 0])
    
    style.configure("TNotebook.Tab",
                   background=theme.tab_inactive,
                   foreground=text_color,
                   padding=[10, 2],
                   font=(config.font_family if config else 'Helvetica',
                        config.font_size if config else 10))
    
    style.map("TNotebook.Tab",
             background=[("selected", theme.tab_active),
                        ("active", theme.bg_tertiary)],
             foreground=[("selected", text_color),
                        ("active", text_color)])
    
    # Combobox styles
    style.configure("TCombobox",
                   fieldbackground=theme.input_bg,
                   background=theme.input_bg,
                   foreground=theme.input_fg,
                   selectbackground=theme.selection_bg,
                   selectforeground=theme.selection_fg,
                   arrowcolor=text_color)
    
    style.map("TCombobox",
             fieldbackground=[("readonly", theme.input_bg)],
             selectbackground=[("readonly", theme.selection_bg)],
             selectforeground=[("readonly", theme.selection_fg)])
    
    # Spinbox styles
    style.configure("TSpinbox",
                   fieldbackground=theme.input_bg,
                   background=theme.input_bg,
                   foreground=theme.input_fg,
                   selectbackground=theme.selection_bg,
                   selectforeground=theme.selection_fg,
                   arrowcolor=text_color)
    
    # Configure text widget colors (will be applied in the tabs)
    style.configure("Custom.Text",
                   background=theme.input_bg,
                   foreground=theme.input_fg,
                   selectbackground=theme.selection_bg,
                   selectforeground=theme.selection_fg,
                   insertbackground=theme.input_fg)

    return style

class AppDimensions:
    """Class to handle default window dimensions"""
    def __init__(self):
        self.padding_height = 40    
        self.title_height = 80     
        self.folder_frame_height = 100  
        self.text_area_height = 300  
        self.terminal_height = 150  
        self.controls_height = 100  
        self.status_bar_height = 30
        
        self.default_height = (self.padding_height + self.title_height + 
                             self.folder_frame_height + self.text_area_height + 
                             self.terminal_height + self.controls_height + 
                             self.status_bar_height + 50)
        
        self.default_width = 1200  # Wide enough to show all controls
        self.min_width = 750