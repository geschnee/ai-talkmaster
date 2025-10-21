import yaml
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import Field
from dataclasses import dataclass
from enum import Enum
from ollama import Client
from openai import OpenAI

def log(message):
    with open("./logs/config_logfile.txt", "a") as file:
        file.write(message + "\n")
    print(message)

class ConfigurationValidationError(Exception):
    """Exception raised when configuration validation fails"""
    pass

class ChatClientMode(Enum):
    """Enum for chat client modes"""
    OLLAMA = "ollama"
    OPENAI = "openai"

class AudioClientMode(Enum):
    """Enum for audio client modes"""
    OPENAI = "openai"
    KOKORO = "kokoro"

@dataclass
class UsageConfig:
    """Usage and rate limiting configuration"""
    use_rate_limit: bool = False
    rate_limit_xForwardedFor: bool = False
    rate_limit_per_day: int = 100000
    audio_cost_per_second: float = 100

@dataclass
class ServerConfig:
    """Server configuration settings"""
    host: str = "0.0.0.0"
    port: int = 6000
    log_file: str = "logfile.txt"
    usage: UsageConfig = None
    


@dataclass
class ChatClientConfig:
    mode: ChatClientMode
    key_file: str = ""
    base_url: str = ""
    default_model: str = "llama3.2"
    allowed_models: list = Field(default_factory=list)

@dataclass
class AudioClientConfig:
    mode: AudioClientMode
    key_file: str = ""
    base_url: str = ""
    default_voice: str = "alloy"
    default_model: str = "tts-1"
    allowed_voices: list = Field(default_factory=list)
    allowed_models: list = Field(default_factory=list)

@dataclass
class LiquidsoapClientConfig:
    """Liquidsoap client configuration"""
    host: str = "localhost"
    telnet_port: int = 1234

@dataclass
class IcecastClientConfig:
    """Icecast client configuration"""
    host: str = "localhost"
    port: int = 8000
    admin_user: str = "admin"
    admin_password: str = "password"
    stream_endpoint_prefix: str = ""


@dataclass
class AitalkmasterConfig:
    """AI Talkmaster configuration"""
    join_key_keep_alive_list: list = Field(default_factory=list)


