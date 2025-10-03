import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field
from dataclasses import dataclass
from ollama import Client
from openai import OpenAI

@dataclass
class ServerConfig:
    """Server configuration settings"""
    host: str = "0.0.0.0"
    port: int = 7999
    pid_file: str = "/opt/OllamaProxy.pid"


@dataclass
class ChatClientConfig:
    mode: str = "openai" # "openai" or "ollama"
    key_file: str = "openai_key.txt"
    base_url: str = "http://localhost:11434"
    valid_models: list = Field(default_factory=list)


@dataclass
class AudioClientConfig:
    mode: str = "openai" # "openai" or "kokoro"
    key_file: str = "openai_key.txt"
    base_url: str = "http://localhost:8880/v1"
    default_voice: str = "alloy"
    default_model: str = "tts-1"
    valid_voices: list = Field(default_factory=list)
    valid_models: list = Field(default_factory=list)

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

@dataclass
class AITalkmasterConfig:
    """AI Theater specific configuration"""
    max_active_plays: int = 100
    response_timeout: int = 60


@dataclass
class PathsConfig:
    """File path configuration"""
    log_file: str = "logfile.txt"

@dataclass
class TheaterConfig:
    """AI Theater configuration"""
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
        self._ollama_audio_client: Optional[Any] = None
        self._openai_chat_client: Optional[Any] = None
        self._openai_audio_client: Optional[Any] = None
        
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
        self.server = ServerConfig(
            host=server_data.get('host', '0.0.0.0'),
            port=server_data.get('port', 7999),
            pid_file=server_data.get('pid_file', '/opt/OllamaProxy.pid')
        )
        
        # Ollama configuration
        chat_client_data = self.config_data.get('chat_client', {})
        self.chat_client = ChatClientConfig(
            mode=chat_client_data.get('mode', 'ollama'),
            base_url=chat_client_data.get('base_url', 'http://localhost:11434'),
            valid_models=chat_client_data.get('valid_models', [])
        )
        
        # OpenAI configuration
        audio_client_data = self.config_data.get('audio_client', {})
        self.audio_client = AudioClientConfig(
            mode=audio_client_data.get('mode', 'openai'),
            key_file=audio_client_data.get('key_file', 'openai_key.txt'),
            base_url=audio_client_data.get('base_url', 'http://localhost:8880/v1'),
            default_voice=audio_client_data.get('default_voice', 'alloy'),
            default_model=audio_client_data.get('default_model', 'tts-1'),
            valid_voices=audio_client_data.get('valid_voices', ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]),
            valid_models=audio_client_data.get('valid_models', ["tts-1", "tts-1-hd", "gpt-4o-mini-tts", "kokoro"])
        )
        
        # Liquidsoap client configuration (optional)
        liquidsoap_client_data = self.config_data.get('liquidsoap_client')
        if liquidsoap_client_data:
            self.liquidsoap_client = LiquidsoapClientConfig(
                host=liquidsoap_client_data.get('host', 'localhost'),
                telnet_port=liquidsoap_client_data.get('telnet_port', 1234),
            )
        else:
            self.liquidsoap_client = None
        
        # Icecast client configuration (optional)
        icecast_client_data = self.config_data.get('icecast_client')
        if icecast_client_data:
            self.icecast_client = IcecastClientConfig(
                host=icecast_client_data.get('host', 'localhost'),
                port=icecast_client_data.get('port', 8000),
                admin_password=icecast_client_data.get('admin_password', 'password'),
            )
        else:
            self.icecast_client = None
        
        # Paths configuration
        paths_data = self.config_data.get('paths', {})
        self.paths = PathsConfig(
            log_file=paths_data.get('log_file', 'logfile.txt')
        )
        
        # Theater configuration
        theater_data = self.config_data.get('theater', {})
        self.theater = TheaterConfig(
            join_key_keep_alive_list=theater_data.get('join_key_keep_alive_list', [])
        )
    
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
        
        with open(key_file, "r") as f:
            key = f.read().strip()
            if not key:
                raise ValueError("OpenAI key file is empty")
            return key
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all configuration settings
        
        Returns:
            Dictionary containing all configuration settings
        """
        return {
            'server': {
                'host': self.server.host,
                'port': self.server.port
            },
            'chat_client': {
                'mode': self.chat_client.mode,
                'url': self.chat_client.base_url,
                'valid_models': self.chat_client.valid_models
            },
            'audio_client': {
                'mode': self.audio_client.mode,
                'key_file': self.audio_client.key_file,
                'base_url': self.audio_client.base_url,
                'default_voice': self.audio_client.default_voice,
                'default_model': self.audio_client.default_model,
                'valid_voices': self.audio_client.valid_voices,
                'valid_models': self.audio_client.valid_models
            },
            'liquidsoap_client': {
                'host': self.liquidsoap_client.host,
                'telnet_port': self.liquidsoap_client.telnet_port,
            } if self.liquidsoap_client else None,
            'icecast_client': {
                'host': self.icecast_client.host,
                'port': self.icecast_client.port,
                'admin_password': self.icecast_client.admin_password
            } if self.icecast_client else None,
            'paths': {
                'log_file': self.paths.log_file
            },
            'theater': {
                'join_key_keep_alive_list': self.theater.join_key_keep_alive_list
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
    
    def get_or_create_ollama_audio_client(self) -> OpenAI:
        """
        Get or create Ollama audio client instance (for Kokoro)
        
        Returns:
            OpenAI Client instance configured for Kokoro audio server
        """
        if self._ollama_audio_client is None:
            from openai import OpenAI
            self._ollama_audio_client = OpenAI(
                base_url=self.audio_client.base_url, 
                api_key="kokoro"
            )
        return self._ollama_audio_client
    
    def get_or_create_openai_chat_client(self) -> OpenAI:
        """
        Get or create OpenAI chat client instance
        
        Returns:
            OpenAI Client instance for chat operations
        """
        if self._openai_chat_client is None:
            from openai import OpenAI
            self._openai_chat_client = OpenAI(api_key=self.get_openai_key_from_file(self.chat_client.key_file))

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
    
    def reload(self):
        """Reload configuration from file"""
        # Clear client instances to force recreation with new config
        self._ollama_chat_client = None
        self._ollama_audio_client = None
        self._openai_chat_client = None
        self._openai_audio_client = None
        
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
