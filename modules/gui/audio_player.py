import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging

class AudioPlayer:
    """Helper class to manage audio playback functionality"""
    def __init__(self, audio_processor, terminal_callback, root):
        self.audio_processor = audio_processor
        self.terminal_callback = terminal_callback
        self.root = root
        self.current_audio_file = None
        self.playback_active = False
        
    def setup_playback_controls(self, play_button, stop_button):
        """Setup playback controls"""
        self.play_button = play_button
        self.stop_button = stop_button
    
    def set_audio_file(self, audio_file_path):
        """Set the audio file for playback"""
        self.current_audio_file = audio_file_path
        if audio_file_path and os.path.exists(audio_file_path):
            self.play_button.configure(state=tk.NORMAL)
        else:
            self.play_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.DISABLED)
    
    def play_audio(self):
        """Play current audio file"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            self.play_button.configure(state=tk.DISABLED)
            return False

        try:
            self.audio_processor.play_audio(self.current_audio_file)
            self.playback_active = True
            self.play_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.terminal_callback("Playing audio file...")
            
            # Start checking playback status
            self.check_playback_status()
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {str(e)}")
            self._reset_audio_buttons()
            self.terminal_callback("Error playing audio file")
            return False

    def check_playback_status(self):
        """Check if audio is still playing"""
        try:
            if self.audio_processor.is_playing():
                self.root.after(100, self.check_playback_status)
            else:
                self._reset_audio_buttons()
                self.terminal_callback("Audio playback completed")
        except Exception as e:
            logging.error(f"Error checking playback status: {e}")
            self._reset_audio_buttons()

    def stop_audio(self):
        """Stop audio playback"""
        try:
            if self.playback_active:
                self.audio_processor.stop_audio()
                self._reset_audio_buttons()
                self.terminal_callback("Audio playback stopped")
                return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop audio: {str(e)}")
            self._reset_audio_buttons()
        return False

    def _reset_audio_buttons(self):
        """Reset audio control buttons"""
        self.playback_active = False
        if self.current_audio_file and os.path.exists(self.current_audio_file):
            self.play_button.configure(state=tk.NORMAL)
        else:
            self.play_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.DISABLED)