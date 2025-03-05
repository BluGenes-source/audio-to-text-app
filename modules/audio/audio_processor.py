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
import tempfile
import asyncio
import functools
import concurrent.futures
import traceback  # Added import for traceback
from functools import lru_cache
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path
from .huggingface_models import HuggingFaceModelManager  # Import the new HuggingFaceModelManager

MAX_AUDIO_LENGTH_MINUTES = 60.0  # Maximum audio length in minutes
MAX_AUDIO_LENGTH_SECONDS = MAX_AUDIO_LENGTH_MINUTES * 60  # Convert to seconds

def find_ffmpeg():
    """Find FFmpeg executable in common locations"""
    logging.info("Searching for FFmpeg executables...")
    try:
        # First check the tools directory relative to this file
        tools_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tools')
        ffmpeg_exe = os.path.join(tools_path, 'ffmpeg.exe')
        ffprobe_exe = os.path.join(tools_path, 'ffprobe.exe')
        
        logging.info(f"Checking tools directory: {tools_path}")
        if (os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe)):
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
                else:
                    logging.error(f"FFmpeg tools found but failed version check: ffmpeg={result_ffmpeg.returncode}, ffprobe={result_ffprobe.returncode}")
            except Exception as e:
                logging.error(f"Error testing FFmpeg tools in tools directory: {e}")
                logging.debug(f"FFmpeg error details: {traceback.format_exc()}")
        else:
            logging.warning(f"FFmpeg tools not found in tools directory: {tools_path}")
        
        # Then try system path
        try:
            logging.info("Checking system PATH for FFmpeg")
            result = subprocess.run(['ffmpeg', '-version'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 encoding='utf-8')
            if result.returncode == 0:
                logging.info("Found FFmpeg in system PATH")
                return 'ffmpeg'
        except FileNotFoundError:
            logging.warning("FFmpeg not found in system PATH")
        except Exception as e:
            logging.error(f"Error checking FFmpeg in system PATH: {e}")
            logging.debug(f"System PATH check error details: {traceback.format_exc()}")
        
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
                logging.info(f"Checking alternate location: {base_path}")
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
                        else:
                            logging.warning(f"FFmpeg tools found at {base_path} but failed version check")
                    except Exception as e:
                        logging.error(f"Error testing FFmpeg at {base_path}: {e}")
                        logging.debug(f"Alternate location error details: {traceback.format_exc()}")
                        continue
    except Exception as e:
        logging.error(f"Error during FFmpeg search: {e}")
        logging.debug(f"FFmpeg search error details: {traceback.format_exc()}")
    
    logging.error("FFmpeg/FFprobe not found in any location")
    return None

def _ensure_ffmpeg(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and try again.")
        return func(self, *args, **kwargs)
    return wrapper

class AudioProcessor:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        self.initialize_pygame()
        self.current_playback_file = None
        self._cache_dir = Path(tempfile.gettempdir()) / "audio_converter_cache"
        self._cache_dir.mkdir(exist_ok=True)
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self._conversion_cache = {}
        
        # Get FFmpeg path and ensure it's set
        self.ffmpeg_path = find_ffmpeg()
        if self.ffmpeg_path:
            from pydub import AudioSegment
            AudioSegment.converter = self.ffmpeg_path
            AudioSegment.ffmpeg = self.ffmpeg_path
            AudioSegment.ffprobe = self.ffmpeg_path
            os.environ['FFMPEG_BINARY'] = self.ffmpeg_path

        # Initialize Hugging Face model manager
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Models")
        self.hf_manager = HuggingFaceModelManager(models_dir)
        self._hf_initialized = False
        
        # Run initial async initialization
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                asyncio.create_task(self._init_hf_async())
            else:
                loop.run_until_complete(self._init_hf_async())
        except Exception as e:
            logging.error(f"Failed to initialize Hugging Face models: {e}")
            self._hf_initialized = False
            self.hf_manager = None

    async def _init_hf_async(self):
        """Initialize Hugging Face models asynchronously"""
        try:
            await self.hf_manager.initialize()
            self._hf_initialized = True
        except Exception as e:
            logging.error(f"Failed to initialize Hugging Face models: {e}")
            self._hf_initialized = False
            self.hf_manager = None

    def initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        try:
            pygame.mixer.quit()  # Ensure mixer is properly shut down
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except Exception as e:
            logging.error(f"Failed to initialize pygame mixer: {e}")

    @_ensure_ffmpeg
    @lru_cache(maxsize=32)
    def check_audio_length(self, audio_path: str) -> float:
        """Check audio file length - now cached for performance"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # Convert to seconds
        except Exception as e:
            logging.error(f"Error checking audio length: {e}")
            return 0.0

    def _get_cache_path(self, audio_path: str) -> Path:
        """Get cache file path for an audio file"""
        audio_hash = str(hash(audio_path + str(os.path.getmtime(audio_path))))
        return self._cache_dir / f"transcription_{audio_hash}.txt"

    async def convert_audio_to_text_async(self, audio_path: str, 
                                        progress_callback: Optional[Callable] = None) -> str:
        """Async version of audio to text conversion"""
        cache_path = self._get_cache_path(audio_path)
        
        # Check cache first
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()

        try:
            # Run CPU-intensive conversion in thread pool
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            text = await loop.run_in_executor(
                self._thread_pool,
                functools.partial(self._convert_audio_to_text_impl, 
                                audio_path, 
                                progress_callback)
            )

            # Cache the result
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(text)

            return text

        except Exception as e:
            logging.error(f"Error in async conversion: {e}")
            raise

    @_ensure_ffmpeg
    def _convert_audio_to_text_impl(self, audio_path: str, 
                                  progress_callback: Optional[Callable] = None) -> str:
        """Internal implementation of audio to text conversion"""
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()

            # Update status
            if progress_callback:
                progress_callback("Loading audio file...")

            # Convert audio to WAV if needed
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                if not audio_path.lower().endswith('.wav'):
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(audio_path)
                    audio.export(temp_wav.name, format='wav')
                    audio_path = temp_wav.name

                if progress_callback:
                    progress_callback("Recognizing speech...")

                with sr.AudioFile(audio_path) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                    
                    if progress_callback:
                        progress_callback("Speech recognition complete")
                    
                    return text

        except Exception as e:
            logging.error(f"Error in conversion implementation: {e}")
            raise
        finally:
            # Cleanup temporary WAV file if created
            if 'temp_wav' in locals():
                try:
                    os.unlink(temp_wav.name)
                except:
                    pass

    @_ensure_ffmpeg
    async def text_to_speech_async(self, text: str, output_path: str, 
                                 engine_type: str = None,
                                 voice_name: Optional[str] = None, 
                                 lang: str = "en",
                                 progress_callback: Optional[Callable] = None) -> bool:
        """Async version of text to speech conversion"""
        try:
            # Use the specified engine or the current default
            engine_type = engine_type or self.current_tts_engine
            
            # Check for Hugging Face engine type
            if engine_type == "huggingface":
                # Initialize Hugging Face if not already done
                if not self._hf_initialized:
                    if progress_callback:
                        progress_callback("Initializing Hugging Face model manager...")
                    await self.hf_manager.initialize()
                    self._hf_initialized = True
                
                # Use Hugging Face for TTS
                model_id = voice_name or self.current_hf_model
                if not model_id:
                    if progress_callback:
                        progress_callback("No Hugging Face model selected. Please select a model.")
                    return False
                
                # Load the model if needed
                if self.hf_manager.current_model != model_id:
                    success = await self.hf_manager.load_model(model_id, progress_callback)
                    if not success:
                        return False
                    
                    # For SpeechT5 models, also load the vocoder if needed
                    if "speecht5" in model_id and not self.hf_manager.vocoder_model:
                        await self.hf_manager.load_vocoder(None, progress_callback)
                
                # Convert text to speech using Hugging Face
                return await self.hf_manager.text_to_speech(text, output_path, None, progress_callback)
            
            else:
                # Use standard implementation for other engine types
                # Run CPU-intensive conversion in thread pool
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # Create a new event loop if there isn't one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                return await loop.run_in_executor(
                    self._thread_pool,
                    functools.partial(self._text_to_speech_impl,
                                    text, output_path, engine_type,
                                    voice_name, lang, progress_callback)
                )
        except Exception as e:
            logging.error(f"Error in async TTS conversion: {e}")
            raise

    def _text_to_speech_impl(self, text, output_path, engine_type,
                           voice_name, lang, progress_callback):
        """Internal implementation of text to speech conversion"""
        try:
            if engine_type == "google":
                from gtts import gTTS
                if progress_callback:
                    progress_callback("Converting text to speech using Google TTS...")
                tts = gTTS(text=text, lang=lang)
                tts.save(output_path)
            elif engine_type == "local":
                import pyttsx3
                engine = pyttsx3.init()
                if voice_name:
                    for voice in engine.getProperty('voices'):
                        if voice_name in voice.name:
                            engine.setProperty('voice', voice.id)
                            break
                if progress_callback:
                    progress_callback("Converting text to speech using local TTS...")
                engine.save_to_file(text, output_path)
                engine.runAndWait()
            else:
                raise ValueError(f"Unknown engine type: {engine_type}")
            
            if progress_callback:
                progress_callback("Speech generation complete")
            return True

        except Exception as e:
            logging.error(f"Error in TTS implementation: {e}")
            raise

    async def get_huggingface_voices(self) -> List[Dict[str, Any]]:
        """Get available Hugging Face TTS models"""
        if not self._hf_initialized:
            await self.hf_manager.initialize()
            self._hf_initialized = True
        
        return await self.hf_manager.get_available_voices()
    
    def get_huggingface_recommended_models(self) -> List[Dict[str, str]]:
        """Get recommended Hugging Face models for download"""
        try:
            if not self.hf_manager or not self._hf_initialized:
                return []
            return self.hf_manager.get_recommended_models()
        except Exception as e:
            logging.error(f"Error getting recommended models: {e}")
            return []

    def set_tts_engine(self, engine_type: str):
        """Set the TTS engine type (google, local, huggingface)"""
        if engine_type in ["google", "local", "huggingface"]:
            self.current_tts_engine = engine_type
            return True
        return False
    
    def set_huggingface_model(self, model_id: str):
        """Set the current Hugging Face model ID"""
        self.current_hf_model = model_id
        return True
        
    def set_local_voice(self, voice_name: str):
        """Set the local TTS voice"""
        self.current_local_voice = voice_name
        return True

    def cleanup(self):
        """Cleanup resources"""
        self._thread_pool.shutdown(wait=True)
        try:
            import shutil
            shutil.rmtree(self._cache_dir)
        except Exception as e:
            logging.error(f"Error cleaning up cache: {e}")
        
        # Clean up Hugging Face resources
        if hasattr(self, 'hf_manager'):
            self.hf_manager.cleanup()

    def play_audio(self, audio_path):
        """Play audio file using pygame mixer"""
        try:
            # Clean up any previous temporary file
            self._cleanup_temp_playback()
            
            # Convert audio to WAV format that pygame can handle
            audio = AudioSegment.from_file(audio_path)
            # Convert to format compatible with pygame: WAV PCM 16-bit stereo 44.1kHz
            audio = audio.set_frame_rate(44100).set_channels(2)
            
            logging.info(f"Starting audio playback for: {os.path.basename(audio_path)}")
            # Create temporary WAV file for playback
            os.makedirs(self.output_folder, exist_ok=True)
            self.current_playback_file = os.path.join(
                self.output_folder, 
                f"temp_playback_{os.path.basename(audio_path)}.wav"
            )
            
            logging.debug(f"Creating temporary playback file: {self.current_playback_file}")
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
            logging.info(f"Successfully started playback of: {os.path.basename(audio_path)}")
            return True
            
        except Exception as e:
            self._cleanup_temp_playback()
            error_msg = f"Error playing audio {os.path.basename(audio_path)}: {str(e)}"
            logging.error(error_msg, exc_info=True)  # Add full stack trace
            raise RuntimeError(error_msg) from e

    def stop_audio(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
            self._cleanup_temp_playback()
            logging.info("Stopped audio playback")
            return True
        except Exception as e:
            error_msg = f"Error stopping audio playback: {str(e)}"
            logging.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

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