import os
import subprocess
import speech_recognition as sr
from pydub import AudioSegment
import logging
import pygame.mixer
from gtts import gTTS
import pyttsx3
import re
import threading

def find_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'ffmpeg'
    except FileNotFoundError:
        possible_paths = [
            os.path.join(os.getenv('ProgramFiles'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.getenv('ProgramFiles(x86)'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.getenv('LOCALAPPDATA'), 'Programs', 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'ffmpeg.exe'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

class AudioProcessor:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        self.initialize_pygame()
        self.ffmpeg_path = find_ffmpeg()
        if self.ffmpeg_path:
            AudioSegment.converter = self.ffmpeg_path

    def initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        pygame.mixer.init()

    def convert_audio_to_text(self, audio_path, progress_callback=None):
        """Convert audio file to text using speech recognition"""
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                raise ValueError("Audio file is empty")
            
            if progress_callback:
                progress_callback(f"Initializing speech recognition for {os.path.basename(audio_path)}...")
            
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.8
            
            if progress_callback:
                progress_callback("Loading and analyzing audio file...")
            
            audio = AudioSegment.from_file(audio_path)
            duration_seconds = len(audio) / 1000
            
            os.makedirs(self.output_folder, exist_ok=True)
            temp_path = os.path.join(self.output_folder, 
                                   f"temp_{os.path.splitext(os.path.basename(audio_path))[0]}.wav")
            
            if progress_callback:
                progress_callback("Converting audio format for optimal recognition...")
            
            audio.export(temp_path, format="wav", parameters=[
                "-ac", "1", "-ar", "16000", "-loglevel", "error"
            ])
            
            if progress_callback:
                progress_callback("Performing speech recognition...")
            
            with sr.AudioFile(temp_path) as source:
                audio_data = recognizer.record(source)
                if progress_callback:
                    progress_callback("Processing audio...")
                text = recognizer.recognize_google(audio_data, language='en-US', show_all=True)
                
                if not text:
                    raise sr.UnknownValueError("Speech recognition returned empty result")
                
                if isinstance(text, dict) and 'alternative' in text:
                    text = text['alternative'][0]['transcript']
            
            try:
                os.remove(temp_path)
            except:
                pass
            
            return text
            
        except Exception as e:
            logging.error(f"Error in audio conversion: {str(e)}")
            raise

    def text_to_speech(self, text, output_path, engine_type="google", voice_name=None, 
                      lang="en", progress_callback=None):
        """Convert text to speech using selected engine"""
        try:
            if progress_callback:
                progress_callback("Starting text-to-speech conversion...")
            
            if engine_type == "google":
                if progress_callback:
                    progress_callback("Using Google TTS engine...")
                text = re.sub(r'<break\s+time="[^"]*"\s*/>', ' ', text)
                tts = gTTS(text=text, lang=lang)
                tts.save(output_path)
            else:
                if progress_callback:
                    progress_callback("Using local TTS engine...")
                engine = pyttsx3.init()
                if voice_name:
                    for voice in engine.getProperty('voices'):
                        if voice.name == voice_name:
                            engine.setProperty('voice', voice.id)
                            break
                
                if progress_callback:
                    progress_callback("Generating audio...")
                engine.save_to_file(text, output_path)
                engine.runAndWait()
            
            return True
        except Exception as e:
            logging.error(f"Error in text-to-speech conversion: {str(e)}")
            raise

    def play_audio(self, audio_path):
        """Play audio file using pygame mixer"""
        try:
            pygame.mixer.quit()
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            return True
        except Exception as e:
            logging.error(f"Error playing audio: {str(e)}")
            raise

    def stop_audio(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
            return True
        except Exception as e:
            logging.error(f"Error stopping audio: {str(e)}")
            raise

    def get_available_voices(self):
        """Get list of available voices for local TTS"""
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.stop()
        return voices

    def is_playing(self):
        """Check if audio is currently playing"""
        return pygame.mixer.music.get_busy()