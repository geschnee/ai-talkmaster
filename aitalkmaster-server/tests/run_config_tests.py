#!/usr/bin/env python3
"""
Configuration test runner - always runs the full test suite
Usage: python run_config_tests.py
"""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from configuration_tester import ConfigurationTester


async def run_full_test():
    """Run the full test suite (chat + audio tests)"""
    print("AI Theater Configuration Tester - Full Test Suite")
    print("Running Chat and Audio Tests")
    print("=" * 50)
    
    # Read OpenAI API key from file
    try:
        with open("openai_key.txt", "r") as f:
            openai_api_key = f.read().strip()
    except FileNotFoundError:
        print("Error: openai_key.txt not found. Please create this file with your OpenAI API key.")
        return
    
    ollama_chat_url = "http://localhost:11434"
    kokoro_audio_url = "http://localhost:8880/v1"
    tester = ConfigurationTester(openai_api_key=openai_api_key, ollama_chat_url=ollama_chat_url, ollama_audio_url=kokoro_audio_url)
    
    # Add all default chat configurations
    chat_configs = tester.create_chat_configurations()
    for config in chat_configs:
        tester.add_chat_configuration(config)
    
    # Add all default audio configurations
    audio_configs = tester.create_audio_configurations()
    for config in audio_configs:
        tester.add_audio_configuration(config)
    
    print(f"Testing {len(chat_configs)} chat configurations and {len(audio_configs)} audio configurations with 3 iterations each...")
    
    # Run chat tests
    print("\n=== Running Chat Tests ===")
    chat_results = await tester.run_all_chat_tests(iterations=3)
    
    # Run audio tests
    print("\n=== Running Audio Tests ===")
    audio_results = await tester.run_all_audio_tests(iterations=3)
    
    # Combine results
    all_results = chat_results + audio_results
    tester.results = all_results
    
    # Print summary
    tester.print_summary()
    
    # Save results
    tester.save_results("full_test_results")
    
    return all_results


def main():
    """Main function with test type selection"""
    print("AI Theater Configuration Tester")
    
    asyncio.run(run_full_test())
    print(f'Tests completed')
        


if __name__ == "__main__":
    main()
