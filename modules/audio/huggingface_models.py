import os
import logging
import asyncio
import torch
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from transformers import AutoProcessor, AutoModel, pipeline

class HuggingFaceModelManager:
    """Manager class for handling Hugging Face models for text-to-speech"""
    
    # Default models to recommend for first-time setup
    DEFAULT_TTS_MODELS = [
        {"id": "microsoft/speecht5_tts", "name": "SpeechT5 TTS"},
        {"id": "espnet/kan-bayashi_ljspeech_vits", "name": "LJSpeech VITS"},
        {"id": "suno/bark-small", "name": "Bark Small"}
    ]
    
    # Default vocoder model (used with some TTS models)
    DEFAULT_VOCODER = "microsoft/speecht5_hifigan"
    
    def __init__(self, models_dir: str):
        """Initialize the Hugging Face model manager"""
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.available_models = {}
        self.current_model = None
        self.current_vocoder = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts_processor = None
        self.tts_model = None
        self.vocoder_model = None
        self._initialized = False
        logging.info(f"HuggingFaceModelManager initialized with device: {self.device}")
        
        # Initialize recommended models list
        self._recommended_models = self.DEFAULT_TTS_MODELS
    
    async def initialize(self):
        """Asynchronously initialize the model manager"""
        if self._initialized:
            return
        
        try:
            # Scan for already downloaded models
            await self.scan_local_models()
            self._initialized = True
        except Exception as e:
            logging.error(f"Failed to initialize Hugging Face model manager: {e}")
            raise
    
    async def scan_local_models(self) -> Dict[str, Dict[str, Any]]:
        """Scan for downloaded models in the models directory"""
        self.available_models = {}
        
        try:
            # Run in a thread pool to avoid blocking the main thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            await loop.run_in_executor(None, self._scan_local_models_sync)
            return self.available_models
        except Exception as e:
            logging.error(f"Error scanning local models: {e}")
            raise
    
    def _scan_local_models_sync(self):
        """Synchronous implementation of model scanning"""
        if not self.models_dir.exists():
            return
        
        # First, look for models directly in the models directory
        for item in self.models_dir.iterdir():
            if not item.is_dir():
                continue
            
            # Check if this is a valid model directory
            config_path = item.joinpath("config.json")
            if config_path.exists():
                try:
                    # Try to identify the model - it could be just the model name without organization
                    model_id = item.name
                    
                    # Look for a .model_info file that might contain the full model ID
                    model_info_path = item.joinpath(".model_info")
                    if model_info_path.exists():
                        try:
                            with open(model_info_path, "r") as f:
                                model_id = f.read().strip()
                        except:
                            pass
                    
                    self.available_models[model_id] = {
                        "name": model_id,
                        "path": str(item),
                        "type": self._determine_model_type(item),
                        "is_local": True
                    }
                    logging.info(f"Found local model: {model_id}")
                except Exception as e:
                    logging.warning(f"Error processing model {item}: {e}")
        
        # Then check for organization folders which may contain model subfolders
        for org_dir in self.models_dir.iterdir():
            if not org_dir.is_dir():
                continue
                
            for model_dir in org_dir.iterdir():
                if not model_dir.is_dir():
                    continue
                    
                # Check if this is a valid model directory
                config_path = model_dir.joinpath("config.json")
                if config_path.exists():
                    try:
                        # This is the organization/model_name format
                        model_id = f"{org_dir.name}/{model_dir.name}"
                        
                        self.available_models[model_id] = {
                            "name": model_id,
                            "path": str(model_dir),
                            "type": self._determine_model_type(model_dir),
                            "is_local": True
                        }
                        logging.info(f"Found local model with organization: {model_id}")
                    except Exception as e:
                        logging.warning(f"Error processing model {model_dir}: {e}")
    
    def _determine_model_type(self, model_path: Path) -> str:
        """Determine the type of model from its directory structure"""
        # This is a simplified version - in practice you might need more sophisticated detection
        if (model_path / "generation_config.json").exists():
            return "tts"
        elif (model_path / "vocoder_config.json").exists():
            return "vocoder"
        return "unknown"
    
    def check_model_available_locally(self, model_id: str) -> bool:
        """
        Check if a model is available locally.
        
        Args:
            model_id: The model ID to check (e.g., "microsoft/speecht5_tts")
            
        Returns:
            bool: True if the model is available locally, False otherwise
        """
        return model_id in self.available_models
    
    def get_model_installation_instructions(self, model_id: str) -> str:
        """
        Get instructions for how to manually download and install a model.
        
        Args:
            model_id: The model ID to provide instructions for
            
        Returns:
            str: Instructions for manual model installation
        """
        # Parse the model_id to determine organization and model name
        if "/" in model_id:
            org, model_name = model_id.split("/", 1)
            model_path = os.path.join(self.models_dir, org, model_name)
        else:
            model_name = model_id
            model_path = os.path.join(self.models_dir, model_name)
            
        instructions = f"""
Model '{model_id}' is not available locally. To use this model, please download it manually:

1. Visit https://huggingface.co/{model_id}
2. Click 'Files and versions' tab
3. Download all model files (configuration files, weights, etc.)
4. Create this folder structure: {model_path}
5. Place all downloaded files in that folder
6. Restart the application

Note: Some models can be very large (several GB). Make sure you have enough storage space.
"""
        return instructions
    
    async def load_model(self, model_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Load a text-to-speech model for use
        
        Args:
            model_id: The model ID to load
            progress_callback: Optional callback to report loading progress
        
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            if progress_callback:
                progress_callback(f"Checking if model {model_id} is available locally...")
            
            # Check if model is available locally
            if model_id not in self.available_models:
                error_msg = f"Model {model_id} not found locally."
                instructions = self.get_model_installation_instructions(model_id)
                if progress_callback:
                    progress_callback(f"{error_msg}\n\n{instructions}")
                logging.error(error_msg)
                return False
            
            # Get model path
            model_path = self.available_models[model_id]["path"]
            
            if progress_callback:
                progress_callback(f"Loading model {model_id}...")
                
            # Use executor to run model loading in a background thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            processor, model = await loop.run_in_executor(
                None,
                lambda: self._load_model_sync(model_id, model_path)
            )
            
            self.tts_processor = processor
            self.tts_model = model
            self.current_model = model_id
            
            if progress_callback:
                progress_callback(f"Model {model_id} loaded successfully")
            
            return True
        except Exception as e:
            logging.error(f"Failed to load model {model_id}: {e}")
            if progress_callback:
                progress_callback(f"Failed to load model {model_id}: {str(e)}")
            return False
    
    def _load_model_sync(self, model_id: str, model_path: str) -> Tuple[Any, Any]:
        """Synchronous implementation of model loading"""
        try:
            # Specific handling for different model types
            if "speecht5" in model_id:
                processor = AutoProcessor.from_pretrained(model_path)
                model = AutoModel.from_pretrained(model_path).to(self.device)
                return processor, model
            else:
                # For other models, use the pipeline approach
                tts = pipeline("text-to-speech", model=model_path, device=self.device)
                return tts, tts
        except Exception as e:
            logging.error(f"Error in _load_model_sync: {e}")
            raise
    
    async def load_vocoder(self, vocoder_id: str = None, progress_callback: Optional[Callable] = None) -> bool:
        """
        Load a vocoder model (used with some TTS models)
        
        Args:
            vocoder_id: The vocoder model ID to load (default: DEFAULT_VOCODER)
            progress_callback: Optional callback to report loading progress
        
        Returns:
            bool: True if loading was successful, False otherwise
        """
        if vocoder_id is None:
            vocoder_id = self.DEFAULT_VOCODER
        
        try:
            if progress_callback:
                progress_callback(f"Checking if vocoder {vocoder_id} is available locally...")
            
            # Check if vocoder is available locally
            if vocoder_id not in self.available_models:
                error_msg = f"Vocoder {vocoder_id} not found locally."
                instructions = self.get_model_installation_instructions(vocoder_id)
                if progress_callback:
                    progress_callback(f"{error_msg}\n\n{instructions}")
                logging.error(error_msg)
                return False
            
            # Get vocoder path
            vocoder_path = self.available_models[vocoder_id]["path"]
            
            if progress_callback:
                progress_callback(f"Loading vocoder {vocoder_id}...")
            
            # Use executor to run model loading in a background thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there isn't one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            vocoder = await loop.run_in_executor(
                None,
                lambda: AutoModel.from_pretrained(vocoder_path).to(self.device)
            )
            
            self.vocoder_model = vocoder
            self.current_vocoder = vocoder_id
            
            if progress_callback:
                progress_callback(f"Vocoder {vocoder_id} loaded successfully")
            
            return True
        except Exception as e:
            logging.error(f"Failed to load vocoder {vocoder_id}: {e}")
            if progress_callback:
                progress_callback(f"Failed to load vocoder {vocoder_id}: {str(e)}")
            return False
    
    async def text_to_speech(
        self, 
        text: str, 
        output_path: str, 
        speaker_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """
        Convert text to speech using the currently loaded model
        
        Args:
            text: The text to convert to speech
            output_path: Path to save the audio file
            speaker_id: Optional speaker ID for multi-speaker models
            progress_callback: Optional callback to report progress
        
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        if not self.tts_model or not self.tts_processor:
            if progress_callback:
                progress_callback("No TTS model loaded")
            return False
        
        try:
            if progress_callback:
                progress_callback("Converting text to speech...")
            
            # Use executor to run TTS in a background thread
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                lambda: self._text_to_speech_sync(text, output_path, speaker_id)
            )
            
            if progress_callback:
                if success:
                    progress_callback("Text-to-speech conversion completed successfully")
                else:
                    progress_callback("Text-to-speech conversion failed")
            
            return success
        except Exception as e:
            logging.error(f"Failed to convert text to speech: {e}")
            if progress_callback:
                progress_callback(f"Failed to convert text to speech: {str(e)}")
            return False
    
    def _text_to_speech_sync(self, text: str, output_path: str, speaker_id: Optional[str] = None) -> bool:
        """Synchronous implementation of text-to-speech conversion"""
        try:
            # Handle different model types differently
            if isinstance(self.tts_model, pipeline):
                # For pipeline-based models
                speech = self.tts_model(text, forward_params={"speaker_id": speaker_id} if speaker_id else None)
                
                if isinstance(speech, dict) and "audio" in speech:
                    import soundfile as sf
                    sf.write(output_path, speech["audio"], speech["sampling_rate"])
                else:
                    with open(output_path, "wb") as f:
                        f.write(speech["bytes"].getvalue())
            
            elif "speecht5" in self.current_model:
                # For SpeechT5 model
                inputs = self.tts_processor(text=text, return_tensors="pt").to(self.device)
                speech = self.tts_model.generate_speech(inputs["input_ids"], self.vocoder_model)
                
                import soundfile as sf
                sf.write(output_path, speech.cpu().numpy(), 16000)
            
            else:
                logging.error(f"Unsupported model type: {self.current_model}")
                return False
            
            return True
        except Exception as e:
            logging.error(f"Error in _text_to_speech_sync: {e}")
            return False
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available voices/models
        
        Returns:
            List of dictionaries with model information
        """
        # Refresh local models
        await self.scan_local_models()
        
        # Format the data for UI display
        voices = []
        for model_id, model_info in self.available_models.items():
            if model_info.get("type") == "tts" or model_info.get("type") == "unknown":
                voices.append({
                    "id": model_id,
                    "name": model_id.split('/')[-1] if '/' in model_id else model_id,
                    "path": model_info.get("path", ""),
                    "is_local": model_info.get("is_local", False)
                })
        
        return voices
    
    def get_recommended_models(self) -> List[Dict[str, str]]:
        """Get a list of recommended models to download"""
        return self._recommended_models
    
    def cleanup(self):
        """Clean up resources"""
        # Clear model references to help with garbage collection
        self.tts_processor = None
        self.tts_model = None
        self.vocoder_model = None
        
        # Force CUDA memory cleanup if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()