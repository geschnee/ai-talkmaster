#!/usr/bin/env python3
"""
Test script for the configuration system
"""

from config import get_config, reload_config
import json

def test_config_loading():
    """Test basic configuration loading"""
    print("Testing configuration loading...")
    
    try:
        config = get_config()
        print("✅ Configuration loaded successfully!")
        
        # Test configuration summary
        summary = config.get_config_summary()
        print(f"✅ Configuration summary generated with {len(summary)} sections")
        
        return config
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return None

def test_config_values(config):
    """Test specific configuration values"""
    print("\nTesting configuration values...")
    
    try:
        # Test server config
        print(f"   Server: {config.server.host}:{config.server.port}")
        print(f"   PID file: {config.server.pid_file}")
        
        # Test Ollama config
        print(f"   Ollama URL: {config.ollama.url}")
        print(f"   Default temperature: {config.ollama.default_temperature}")
        
        # Test OpenAI config
        print(f"   Use OpenAI audio: {config.openai.use_audio}")
        print(f"   Default voice: {config.openai.default_voice}")
        print(f"   Default model: {config.openai.default_model}")
        print(f"   Valid voices: {config.openai.valid_voices}")
        print(f"   Valid models: {config.openai.valid_models}")
        
        # Test audio config
        print(f"   Audio directory: {config.audio.directory}")
        print(f"   Chunk size: {config.audio.chunk_size}")
        print(f"   Stream pacing: {config.audio.stream_pacing}s")
        
        # Test logging config
        print(f"   Log file: {config.logging.log_file}")
        print(f"   Log level: {config.logging.log_level}")
        
        # Test AI theater config
        print(f"   Max active plays: {config.ai_theater.max_active_plays}")
        print(f"   Response timeout: {config.ai_theater.response_timeout}s")
        
        # Test paths config
        print(f"   OpenAI key path: {config.paths.openai_key}")
        print(f"   Audio directory path: {config.paths.audio_directory}")
        print(f"   Log file path: {config.paths.log_file}")
        
        print("✅ All configuration values accessible!")
        
    except Exception as e:
        print(f"❌ Error accessing configuration values: {e}")

def test_openai_key_loading(config):
    """Test OpenAI key loading"""
    print("\nTesting OpenAI key loading...")
    
    try:
        key = config.get_openai_key()
        if key and len(key) > 10:  # Basic validation
            print(f"✅ OpenAI key loaded successfully (length: {len(key)})")
            print(f"   Key starts with: {key[:10]}...")
        else:
            print("❌ OpenAI key appears to be invalid or too short")
    except FileNotFoundError:
        print("⚠️  OpenAI key file not found (this is expected if the file doesn't exist)")
    except Exception as e:
        print(f"❌ Error loading OpenAI key: {e}")

def test_audio_directory_creation(config):
    """Test audio directory creation"""
    print("\nTesting audio directory creation...")
    
    try:
        audio_dir = config.create_audio_directory()
        print(f"✅ Audio directory created/verified: {audio_dir}")
        print(f"   Directory exists: {audio_dir.exists()}")
    except Exception as e:
        print(f"❌ Error creating audio directory: {e}")

def test_config_reload():
    """Test configuration reloading"""
    print("\nTesting configuration reload...")
    
    try:
        reload_config()
        print("✅ Configuration reloaded successfully!")
    except Exception as e:
        print(f"❌ Error reloading configuration: {e}")

def main():
    """Run all configuration tests"""
    print("🔧 Configuration System Test Suite")
    print("=" * 50)
    
    # Test basic loading
    config = test_config_loading()
    
    if config:
        # Test configuration values
        test_config_values(config)
        
        # Test OpenAI key loading
        test_openai_key_loading(config)
        
        # Test audio directory creation
        test_audio_directory_creation(config)
        
        # Test configuration reload
        test_config_reload()
    
    print("\n" + "=" * 50)
    print("🎉 Configuration test suite completed!")
    print("\nTo use the configuration in your code:")
    print("  from config import get_config")
    print("  config = get_config()")
    print("  print(config.server.host)")

if __name__ == "__main__":
    main()
