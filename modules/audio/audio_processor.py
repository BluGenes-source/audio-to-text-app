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
    """Find FFmpeg executable in common locations"""
    try:
        # First check the tools directory relative to this file
        tools_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tools')
        ffmpeg_exe = os.path.join(tools_path, 'ffmpeg.exe')
        ffprobe_exe = os.path.join(tools_path, 'ffprobe.exe')
        
        if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
            try:
                # Test both executables
                result_ffmpeg = subprocess.run([ffmpeg_exe, '-version'],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            encoding='utf-8')
                result_ffprobe = subprocess.run([ffprobe_exe, '-version'],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             encoding='utf-8')
                if result_ffmpeg.returncode == 0 and result_ffprobe.returncode == 0:
                    logging.info(f"Found FFmpeg tools in tools directory: {tools_path}")
                    return ffmpeg_exe
            except Exception as e:
                logging.error(f"Error testing FFmpeg tools in tools directory: {e}")
        
        # Then try system path
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 encoding='utf-8')
            if result.returncode == 0:
                logging.info("Found FFmpeg in system PATH")
                return 'ffmpeg'
        except FileNotFoundError:
            logging.warning("FFmpeg not found in system PATH")
        
        # Check other common locations as fallback
        possible_paths = [
            os.path.join(os.getenv('ProgramFiles'), 'ffmpeg', 'bin'),
            os.path.join(os.getenv('ProgramFiles(x86)'), 'ffmpeg', 'bin'),
            os.path.join(os.getenv('LOCALAPPDATA'), 'Programs', 'ffmpeg', 'bin'),
        ]
        
        for base_path in possible_paths:
            if base_path and os.path.exists(base_path):
                ffmpeg_path = os.path.join(base_path, 'ffmpeg.exe')
                ffprobe_path = os.path.join(base_path, 'ffprobe.exe')
                if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
                    try:
                        result_ffmpeg = subprocess.run([ffmpeg_path, '-version'],
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    encoding='utf-8')
                        result_ffprobe = subprocess.run([ffprobe_path, '-version'],
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.PIPE,
                                                     encoding='utf-8')
                        if result_ffmpeg.returncode == 0 and result_ffprobe.returncode == 0:
                            logging.info(f"Found FFmpeg tools in alternate location: {base_path}")
                            return ffmpeg_path
                    except Exception as e:
                        logging.error(f"Error testing FFmpeg at {base_path}: {e}")
                        continue
    except Exception as e:
        logging.error(f"Error during FFmpeg search: {e}")
    
    logging.error("FFmpeg/FFprobe not found in any location")
    return None

def _ensure_ffmpeg(func):
    """Decorator to ensure FFmpeg is properly configured before audio operations"""
    def wrapper(self, *args, **kwargs):
        if self.ffmpeg_path:
            # Reset FFmpeg paths before each operation
            AudioSegment.converter = self.ffmpeg_path
            AudioSegment.ffmpeg = self.ffmpeg_path
            AudioSegment.ffprobe = self.ffmpeg_path
        return func(self, *args, **kwargs)
    return wrapper

