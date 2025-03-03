import os
import logging
import asyncio
import torch
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from transformers import AutoProcessor, AutoModel, pipeline
from huggingface_hub import hf_hub_download, snapshot_download
from huggingface_hub.utils import HfHubHTTPError

class HuggingFaceModelManager:
    """Manager class for handling Hugging Face models for text-to-speech"""
    
    # Default models to recommend for first-time setup
    DEFAULT_TTS_MODELS = [
        "microsoft/speecht5_tts",
        "facebook/mms-tts-eng",
        "espnet/kan-bayashi_ljspeech_vits",
        "suno/bark-small"
    ]
    
    # Default vocoder model (used with some TTS models)
    DEFAULT_VOCODER = "microsoft/speecht5_hifigan"
    
    def __init__(self, models_dir: str):
        """
        Initialize the Hugging Face model manager
        
        Args:
            models_dir: Path to directory where models will be stored
        """
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
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._scan_local_models_sync)
            return self.available_models
        except Exception as e:
            logging.error(f"Error scanning local models: {e}")
            raise
    
    def _scan_local_models_sync(self):
        """Synchronous implementation of model scanning"""
        if not self.models_dir.exists():
            return
        
        for item in self.models_dir.iterdir():
            if not item.is_dir():
                continue
            
            # Check if this is a valid model directory
            config_path = item.joinpath("config.json")
            if config_path.exists():
                try:
                    model_id = item.name
                    self.available_models[model_id] = {
                        "name": model_id,
                        "path": str(item),
                        "type": self._determine_model_type(item),
                        "is_local": True
                    }
                    logging.info(f"Found local model: {model_id}")
                except Exception as e:
                    logging.warning(f"Error processing model {item}: {e}")
    
    def _determine_model_type(self, model_path: Path) -> str:
        """Determine the type of model from its directory structure"""
        # This is a simplified version - in practice you might need more sophisticated detection
        if (model_path / "generation_config.json").exists():
            return "tts"
        elif (model_path / "vocoder_config.json").exists():
            return "vocoder"
        return "unknown"
    
    async def download_model(self, model_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Download a model from Hugging Face Hub
        
        Args:
            model_id: The model ID on Hugging Face Hub (e.g., "microsoft/speecht5_tts")
            progress_callback: Optional callback to report download progress
        
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            # Create a subdirectory for the model
            model_name = model_id.split('/')[-1] if '/' in model_id else model_id
            model_dir = self.models_dir / model_name
            
            if progress_callback:
                progress_callback(f"Starting download of {model_id}...")
            
            # Use executor to run the download in a background thread
            loop = asyncio.get_event_loop()
            model_path = await loop.run_in_executor(
                None, 
                lambda: snapshot_download(
                    repo_id=model_id,
                    local_dir=str(model_dir),
                    local_dir_use_symlinks=False
                )
            )
            
            # Update available models
            self.available_models[model_id] = {
                "name": model_id,
                "path": model_path,
                "type": self._determine_model_type(Path(model_path)),
                "is_local": True
            }
            
            if progress_callback:
                progress_callback(f"Downloaded {model_id} successfully")
            
            return True
        except Exception as e:
            logging.error(f"Failed to download model {model_id}: {e}")
            if progress_callback:
                progress_callback(f"Failed to download {model_id}: {str(e)}")
            return False
    
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
                progress_callback(f"Loading model {model_id}...")
            
            # Check if model is available locally
            if model_id not in self.available_models:
                if progress_callback:
                    progress_callback(f"Model {model_id} not found locally, downloading...")
                success = await self.download_model(model_id, progress_callback)
                if not success:
                    return False
            
            # Get model path
            model_path = self.available_models[model_id]["path"]
            
            # Use executor to run model loading in a background thread
            loop = asyncio.get_event_loop()
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
                progress_callback(f"Loading vocoder {vocoder_id}...")
            
            # Check if vocoder is available locally
            if vocoder_id not in self.available_models:
                if progress_callback:
                    progress_callback(f"Vocoder {vocoder_id} not found locally, downloading...")
                success = await self.download_model(vocoder_id, progress_callback)
                if not success:
                    return False
            
            # Get vocoder path
            vocoder_path = self.available_models[vocoder_id]["path"]
            
            # Use executor to run model loading in a background thread
            loop = asyncio.get_event_loop()
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
        """
        Get a list of recommended models to download
        
        Returns:
            List of dictionaries with model information
        """
        return [{"id": model_id, "name": model_id.split('/')[-1]} for model_id in self.DEFAULT_TTS_MODELS]
    
    def cleanup(self):
        """Clean up resources"""
        # Clear model references to help with garbage collection
        self.tts_processor = None
        self.tts_model = None
        self.vocoder_model = None
        
        # Force CUDA memory cleanup if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()