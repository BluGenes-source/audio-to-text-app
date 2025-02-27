import tkinter as tk
from tkinter import ttk, colorchooser, font
import json
import os

class SettingsTab:
    def __init__(self, parent, config, update_styles_callback):
        self.parent = parent
        self.config = config
        self.update_styles = update_styles_callback
        self.setup_tab()

    def setup_tab(self):
        # Main container with padding
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Theme selection
        theme_frame = ttk.LabelFrame(main_frame, text="Theme Settings", padding="10")
        theme_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.theme_var = tk.StringVar(value=self.config.theme or "light")
        ttk.Radiobutton(theme_frame, text="Light Theme", 
                       variable=self.theme_var, 
                       value="light",
                       command=self.apply_settings).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(theme_frame, text="Dark Theme", 
                       variable=self.theme_var, 
                       value="dark",
                       command=self.apply_settings).grid(row=0, column=1, padx=5)

        # Font settings
        font_frame = ttk.LabelFrame(main_frame, text="Font Settings", padding="10")
        font_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Font family
        ttk.Label(font_frame, text="Font Family:").grid(row=0, column=0, padx=5, pady=5)
        self.font_family = tk.StringVar(value=self.config.font_family or "Helvetica")
        font_selector = ttk.Combobox(font_frame, textvariable=self.font_family)
        font_selector['values'] = sorted(font.families())
        font_selector.grid(row=0, column=1, sticky="ew", padx=5)
        font_selector.bind('<<ComboboxSelected>>', lambda e: self.apply_settings())

        # Font size
        ttk.Label(font_frame, text="Font Size:").grid(row=1, column=0, padx=5, pady=5)
        self.font_size = tk.StringVar(value=str(self.config.font_size or 10))
        size_selector = ttk.Spinbox(font_frame, from_=8, to=24, width=5,
                                  textvariable=self.font_size)
        size_selector.grid(row=1, column=1, sticky="w", padx=5)
        size_selector.bind('<Return>', lambda e: self.apply_settings())
        size_selector.bind('<FocusOut>', lambda e: self.apply_settings())

        # Color customization
        color_frame = ttk.LabelFrame(main_frame, text="Color Settings", padding="10")
        color_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # Accent color picker
        ttk.Label(color_frame, text="Accent Color:").grid(row=0, column=0, padx=5, pady=5)
        self.accent_color = tk.StringVar(value=self.config.accent_color or "#2962ff")
        self.accent_preview = tk.Frame(color_frame, width=30, height=20, 
                                     bg=self.accent_color.get())
        self.accent_preview.grid(row=0, column=1, padx=5)
        ttk.Button(color_frame, text="Choose Color",
                  command=lambda: self.choose_color('accent')).grid(row=0, column=2, padx=5)

        # Text color picker
        ttk.Label(color_frame, text="Text Color:").grid(row=1, column=0, padx=5, pady=5)
        self.text_color = tk.StringVar(value=self.config.text_color or "#000000")
        self.text_preview = tk.Frame(color_frame, width=30, height=20,
                                   bg=self.text_color.get())
        self.text_preview.grid(row=1, column=1, padx=5)
        ttk.Button(color_frame, text="Choose Color",
                  command=lambda: self.choose_color('text')).grid(row=1, column=2, padx=5)

        # Button state colors
        ttk.Label(color_frame, text="Inactive Button:").grid(row=2, column=0, padx=5, pady=5)
        self.button_inactive_color = tk.StringVar(value=self.config.button_inactive_color or "#cccccc")
        self.button_inactive_preview = tk.Frame(color_frame, width=30, height=20,
                                              bg=self.button_inactive_color.get())
        self.button_inactive_preview.grid(row=2, column=1, padx=5)
        ttk.Button(color_frame, text="Choose Color",
                  command=lambda: self.choose_color('button_inactive')).grid(row=2, column=2, padx=5)

        ttk.Label(color_frame, text="Ready Button:").grid(row=3, column=0, padx=5, pady=5)
        self.button_ready_color = tk.StringVar(value=self.config.button_ready_color or "#2962ff")
        self.button_ready_preview = tk.Frame(color_frame, width=30, height=20,
                                           bg=self.button_ready_color.get())
        self.button_ready_preview.grid(row=3, column=1, padx=5)
        ttk.Button(color_frame, text="Choose Color",
                  command=lambda: self.choose_color('button_ready')).grid(row=3, column=2, padx=5)

        ttk.Label(color_frame, text="Success Button:").grid(row=4, column=0, padx=5, pady=5)
        self.button_success_color = tk.StringVar(value=self.config.button_success_color or "#4caf50")
        self.button_success_preview = tk.Frame(color_frame, width=30, height=20,
                                           bg=self.button_success_color.get())
        self.button_success_preview.grid(row=4, column=1, padx=5)
        ttk.Button(color_frame, text="Choose Color",
                  command=lambda: self.choose_color('button_success')).grid(row=4, column=2, padx=5)

        ttk.Label(color_frame, text="Disabled Color:").grid(row=5, column=0, padx=5, pady=5)
        self.disabled_color = tk.StringVar(value=self.config.disabled_color or "#e0e0e0")
        self.disabled_preview = tk.Frame(color_frame, width=30, height=20,
                                     bg=self.disabled_color.get())
        self.disabled_preview.grid(row=5, column=1, padx=5)
        ttk.Button(color_frame, text="Choose Color",
                  command=lambda: self.choose_color('disabled')).grid(row=5, column=2, padx=5)

        # Queue Settings
        queue_frame = ttk.LabelFrame(main_frame, text="Queue Settings", padding="10")
        queue_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(queue_frame, text="Delay between files (seconds):").grid(row=0, column=0, padx=5, pady=5)
        self.queue_delay = tk.StringVar(value=str(self.config.queue_delay))
        delay_selector = ttk.Spinbox(queue_frame, from_=0, to=10, width=5,
                                  textvariable=self.queue_delay)
        delay_selector.grid(row=0, column=1, sticky="w", padx=5)
        delay_selector.bind('<Return>', lambda e: self.apply_settings())
        delay_selector.bind('<FocusOut>', lambda e: self.apply_settings())

        # Preview section
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, width=40, height=3)
        self.preview_text.insert('1.0', "This is a preview of how your text will look.")
        self.preview_text.grid(row=0, column=0, padx=5, pady=5)
        self.preview_text.configure(state='disabled')

        # Save button
        ttk.Button(main_frame, text="Save Settings",
                  command=self.save_settings,
                  style='Action.TButton').grid(row=5, column=0, pady=10)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        theme_frame.columnconfigure(1, weight=1)
        font_frame.columnconfigure(1, weight=1)
        color_frame.columnconfigure(2, weight=1)
        preview_frame.columnconfigure(0, weight=1)

    def choose_color(self, color_type):
        """Handle color chooser for different color settings"""
        if color_type == 'accent':
            current_color = self.accent_color.get()
        elif color_type == 'text':
            current_color = self.text_color.get()
        elif color_type == 'button_inactive':
            current_color = self.button_inactive_color.get()
        elif color_type == 'button_ready':
            current_color = self.button_ready_color.get()
        elif color_type == 'button_success':
            current_color = self.button_success_color.get()
        else:  # disabled
            current_color = self.disabled_color.get()

        color = colorchooser.askcolor(color=current_color)
        if color[1]:
            if color_type == 'accent':
                self.accent_color.set(color[1])
                self.accent_preview.configure(bg=color[1])
            elif color_type == 'text':
                self.text_color.set(color[1])
                self.text_preview.configure(bg=color[1])
            elif color_type == 'button_inactive':
                self.button_inactive_color.set(color[1])
                self.button_inactive_preview.configure(bg=color[1])
            elif color_type == 'button_ready':
                self.button_ready_color.set(color[1])
                self.button_ready_preview.configure(bg=color[1])
            elif color_type == 'button_success':
                self.button_success_color.set(color[1])
                self.button_success_preview.configure(bg=color[1])
            else:  # disabled
                self.disabled_color.set(color[1])
                self.disabled_preview.configure(bg=color[1])
            self.apply_settings()

    def apply_settings(self):
        # Update configuration
        self.config.theme = self.theme_var.get()
        self.config.font_family = self.font_family.get()
        try:
            self.config.font_size = int(self.font_size.get())
        except ValueError:
            self.config.font_size = 10
        self.config.accent_color = self.accent_color.get()
        self.config.text_color = self.text_color.get()
        self.config.button_inactive_color = self.button_inactive_color.get()
        self.config.button_ready_color = self.button_ready_color.get()
        self.config.button_success_color = self.button_success_color.get()
        self.config.disabled_color = self.disabled_color.get()
        try:
            self.config.queue_delay = int(self.queue_delay.get())
        except ValueError:
            self.config.queue_delay = 2

        # Update preview
        self.preview_text.configure(
            font=(self.font_family.get(), self.config.font_size),
            fg=self.text_color.get(),
            bg=self.get_background_color()
        )

        # Update application styles
        self.update_styles()

    def get_background_color(self):
        return "#f5f5f5" if self.theme_var.get() == "light" else "#2d2d2d"

    def save_settings(self):
        self.apply_settings()
        self.config.save_config()