class AudioProcessor:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        self.initialize_pygame()
        self.current_playback_file = None
        
        # Get FFmpeg path and ensure it's set
        self.ffmpeg_path = find_ffmpeg()
        if self.ffmpeg_path:
            from pydub import AudioSegment
            AudioSegment.converter = self.ffmpeg_path
            AudioSegment.ffmpeg = self.ffmpeg_path
            AudioSegment.ffprobe = self.ffmpeg_path
            os.environ['FFMPEG_BINARY'] = self.ffmpeg_path

    def initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        try:
            pygame.mixer.quit()  # Ensure mixer is properly shut down
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except Exception as e:
            logging.error(f"Failed to initialize pygame mixer: {e}")

    @_ensure_ffmpeg
    def convert_audio_to_text(self, audio_path, progress_callback=None):
        """Convert audio file to text using speech recognition"""
        temp_path = None
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
            
            try:
                # Load and normalize audio file
                audio = AudioSegment.from_file(audio_path)
                audio = audio.set_frame_rate(16000).set_channels(1)  # Mono 16kHz for speech recognition
                logging.info(f"Successfully loaded and normalized audio file: {audio_path}")
                logging.info(f"Audio properties - Channels: {audio.channels}, Frame rate: {audio.frame_rate}, Sample width: {audio.sample_width}")
            except Exception as e:
                logging.error(f"Failed to load audio file: {e}")
                raise RuntimeError(f"Failed to load audio file: {str(e)}")
            
            os.makedirs(self.output_folder, exist_ok=True)
            temp_path = os.path.join(self.output_folder, 
                                   f"temp_{os.path.splitext(os.path.basename(audio_path))[0]}.wav")
            
            if progress_callback:
                progress_callback("Converting audio format for optimal recognition...")
            
            # Export with specific WAV format parameters for speech recognition
            try:
                audio.export(temp_path, format="wav", parameters=[
                    "-ac", "1",  # Mono
                    "-ar", "16000",  # 16kHz sample rate
                    "-acodec", "pcm_s16le",  # 16-bit PCM encoding
                    "-loglevel", "error"
                ])
                logging.info(f"Successfully exported temp WAV file to: {temp_path}")
            except Exception as e:
                logging.error(f"Failed to export WAV file: {e}")
                raise RuntimeError(f"Failed to export WAV file: {str(e)}")
            
            if progress_callback:
                progress_callback("Performing speech recognition...")
            
            try:
                with sr.AudioFile(temp_path) as source:
                    audio_data = recognizer.record(source)
                    if progress_callback:
                        progress_callback("Processing audio...")
                    text = recognizer.recognize_google(audio_data, language='en-US', show_all=True)
                    logging.info("Successfully performed speech recognition")
            except Exception as e:
                logging.error(f"Speech recognition failed: {e}")
                raise RuntimeError(f"Speech recognition failed: {str(e)}")
            
            if not text:
                raise sr.UnknownValueError("Speech recognition returned empty result")
            
            if isinstance(text, dict) and 'alternative' in text:
                text = text['alternative'][0]['transcript']
                logging.info("Successfully extracted transcript")
            
            return text
            
        except Exception as e:
            logging.error(f"Error in audio conversion: {str(e)}")
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    logging.warning(f"Failed to remove temporary file: {temp_path}")

    @_ensure_ffmpeg
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

    @_ensure_ffmpeg
    def play_audio(self, audio_path):
        """Play audio file using pygame mixer"""
        try:
            # Clean up any previous temporary file
            self._cleanup_temp_playback()
            
            # Convert audio to WAV format that pygame can handle
            audio = AudioSegment.from_file(audio_path)
            # Convert to format compatible with pygame: WAV PCM 16-bit stereo 44.1kHz
            audio = audio.set_frame_rate(44100).set_channels(2)
            
            # Create temporary WAV file for playback
            os.makedirs(self.output_folder, exist_ok=True)
            self.current_playback_file = os.path.join(
                self.output_folder, 
                f"temp_playback_{os.path.basename(audio_path)}.wav"
            )
            
            audio.export(self.current_playback_file, format="wav", parameters=[
                "-ac", "2",  # Stereo
                "-ar", "44100",  # 44.1kHz sample rate
                "-acodec", "pcm_s16le",  # 16-bit PCM encoding
                "-loglevel", "error"
            ])
            
            # Initialize and play audio
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            pygame.mixer.music.load(self.current_playback_file)
            pygame.mixer.music.play()
            return True
            
        except Exception as e:
            self._cleanup_temp_playback()
            logging.error(f"Error playing audio: {str(e)}")
            raise

    def stop_audio(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
            self._cleanup_temp_playback()
            return True
        except Exception as e:
            logging.error(f"Error stopping audio: {str(e)}")
            raise

    def _cleanup_temp_playback(self):
        """Clean up temporary playback file"""
        if self.current_playback_file and os.path.exists(self.current_playback_file):
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                os.remove(self.current_playback_file)
                self.current_playback_file = None
            except Exception as e:
                logging.warning(f"Failed to remove temporary playback file: {e}")

    def get_available_voices(self):
        """Get list of available voices for local TTS"""
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.stop()
        return voices

    def is_playing(self):
        """Check if audio is currently playing"""
        return pygame.mixer.music.get_busy()