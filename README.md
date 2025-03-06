# Audio/Text Converter Application
A Python desktop application for converting between audio and text, featuring both speech-to-text and text-to-speech capabilities.

## What's New
- Added Mermaid diagram showing module dependencies
- Added Hugging Face model integration for text-to-speech
- Fixed configuration attribute errors
- Improved error handling and logging
- Enhanced queue management system
- Added support for custom button colors and theme settings

## Features
- Speech to Text conversion with support for multiple audio formats (WAV, MP3, FLAC)
- Text to Speech conversion with multiple options:
  - Online (Google TTS)
  - Offline (local system TTS)
  - AI-powered (Hugging Face models)
- Audio playback with pause/stop controls
- Customizable user interface with light/dark themes
- Drag and drop support for files
- Progress tracking and detailed status updates
- Automatic pause insertion in text for better speech synthesis
- Save and load transcriptions

## Branch Information
- The `master` branch contains a stable version of the application that runs, but may not be fully functional
- New features will be developed in separate feature branches
- Updates to the master branch may take longer as they require thorough testing
- Current feature branches:
  - `local_tts`: Development branch for local AI model integration, starting with Hugging Face API (still under active development)

## Requirements
- Python 3.10 or higher
- FFmpeg and FFprobe executables (for audio processing)
- Required Python packages (see requirements.txt)

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd audio-to-text-app
   ```
2. Create and activate a virtual environment (recommended):
   ```
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/Mac:
   source .venv/bin/activate
   ```
3. Install required packages:
   ```
   pip install -r requirements.txt
   ```
4. Install FFmpeg:
   - Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z
   - Extract the archive
   - Copy both ffmpeg.exe AND ffprobe.exe from the bin folder to the 'tools' folder in the application directory
5. Install additional system requirements:
   - Install the `tkinter` package if not included in your Python installation:
     ```
     # On Ubuntu/Debian:
     sudo apt-get install python3-tk
     # On Fedora:
     sudo dnf install python3-tkinter
     # On Windows:
     # Tkinter comes with Python installation
     ```

## Running the Application
1. Make sure your virtual environment is activated
2. Run the main script:
   ```
   python main.py
   ```

## Usage
### Speech to Text
1. Click "Select Input Folder" to set your audio files location
2. Either drag and drop an audio file onto the text area or use "Load File from Input"
3. Click "Start Conversion" to begin transcription
4. Once complete, you can:
   - Save the transcribed text
   - Play back the audio
   - Send the text to the TTS tab

### Text to Speech
1. Enter or paste text into the text area
2. Use the formatting tools to add pauses and improve speech synthesis
3. Choose your TTS engine:
   - Google TTS (online)
   - Local TTS (offline system voices)
   - Hugging Face models (AI-powered)
4. Select your preferred voice
5. Click "Generate Speech" to create the audio
6. Preview the audio and save it if desired

### Settings
- Choose between light and dark themes
- Customize fonts and colors
- All settings are automatically saved

## Troubleshooting
1. FFmpeg Missing Error:
   - Ensure both ffmpeg.exe and ffprobe.exe are in the tools folder
   - Both executables must have execute permissions
2. Audio Playback Issues:
   - Make sure no other application is using your audio device
   - Try restarting the application if audio becomes unresponsive
3. Speech Recognition Errors:
   - Ensure you have a working internet connection for Google Speech Recognition
   - Check that your audio file isn't corrupted
   - Verify the audio format is supported (WAV, MP3, FLAC)
4. Hugging Face Model Issues:
   - Ensure you have a working internet connection for model downloads
   - Check that you have sufficient disk space for model storage
   - For CUDA acceleration, make sure you have compatible NVIDIA drivers

## Module Architecture
Below is a diagram showing the dependencies between the main modules in the application:

```mermaid
graph TD
    main[main.py] --> gui[modules/gui]
    main --> config[modules/config]
    gui --> audio[modules/audio]
    gui --> utils[modules/utils]
    gui --> config
    audio --> utils
    audio --> config
    
    %% Detailed submodules
    gui --> gui_tabs[gui/tabs.py]
    gui --> gui_player[gui/audio_player.py]
    gui --> gui_conversion[gui/conversion_handler.py]
    gui --> gui_queue[gui/queue_manager.py]
    gui --> gui_settings[gui/settings_tab.py]
    gui --> gui_tts[gui/text_to_speech_tab.py]
    
    audio --> audio_processor[audio/audio_processor.py]
    audio --> huggingface[audio/huggingface_models.py]
    
    utils --> error_handler[utils/error_handler.py]
    utils --> logging[utils/logging_utils.py]
    utils --> progress[utils/progress_tracker.py]
    utils --> task_manager[utils/task_manager.py]
    
    config --> config_manager[config/config_manager.py]
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.