"""
Text-to-speech adapter for the Speech UI.

This module provides a PyQt wrapper around the TTS adapters.
"""

import os
import time
import threading
import random
import math
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# Import the centralized logger
from speech_mcp_echo.utils.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__, component="tts")

# Import centralized constants
from speech_mcp_echo.constants import ENV_TTS_VOICE

class TTSAdapter(QObject):
    """
    Text-to-speech adapter for PyQt UI.
    
    This class provides a Qt wrapper around the TTS adapters to integrate with PyQt signals.
    """
    speaking_finished = pyqtSignal()
    speaking_started = pyqtSignal()
    speaking_progress = pyqtSignal(float)  # Progress between 0.0 and 1.0
    audio_level = pyqtSignal(float)  # Audio level for visualization
    
    def __init__(self):
        super().__init__()
        self.tts_engine = None
        self.is_speaking = False
        self._speaking_lock = threading.Lock()  # Add a lock for thread safety
        self.available_voices = []
        self.current_voice = None
        self.initialize_tts()
    
    def initialize_tts(self):
        """Initialize the TTS engine using the adapter system"""
        try:
            logger.info("Initializing TTS using adapter system")

            # Try Google Cloud TTS first (primary engine for this project)
            try:
                logger.info("Trying to initialize Google Cloud TTS adapter")
                from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS
                self.tts_engine = GoogleCloudTTS()
                if self.tts_engine.is_initialized:
                    logger.info("Google Cloud TTS adapter initialized successfully")
                else:
                    logger.warning("Google Cloud TTS adapter initialization failed")
                    raise ImportError("Google Cloud TTS initialization failed")
            except ImportError as e:
                logger.warning(f"Failed to initialize Google Cloud TTS adapter: {e}")
                # Fall back to OpenAI TTS
                try:
                    logger.info("Falling back to OpenAI TTS adapter")
                    from speech_mcp_echo.tts_adapters.openai_tts_adapter import OpenAITTS
                    self.tts_engine = OpenAITTS()
                    if self.tts_engine.is_initialized:
                        logger.info("OpenAI TTS adapter initialized successfully")
                    else:
                        logger.warning("OpenAI TTS adapter initialization failed")
                        raise ImportError("OpenAI TTS initialization failed")
                except ImportError as e:
                    logger.error(f"Failed to initialize OpenAI TTS adapter: {e}")
                    self.tts_engine = None
            except Exception as e:
                logger.error(f"Error initializing Google Cloud TTS: {e}")
                # Fall back to OpenAI TTS
                try:
                    logger.info("Falling back to OpenAI TTS adapter")
                    from speech_mcp_echo.tts_adapters.openai_tts_adapter import OpenAITTS
                    self.tts_engine = OpenAITTS()
                    if self.tts_engine.is_initialized:
                        logger.info("OpenAI TTS adapter initialized successfully")
                    else:
                        logger.warning("OpenAI TTS adapter initialization failed")
                        raise ImportError("OpenAI TTS initialization failed")
                except ImportError as e:
                    logger.error(f"Failed to initialize OpenAI TTS adapter: {e}")
                    self.tts_engine = None
                except Exception as e:
                    logger.error(f"Error initializing OpenAI TTS: {e}")
                    self.tts_engine = None

            # If we have a TTS engine, get the available voices
            if self.tts_engine:
                self.available_voices = self.tts_engine.get_available_voices()
                self.current_voice = self.tts_engine.voice
                logger.info(f"TTS initialized with {len(self.available_voices)} voices, current voice: {self.current_voice}")
                return True
            else:
                logger.error("No TTS engine available")
                return False

        except Exception as e:
            logger.error(f"Error initializing TTS: {e}")
            return False
    
    def speak(self, text):
        """Speak the given text"""
        if not text:
            logger.warning("Empty text provided to speak")
            return False
        
        if not self.tts_engine:
            logger.warning("No TTS engine available")
            return False
        
        # Use a lock to safely check and update speaking state
        with self._speaking_lock:
            if self.is_speaking:
                logger.warning("Already speaking, ignoring new request")
                return False
            
            # Set speaking state before starting thread
            self.is_speaking = True
        
        logger.info(f"TTSAdapter.speak called with text: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # Emit speaking started signal on the main thread
        self.speaking_started.emit()
        
        # Start speaking in a separate thread
        speak_thread = threading.Thread(target=self._speak_thread, args=(text,), daemon=True)
        speak_thread.start()
        logger.debug("Started _speak_thread")
        return True
    
    def emit_audio_level(self):
        """Emit audio level signal for visualization"""
        # Use the lock to safely check the speaking state
        with self._speaking_lock:
            is_speaking = self.is_speaking
        
        if not is_speaking:
            if hasattr(self, 'audio_level_timer') and self.audio_level_timer.isActive():
                self.audio_level_timer.stop()
            self.audio_level.emit(0.0)  # Reset to zero when not speaking
            return
        
        # When speaking, we don't need to emit actual levels since we're using pre-recorded patterns
        # Just emit a dummy signal to trigger visualization updates
        self.audio_level.emit(0.5)
    
    def _speak_thread(self, text):
        """Thread function for speaking text"""
        try:
            logger.info(f"_speak_thread started for text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Use the TTS engine's speak method
            if hasattr(self.tts_engine, 'speak'):
                # This is one of our adapters
                logger.info("Using TTS adapter speak method")
                try:
                    result = self.tts_engine.speak(text)
                    logger.info(f"TTS speak result: {result}")
                    if not result:
                        logger.error("TTS failed")
                except Exception as e:
                    logger.error(f"Exception in TTS speak: {e}", exc_info=True)
                    result = False
            elif hasattr(self.tts_engine, 'say'):
                # This is direct pyttsx3
                logger.info("Using direct pyttsx3 say method")
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                logger.info("pyttsx3 speech completed")
            else:
                logger.error("TTS engine does not have speak or say method")
            
            logger.info("Speech completed")
        except Exception as e:
            logger.error(f"Error during text-to-speech: {e}", exc_info=True)
        finally:
            # Use the lock to safely update the speaking state
            with self._speaking_lock:
                self.is_speaking = False
            
            # Emit the signal after releasing the lock
            self.speaking_finished.emit()
            logger.info("Speaking finished signal emitted")
    
    def set_voice(self, voice_id):
        """Set the voice to use for TTS"""
        if not self.tts_engine:
            logger.warning("No TTS engine available")
            return False
        
        try:
            if hasattr(self.tts_engine, 'set_voice'):
                # This is one of our adapters
                result = self.tts_engine.set_voice(voice_id)
                if result:
                    self.current_voice = voice_id
                    logger.info(f"Voice set to: {voice_id}")
                    return True
                else:
                    logger.error(f"Failed to set voice to: {voice_id}")
                    return False
            elif hasattr(self.tts_engine, 'setProperty'):
                # This is direct pyttsx3
                # Extract the voice ID from the format "pyttsx3:voice_id"
                if voice_id.startswith("pyttsx3:"):
                    voice_id = voice_id.split(":", 1)[1]
                
                # Find the voice object
                for voice in self.tts_engine.getProperty('voices'):
                    if voice.id == voice_id:
                        self.tts_engine.setProperty('voice', voice.id)
                        self.current_voice = f"pyttsx3:{voice.id}"
                        logger.info(f"Voice set to: {voice.name}")
                        return True
                
                logger.error(f"Voice not found: {voice_id}")
                return False
            
            logger.warning("TTS engine does not support voice selection")
            return False
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
    
    def get_available_voices(self):
        """Get a list of available voices"""
        return self.available_voices

    def get_current_voice(self):
        """Get the current voice"""
        return self.current_voice

    def get_current_engine(self):
        """Get the current TTS engine name"""
        if self.tts_engine is None:
            return None
        engine_class = type(self.tts_engine).__name__
        if "Google" in engine_class:
            return "google"
        elif "OpenAI" in engine_class:
            return "openai"
        return engine_class.lower()

    def set_engine(self, engine_name: str) -> bool:
        """Switch to a different TTS engine"""
        try:
            logger.info(f"Switching TTS engine to: {engine_name}")

            if engine_name == "google":
                from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS
                self.tts_engine = GoogleCloudTTS()
            elif engine_name == "openai":
                from speech_mcp_echo.tts_adapters.openai_tts_adapter import OpenAITTS
                self.tts_engine = OpenAITTS()
            else:
                logger.error(f"Unknown TTS engine: {engine_name}")
                return False

            if self.tts_engine and self.tts_engine.is_initialized:
                self.available_voices = self.tts_engine.get_available_voices()
                self.current_voice = self.tts_engine.voice
                logger.info(f"Switched to {engine_name} with {len(self.available_voices)} voices")
                return True
            else:
                logger.error(f"Failed to initialize {engine_name} TTS")
                return False

        except ImportError as e:
            logger.error(f"Failed to import {engine_name} TTS adapter: {e}")
            return False
        except Exception as e:
            logger.error(f"Error switching to {engine_name} TTS: {e}")
            return False