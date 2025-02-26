from tkinter import ttk

def setup_styles():
    """Configure custom ttk styles for the application"""
    style = ttk.Style()
    
    # Configure colors
    accent_color = "#2962ff"  # Material Blue
    accent_light = "#768fff"
    accent_dark = "#0039cb"
    bg_color = "#f5f5f5"      # Light gray background
    status_bg = "#1976d2"     # Darker blue for status bar
    status_fg = "white"       # White text for status
    
    # Configure general styles
    style.configure(".", font=('Helvetica', 10))
    style.configure("TLabelframe", background=bg_color)
    style.configure("TLabelframe.Label", font=('Helvetica', 10, 'bold'))
    
    # Custom title style
    style.configure("Title.TLabel", 
                   font=('Helvetica', 24, 'bold'),
                   foreground=accent_dark)
    
    # Custom subtitle style
    style.configure("Subtitle.TLabel",
                   font=('Helvetica', 12),
                   foreground=accent_color)
    
    # Custom button styles
    style.configure("Action.TButton",
                   font=('Helvetica', 10, 'bold'),
                   background=accent_color,
                   padding=5)
    
    style.configure("Cancel.TButton",
                   padding=5)
    
    # Custom frame styles
    style.configure("Group.TLabelframe",
                   padding=10,
                   relief="solid")
    
    # Status bar style - new modern look
    style.configure("Status.TFrame",
                   background=status_bg)
    style.configure("Status.TLabel",
                   background=status_bg,
                   foreground=status_fg,
                   font=('Helvetica', 10),
                   padding=5)

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