class Config:
    """
    Main configuration class that loads and manages all configuration settings
    """
    
    def __init__(self, config_file: str = "config.yml"):
        """
        Initialize configuration from YAML file
        
        Args:
            config_file: Path to the YAML configuration file
        """
        self.config_file = config_file
        self.config_data = {}
        
        # Client instances storage
        self._ollama_chat_client: Optional[Any] = None
        self._opensource_audio_client: Optional[Any] = None
        self._openai_chat_client: Optional[Any] = None
        self._openai_audio_client: Optional[Any] = None
        
        # Validation results storage
        self._validation_results: Optional[Dict[str, Any]] = None
        
        self._load_config()
        self._setup_config_objects()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration file: {e}")
    
    def _setup_config_objects(self):
        """Setup configuration objects from loaded data"""
        # Server configuration
        server_data = self.config_data.get('server', {})
        usage_data = server_data.get('usage', {})
        
        self.server = ServerConfig(
            host=server_data.get('host'),
            port=server_data.get('port'),
            log_file=server_data.get('log_file'),
            usage=UsageConfig(
                use_rate_limit=usage_data.get('use_rate_limit'),
                rate_limit_xForwardedFor=usage_data.get('rate_limit_xForwardedFor'),
                rate_limit_per_day=usage_data.get('rate_limit_per_day'),
                audio_cost_per_second=usage_data.get('audio_cost_per_second')
            )
        )
        
        # Chat client configuration
        chat_client_data = self.config_data.get('chat_client', {})
        chat_mode = chat_client_data.get('mode')
        if chat_mode is None:
            raise ConfigurationValidationError("Chat client mode is required but not specified")
        
        try:
            chat_mode = ChatClientMode(chat_mode)
        except ValueError:
            valid_modes = [mode.value for mode in ChatClientMode]
            raise ConfigurationValidationError(f"Invalid chat client mode '{chat_mode}'. Valid modes are: {valid_modes}")
        
        self.chat_client = ChatClientConfig(
            mode=chat_mode,
            key_file=chat_client_data.get('key_file'),
            base_url=chat_client_data.get('base_url'),
            default_model=chat_client_data.get('default_model'),
            allowed_models=chat_client_data.get('allowed_models')
        )
        
        # Audio client configuration (optional)
        audio_client_data = self.config_data.get('audio_client')
        if audio_client_data:
            audio_mode = audio_client_data.get('mode')
            if audio_mode is None:
                raise ConfigurationValidationError("Audio client mode is required but not specified")
            
            try:
                audio_mode = AudioClientMode(audio_mode)
            except ValueError:
                valid_modes = [mode.value for mode in AudioClientMode]
                raise ConfigurationValidationError(f"Invalid audio client mode '{audio_mode}'. Valid modes are: {valid_modes}")
            
            self.audio_client = AudioClientConfig(
                mode=audio_mode,
                key_file=audio_client_data.get('key_file'),
                base_url=audio_client_data.get('base_url'),
                default_voice=audio_client_data.get('default_voice'),
                default_model=audio_client_data.get('default_model'),
                allowed_voices=audio_client_data.get('allowed_voices'),
                allowed_models=audio_client_data.get('allowed_models')
            )
        else:
            self.audio_client = None
        
        # Liquidsoap client configuration (optional)
        liquidsoap_client_data = self.config_data.get('liquidsoap_client')
        if liquidsoap_client_data:
            self.liquidsoap_client = LiquidsoapClientConfig(
                host=liquidsoap_client_data.get('host'),
                telnet_port=liquidsoap_client_data.get('telnet_port'),
            )
        else:
            self.liquidsoap_client = None
        
        # Icecast client configuration (optional)
        icecast_client_data = self.config_data.get('icecast_client')
        if icecast_client_data:
            self.icecast_client = IcecastClientConfig(
                host=icecast_client_data.get('host'),
                port=icecast_client_data.get('port'),
                admin_password=icecast_client_data.get('admin_password'),
                stream_endpoint_prefix=icecast_client_data.get('stream_endpoint_prefix'),
            )
        else:
            self.icecast_client = None
        
        # Aitalkmaster configuration
        aitalkmaster_data = self.config_data.get('aitalkmaster', {})
        self.aitalkmaster = AitalkmasterConfig(
            join_key_keep_alive_list=aitalkmaster_data.get('join_key_keep_alive_list')
        )
        
        # Validate all configured models and voices
        self._validate_configuration()
    
    def _validate_configuration(self):
        """
        Internal method to validate configuration during setup.
        This is called after all config objects are created.
        Raises ConfigurationValidationError if validation fails.
        """
        try:
            validation_results = self.validate_all_models_and_voices()

            # Store validation results for potential use
            self._validation_results = validation_results
            
            # Check if validation failed and raise exception
            if not validation_results["overall_valid"]:
                error_messages = []
                
                # Collect all validation errors
                if not validation_results["chat_models"]["valid"]:
                    invalid_models = validation_results["chat_models"]["invalid"]
                    available_models = validation_results["chat_models"]["available"]
                    error_messages.append(f"Invalid chat models: {invalid_models}. Available: {available_models}")
                
                if not validation_results["audio_voices"]["valid"]:
                    invalid_voices = validation_results["audio_voices"]["invalid"]
                    available_voices = validation_results["audio_voices"]["available"]
                    error_messages.append(f"Invalid audio voices: {invalid_voices}. Available: {available_voices}")
                
                if not validation_results["audio_models"]["valid"]:
                    invalid_models = validation_results["audio_models"]["invalid"]
                    available_models = validation_results["audio_models"]["available"]
                    error_messages.append(f"Invalid audio models: {invalid_models}. Available: {available_models}")
                
                # Raise exception with detailed error message
                error_message = "Configuration validation failed:\n" + "\n".join(error_messages)
                log(f"FATAL: {error_message}")
                raise ConfigurationValidationError(error_message)
            else:
                log("Configuration validation completed successfully.")
                
        except ConfigurationValidationError:
            # Re-raise configuration validation errors
            raise
        except Exception as e:
            log(f"FATAL: Error during configuration validation: {e}")
            raise ConfigurationValidationError(f"Configuration validation failed: {e}")
    
    def get_openai_key_from_file(self, file_path: str) -> str:
        """
        Read OpenAI API key from file
        
        Returns:
            OpenAI API key string
            
        Raises:
            FileNotFoundError: If key file doesn't exist
            ValueError: If key file is empty
        """

        key_file = Path(file_path)
        
        if not key_file.exists():
            raise FileNotFoundError(f"OpenAI key file not found at {key_file}")

        if key_file.is_dir():
            raise ValueError(f"OpenAI key file is a directory: {key_file}")
        
        with open(key_file, "r") as f:
            key = f.read().strip()
            if not key:
                raise ValueError("OpenAI key file is empty")
            return key
    
    def get_config_summary(self) -> Dict[str, Any]:
        return {
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'log_file': self.server.log_file,
                'usage': {
                    'use_rate_limit': self.server.usage.use_rate_limit,
                    'rate_limit_xForwardedFor': self.server.usage.rate_limit_xForwardedFor,
                    'rate_limit_per_day': self.server.usage.rate_limit_per_day,
                    'audio_cost_per_second': self.server.usage.audio_cost_per_second
                }
            },
            'chat_client': {
                'mode': self.chat_client.mode,
                'url': self.chat_client.base_url,
                'default_model': self.chat_client.default_model,
                'allowed_models': self.chat_client.allowed_models
            },
            'audio_client': {
                'mode': self.audio_client.mode,
                'key_file': self.audio_client.key_file,
                'base_url': self.audio_client.base_url,
                'default_voice': self.audio_client.default_voice,
                'default_model': self.audio_client.default_model,
                'allowed_voices': self.audio_client.allowed_voices,
                'allowed_models': self.audio_client.allowed_models
            } if self.audio_client else None,
            'liquidsoap_client': {
                'host': self.liquidsoap_client.host,
                'telnet_port': self.liquidsoap_client.telnet_port,
            } if self.liquidsoap_client else None,
            'icecast_client': {
                'host': self.icecast_client.host,
                'port': self.icecast_client.port,
                'admin_password': self.icecast_client.admin_password,
                'stream_endpoint_prefix': self.icecast_client.stream_endpoint_prefix
            } if self.icecast_client else None,
            'aitalkmaster': {
                'join_key_keep_alive_list': self.aitalkmaster.join_key_keep_alive_list
            }
        }
    
    def get_or_create_ollama_chat_client(self) -> Client:
        """
        Get or create Ollama chat client instance
        
        Returns:
            Ollama Client instance for chat operations
        """
        if self._ollama_chat_client is None:
            from ollama import Client
            self._ollama_chat_client = Client(host=self.chat_client.base_url)
        return self._ollama_chat_client
    
    def get_or_create_opensource_audio_client(self) -> OpenAI:
        
        if self._opensource_audio_client is None:
            from openai import OpenAI
            self._opensource_audio_client = OpenAI(
                base_url=self.audio_client.base_url, 
                api_key="kokoro"
            )
        return self._opensource_audio_client
    
    def get_or_create_openai_chat_client(self) -> OpenAI:
        """
        Get or create OpenAI chat client instance
        
        Returns:
            OpenAI Client instance for chat operations
        """
        if self._openai_chat_client is None:
            from openai import OpenAI
            if self.chat_client.base_url == "":
                self._openai_chat_client = OpenAI(api_key=self.get_openai_key_from_file(self.chat_client.key_file))
            else:
                self._openai_chat_client = OpenAI(base_url=self.chat_client.base_url, api_key=self.get_openai_key_from_file(self.chat_client.key_file))

        return self._openai_chat_client
    
    def get_or_create_openai_audio_client(self) -> OpenAI:
        """
        Get or create OpenAI audio client instance
        
        Returns:
            OpenAI Client instance for audio operations
        """
        if self._openai_audio_client is None:
            from openai import OpenAI
            self._openai_audio_client = OpenAI(api_key=self.get_openai_key_from_file(self.audio_client.key_file))
        return self._openai_audio_client
    
    def _get_available_chat_models(self) -> List[str]:
        """
        Get available chat models from the configured chat client.
        
        Returns:
            List of available model names
        """
        available_models = []
        
        if self.chat_client.mode == ChatClientMode.OPENAI:
            try:
                openai_client = self.get_or_create_openai_chat_client()
                openai_models = openai_client.models.list()
                available_models = [model.id for model in openai_models.data]
            except Exception as e:
                log(f"FATAL: Could not fetch OpenAI models: {e}")
                raise ConfigurationValidationError(f"Failed to fetch OpenAI models: {e}")
                
        elif self.chat_client.mode == ChatClientMode.OLLAMA:
            try:
                if self.chat_client.base_url == "":
                    raise ConfigurationValidationError("Base URL for chat client with mode ollama is not set")

                response = requests.get(f"{self.chat_client.base_url}/api/tags", timeout=10)
                response.raise_for_status()
                jsondata = response.json()
                available_models = [model["name"] for model in jsondata["models"]]
                for m in [model["name"].split(":")[0] for model in jsondata["models"]]:
                    if m not in available_models:
                        available_models.append(m)
            except Exception as e:
                log(f"FATAL: Could not fetch Ollama models: {e}")
                raise ConfigurationValidationError(f"Failed to fetch Ollama models: {e}")
        else:
            log(f"FATAL: Unknown chat client mode: {self.chat_client.mode}")
            raise ConfigurationValidationError(f"Unknown chat client mode: {self.chat_client.mode}")
        
        return available_models
    
    def _get_available_audio_voices(self) -> List[str]:
        """
        Get available audio voices from the configured audio client.
        
        Returns:
            List of available voice names
        """
        if self.audio_client is None:
            return []
        
        available_voices = []
        
        if self.audio_client.mode == AudioClientMode.OPENAI:
            # OpenAI TTS voices are predefined, so we use the standard list
            available_voices = ["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
        
        elif self.audio_client.mode == AudioClientMode.KOKORO:
            # For Kokoro, we need to check the server
            try:
                # Try to get available voices from Kokoro server
                response = requests.get(f"{self.audio_client.base_url}/audio/voices", timeout=10)
                if response.status_code == 200:
                    voices_data = response.json()
                    
                    available_voices = voices_data["voices"]
                else:
                    log(f"FATAL: Could not fetch Kokoro voices (status {response.status_code})")
                    raise ConfigurationValidationError(f"Failed to fetch Kokoro voices (status {response.status_code})")
            except Exception as e:
                log(f"FATAL: Could not fetch Kokoro voices: {e}")
                raise ConfigurationValidationError(f"Failed to fetch Kokoro voices: {e}")
        else:
            log(f"FATAL: Unknown audio client mode: {self.audio_client.mode}")
            raise ConfigurationValidationError(f"Unknown audio client mode: {self.audio_client.mode}")
        
        return available_voices
    
    def _get_available_audio_models(self) -> List[str]:
        """
        Get available audio models from the configured audio client.
        
        Returns:
            List of available model names
        """
        if self.audio_client is None:
            return []
        
        available_models = []
        
        if self.audio_client.mode == AudioClientMode.OPENAI:
            openai_models = self.get_or_create_openai_audio_client().models.list()
            available_models = [model.id for model in openai_models.data]
        elif self.audio_client.mode == AudioClientMode.KOKORO:
            # For Kokoro, we need to check the server

            if self.audio_client.base_url == "":
                raise ConfigurationValidationError("Base URL for audio client with mode kokoro is not set")

            try:
                # Try to get available models from Kokoro server
                response = requests.get(f"{self.audio_client.base_url}/models", timeout=10)
                if response.status_code == 200:
                    models_data = response.json()["data"]
                    available_models = [model["id"] for model in models_data]
                else:
                    log(f"FATAL: Could not fetch Kokoro models (status {response.status_code})")
                    raise ConfigurationValidationError(f"Failed to fetch Kokoro models (status {response.status_code})")
            except Exception as e:
                log(f"FATAL: Could not fetch Kokoro models: {e}")
                raise ConfigurationValidationError(f"Failed to fetch Kokoro models: {e}")
        else:
            log(f"FATAL: Unknown audio client mode: {self.audio_client.mode}")
            raise ConfigurationValidationError(f"Unknown audio client mode: {self.audio_client.mode}")
        
        return available_models
    
    def validate_chat_default_model(self) -> Tuple[bool, str, List[str]]:
        """
        Validate the default chat model against available models from the client.
        
        Returns:
            Tuple of (is_valid, default_model, available_models)
        """
        try:
            available_models = self._get_available_chat_models()
            
            # Check if default model is available
            is_valid = self.chat_client.default_model in available_models
            
            return is_valid, self.chat_client.default_model, available_models
            
        except ConfigurationValidationError:
            # Re-raise configuration validation errors
            raise
        except Exception as e:
            log(f"FATAL: Error validating chat default model: {e}")
            raise ConfigurationValidationError(f"Error validating chat default model: {e}")

    def validate_chat_models(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all configured chat models against available models from the client.
        
        Returns:
            Tuple of (all_valid, invalid_models, available_models)
        """
        if not self.chat_client.allowed_models:
            raise ConfigurationValidationError("No chat models to validate")
        
        try:
            available_models = self._get_available_chat_models()
            
            # Check which configured models are not available
            invalid_models = [model for model in self.chat_client.allowed_models if model not in available_models]
            
            return len(invalid_models) == 0, invalid_models, available_models
            
        except ConfigurationValidationError:
            # Re-raise configuration validation errors
            raise
        except Exception as e:
            log(f"FATAL: Error validating chat models: {e}")
            raise ConfigurationValidationError(f"Error validating chat models: {e}")
    
    def validate_audio_models(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all configured audio models against available models from the client.
        
        Returns:
            Tuple of (all_valid, invalid_models, available_models)
        """
        
        if self.audio_client is None:
            # No audio client configured, validation passes
            return True, [], []
        
        if not self.audio_client.allowed_models:
            raise ConfigurationValidationError("No audio models to validate")
        
        try:
            available_models = self._get_available_audio_models()
            
            # Check which configured models are not available
            invalid_models = [model for model in self.audio_client.allowed_models if model not in available_models]
            
            return len(invalid_models) == 0, invalid_models, available_models
            
        except ConfigurationValidationError:
            # Re-raise configuration validation errors
            raise
        except Exception as e:
            log(f"FATAL: Error validating audio models: {e}")
            raise ConfigurationValidationError(f"Error validating audio models: {e}")
    

    def validate_audio_default_voice(self) -> Tuple[bool, str, List[str]]:
        """
        Validate the default audio voice against available voices from the client.
        
        Returns:
            Tuple of (is_valid, default_voice, available_voices)
        """
        if self.audio_client is None:
            # No audio client configured, validation passes
            return True, "", []
        
        try:
            available_voices = self._get_available_audio_voices()
            
            # Check if default voice is available
            is_valid = self.audio_client.default_voice in available_voices
            
            return is_valid, self.audio_client.default_voice, available_voices
            
        except ConfigurationValidationError:
            # Re-raise configuration validation errors
            raise
        except Exception as e:
            log(f"FATAL: Error validating audio default voice: {e}")
            raise ConfigurationValidationError(f"Error validating audio default voice: {e}")

    def validate_audio_voices(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all configured audio voices against available voices from the client.
        
        Returns:
            Tuple of (all_valid, invalid_voices, available_voices)
        """
        if self.audio_client is None:
            # No audio client configured, validation passes
            return True, [], []
        
        if not self.audio_client.allowed_voices:
            raise ConfigurationValidationError("No audio voices to validate, specify a list of allowed voices in config")
        
        try:
            available_voices = self._get_available_audio_voices()
            
            # Check which configured voices are not available
            invalid_voices = [voice for voice in self.audio_client.allowed_voices if voice not in available_voices]
            
            return len(invalid_voices) == 0, invalid_voices, available_voices
            
        except ConfigurationValidationError:
            # Re-raise configuration validation errors
            raise
        except Exception as e:
            log(f"FATAL: Error validating audio voices: {e}")
            raise ConfigurationValidationError(f"Error validating audio voices: {e}")

    def validate_all_models_and_voices(self) -> Dict[str, Any]:
        """
        Validate all configured models and voices.
        
        Returns:
            Dictionary with validation results
        """
        log("Validating configured models and voices...")
        
        results = {
            "chat_models": {"valid": True, "invalid": [], "available": []},
            "chat_default_model": {"valid": True, "default_model": "", "available": []},
            "audio_voices": {"valid": True, "invalid": [], "available": []},
            "audio_default_voice": {"valid": True, "default_voice": "", "available": []},
            "audio_models": {"valid": True, "invalid": [], "available": []},
            "overall_valid": True
        }
        
        # Validate chat models
        try:
            chat_valid, chat_invalid, chat_available = self.validate_chat_models()
            results["chat_models"] = {
                "valid": chat_valid,
                "invalid": chat_invalid,
                "available": chat_available
            }
            
            if not chat_valid:
                log(f"FATAL: Invalid chat models: {chat_invalid}")
                log(f"Available chat models: {chat_available}")
                results["overall_valid"] = False
        except ConfigurationValidationError as e:
            log(f"FATAL: Chat model validation failed: {e}")
            results["chat_models"] = {"valid": False, "invalid": self.chat_client.allowed_models, "available": []}
            results["overall_valid"] = False
        
        # Validate chat default model
        try:
            default_valid, default_model, default_available = self.validate_chat_default_model()
            results["chat_default_model"] = {
                "valid": default_valid,
                "default_model": default_model,
                "available": default_available
            }
            
            if not default_valid:
                log(f"FATAL: Invalid chat default model: {default_model}")
                log(f"Available chat models: {default_available}")
                results["overall_valid"] = False
        except ConfigurationValidationError as e:
            log(f"FATAL: Chat default model validation failed: {e}")
            results["chat_default_model"] = {"valid": False, "default_model": self.chat_client.default_model, "available": []}
            results["overall_valid"] = False
        
        # Validate audio models
        try:
            if self.audio_client is not None:
                model_valid, model_invalid, model_available = self.validate_audio_models()
                results["audio_models"] = {
                    "valid": model_valid,
                    "invalid": model_invalid,
                    "available": model_available
                }
                
                if not model_valid:
                    log(f"FATAL: Invalid audio models: {model_invalid}")
                    log(f"Available audio models: {model_available}")
                    results["overall_valid"] = False
            else:
                log("No audio client configured, skipping model validation")
                results["audio_models"] = {"valid": True, "invalid": [], "available": []}
        except ConfigurationValidationError as e:
            log(f"FATAL: Audio model validation failed: {e}")
            results["audio_models"] = {"valid": False, "invalid": self.audio_client.allowed_models if self.audio_client else [], "available": []}
            results["overall_valid"] = False


        # Validate audio voices
        try:
            if self.audio_client is not None:
                voice_valid, voice_invalid, voice_available = self.validate_audio_voices()
                results["audio_voices"] = {
                    "valid": voice_valid,
                    "invalid": voice_invalid,
                    "available": voice_available
                }
                
                if not voice_valid:
                    log(f"FATAL: Invalid audio voices: {voice_invalid}")
                    log(f"Available audio voices: {voice_available}")
                    results["overall_valid"] = False
            else:
                log("No audio client configured, skipping voice validation")
                results["audio_voices"] = {"valid": True, "invalid": [], "available": []}
        except ConfigurationValidationError as e:
            log(f"FATAL: Audio voice validation failed: {e}")
            results["audio_voices"] = {"valid": False, "invalid": self.audio_client.allowed_voices if self.audio_client else [], "available": []}
            results["overall_valid"] = False
        
        # Validate audio default voice
        try:
            if self.audio_client is not None:
                default_voice_valid, default_voice, default_voice_available = self.validate_audio_default_voice()
                results["audio_default_voice"] = {
                    "valid": default_voice_valid,
                    "default_voice": default_voice,
                    "available": default_voice_available
                }
                
                if not default_voice_valid:
                    log(f"FATAL: Invalid audio default voice: {default_voice}")
                    log(f"Available audio voices: {default_voice_available}")
                    results["overall_valid"] = False
            else:
                log("No audio client configured, skipping default voice validation")
                results["audio_default_voice"] = {"valid": True, "default_voice": "", "available": []}
        except ConfigurationValidationError as e:
            log(f"FATAL: Audio default voice validation failed: {e}")
            results["audio_default_voice"] = {"valid": False, "default_voice": self.audio_client.default_voice if self.audio_client else "", "available": []}
            results["overall_valid"] = False
        
        
        if results["overall_valid"]:
            log("All configured models and voices are valid!")
        else:
            log("FATAL: Some configured models or voices are invalid. Server startup will fail.")
        
        return results
    
    def get_validation_results(self) -> Optional[Dict[str, Any]]:
        """
        Get the validation results from the last configuration load.
        
        Returns:
            Dictionary with validation results or None if not validated yet
        """
        return self._validation_results

    def reload(self):
        """Reload configuration from file"""
        # Clear client instances to force recreation with new config
        self._ollama_chat_client = None
        self._opensource_audio_client = None
        self._openai_chat_client = None
        self._openai_audio_client = None
        
        # Clear validation results
        self._validation_results = None
        
        self._load_config()
        self._setup_config_objects()


# Global configuration instance
config = Config()

def get_config() -> Config:
    """
    Get the global configuration instance
    
    Returns:
        Config instance
    """
    return config


def reload_config():
    """Reload the global configuration"""
    global config
    config.reload()
