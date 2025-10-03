#!/usr/bin/env python3
"""
Configuration Testing Script for AI Theater
Tests different configurations and compares performance metrics across:
- Ollama text generation
- OpenAI text generation  
- OpenAI audio generation
- Kokoro audio generation

Metrics tracked:
- API call duration
- Response quality (basic)
- Error rates
"""

import asyncio
import time
import json
import csv
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import traceback

# Import the existing modules
from openai import OpenAI
from ollama import Client
from code.aitalkmaster_utils import TheaterPlay, PostMessageRequest, remove_name


@dataclass
class TestResult:
    """Individual test result"""
    test_id: str
    configuration: Dict[str, Any]
    api_type: str  # 'ollama_text', 'openai_text', 'openai_audio', 'kokoro_audio'
    duration: float
    success: bool
    error_message: Optional[str] = None
    response_length: Optional[int] = None
    timestamp: str = ""


@dataclass
class ConfigurationChatTest:
    """Configuration for chat/text generation tests"""
    name: str
    chat_client_mode: str  # 'openai' or 'ollama'
    chat_model: str
    system_instructions: str
    test_message: str
    username: str
    character_name: str = "TestCharacter"
    play_history: Optional[List[Dict[str, Any]]] = None  # Optional conversation history


@dataclass
class ConfigurationAudioTest:
    """Configuration for audio generation tests"""
    name: str
    audio_client_mode: str  # 'openai' or 'kokoro'
    audio_model: str
    audio_voice: str
    audio_description: str = "Generate natural speech for a virtual theater character"
    test_text: str = "This is a test response for audio generation. It contains enough text to properly test the audio generation capabilities."


class ConfigurationTester:
    """Main testing class for configuration performance comparison"""
    
    def __init__(self, openai_api_key: str, ollama_chat_url: str = "http://localhost:11434", ollama_audio_url: str = "http://localhost:8880/v1"):
        self.results: List[TestResult] = []
        self.chat_configurations: List[ConfigurationChatTest] = []
        self.audio_configurations: List[ConfigurationAudioTest] = []
        self.output_dir = Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Store connection parameters
        self.openai_api_key = openai_api_key
        self.ollama_chat_url = ollama_chat_url
        self.ollama_audio_url = ollama_audio_url
        
        # Create our own clients for testing
        self.openai_chat_client = None
        self.openai_audio_client = None
        self.ollama_chat_client = None
        self.ollama_audio_client = None
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize OpenAI and Ollama clients for testing"""
        try:
            # Initialize OpenAI clients
            self.openai_chat_client = OpenAI(api_key=self.openai_api_key)
            self.openai_audio_client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize Ollama clients
            self.ollama_chat_client = Client(host=self.ollama_chat_url)
            self.ollama_audio_client = OpenAI(base_url=self.ollama_audio_url, api_key="kokoro")
            
        except Exception as e:
            print(f"Warning: Could not initialize all clients: {e}")
    
    def get_response_ollama(self, request: PostMessageRequest, play: TheaterPlay) -> str:
        """Get response from Ollama chat client"""
        if self.ollama_chat_client is None:
            raise RuntimeError("Ollama chat client not initialized")
            
        full_dialog = []
        full_dialog.append({
            "role": "system",
            "content": request.system_instructions  
        })
        for d in play.getDialog():
            full_dialog.append(d)

        response = self.ollama_chat_client.chat(model=request.model, messages=full_dialog)
        response_msg = remove_name(response["message"]["content"], request.charactername)
        return response_msg
    
    def get_response_openai(self, request: PostMessageRequest, play: TheaterPlay) -> str:
        """Get response from OpenAI chat client"""
        if self.openai_chat_client is None:
            raise RuntimeError("OpenAI chat client not initialized")
            
        from pydantic import BaseModel, Field
        
        class ChatResponse(BaseModel):
            text_response: str = Field(description="character response")

        response = self.openai_chat_client.responses.parse(
            model=request.model,
            input=play.getDialog(),
            instructions=request.system_instructions,
            text_format=ChatResponse,
            store=False
        )

        if response.output_parsed is None:
            raise RuntimeError("OpenAI response parsing failed")
            
        return response.output_parsed.text_response
    
    def create_theater_play_with_history(self, join_key: str, play_history: Optional[List[Dict[str, Any]]] = None) -> TheaterPlay:
        """Create a TheaterPlay with optional conversation history"""
        play = TheaterPlay(join_key=join_key)
        
        if play_history:
            for history_item in play_history:
                if history_item.get("role") == "user":
                    play.addUserMessage(
                        message=history_item["content"],
                        name=history_item.get("name", "TestUser"),
                        message_id=history_item.get("message_id", f"hist_{len(play.dialog)}")
                    )
                elif history_item.get("role") == "assistant":
                    play.addResponse(
                        response=history_item["content"],
                        name=history_item.get("name", "TestCharacter"),
                        response_id=history_item.get("response_id", f"hist_resp_{len(play.assistant_responses)}"),
                        filename=history_item.get("filename", "")
                    )
        
        return play
    
    @staticmethod
    def create_simple_play_history(conversation: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Create play history from a simple conversation format.
        
        Args:
            conversation: List of tuples (role, content) where role is "user" or "assistant"
            
        Returns:
            List of history items in the correct format
            
        Example:
            history = ConfigurationTester.create_simple_play_history([
                ("user", "Hello!"),
                ("assistant", "Hi there! How can I help you?"),
                ("user", "Tell me about AI")
            ])
        """
        history = []
        for i, (role, content) in enumerate(conversation):
            if role == "user":
                history.append({
                    "role": "user",
                    "content": content,
                    "name": "TestUser",
                    "message_id": f"simple_{i+1}"
                })
            elif role == "assistant":
                history.append({
                    "role": "assistant",
                    "content": content,
                    "name": "TestCharacter",
                    "response_id": f"simple_resp_{i+1}",
                    "filename": ""
                })
        return history
    
    def add_chat_configuration(self, config: ConfigurationChatTest):
        """Add a chat configuration to test"""
        self.chat_configurations.append(config)
    
    def add_audio_configuration(self, config: ConfigurationAudioTest):
        """Add an audio configuration to test"""
        self.audio_configurations.append(config)
    
    
    def create_chat_configurations(self) -> List[ConfigurationChatTest]:
        """Create chat-only test configurations"""
        # Test messages of different lengths
        short_message = "Hello, how are you?"
        medium_message = "I'm working on a project that involves AI and machine learning. Can you help me understand the basics of neural networks?"
        
        # System instructions variations
        basic_instructions = "You are a helpful AI assistant."
        character_instructions = "You are Vladimir, a man waiting for the ominous Godot. You pass the time waiting by talking to Estragon. Your hope fades slowly as you are uncertain when Godot arrives. The longer you two are waiting the less sure you are Godot arrives.\n\nDo not describe what you are doing, just talk.\nTalk as if you are Vladimir, do not speak the dialogue of other characters.\nRespond in short messages only, about 5 sentences maximum."
        
        # Example play history for testing with conversation context
        example_play_history = [
            {
                "role": "user",
                "content": "Hello Vladimir, do you know what time it is?",
                "name": "Estragon",
                "message_id": "hist_1"
            },
            {
                "role": "assistant", 
                "content": "No Estragon, it's 12 o'clock but I don't knwo what day it is, do you?",
                "name": "Vladimir",
                "response_id": "hist_resp_1",
                "filename": ""
            },
            {
                "role": "user",
                "content": "I think it is Wednesday or even Friday already. It doesn't matter, I only care about meeting Godot tomorrow.",
                "name": "Estragon", 
                "message_id": "hist_2"
            }
        ]
        
        # Chat configuration matrix
        configs = [
            # OpenAI Chat Tests
            ConfigurationChatTest(
                name="OpenAI GPT-4o-mini - Short Message",
                chat_client_mode="openai",
                chat_model="gpt-4o-mini",
                system_instructions=basic_instructions,
                test_message=short_message,
                username="Testuser"
            ),
            ConfigurationChatTest(
                name="OpenAI GPT-4o-mini - Character",
                chat_client_mode="openai",
                chat_model="gpt-4o-mini",
                system_instructions=character_instructions,
                test_message=medium_message,
                username="Testuser"
            ),
            ConfigurationChatTest(
                name="OpenAI GPT-4o-mini - With History",
                chat_client_mode="openai",
                chat_model="gpt-4o-mini",
                system_instructions=character_instructions,
                test_message="I'd love to learn more about philosophy. Can you tell me about existentialism?",
                play_history=example_play_history,
                username="Luzzo"
            ),
            
            # Ollama Chat Tests
            ConfigurationChatTest(
                name="Ollama Llama3.2 - Short Message",
                chat_client_mode="ollama",
                chat_model="llama3.2",
                system_instructions=basic_instructions,
                test_message=short_message,
                username="Testuser"
            ),
            ConfigurationChatTest(
                name="Ollama Llama3.2 - Character",
                chat_client_mode="ollama",
                chat_model="llama3.2",
                system_instructions=character_instructions,
                test_message=medium_message,
                username="Testuser"
            ),
            ConfigurationChatTest(
                name="Ollama LLama3.2 - With History",
                chat_client_mode="ollama",
                chat_model="llama3.2",
                system_instructions=character_instructions,
                test_message="Yes, he will arrive tomorrow",
                username="Luzzo",
                play_history=example_play_history
            )
        ]
        
        return configs
    
    def create_audio_configurations(self) -> List[ConfigurationAudioTest]:
        """Create audio-only test configurations"""
        # Audio descriptions for different scenarios
        basic_audio_description = "Generate natural speech for a helpful assistant."
        sad_audio_description = "You sound defeated and sad"
        happy_audio_description = "Sound happy"
        
        happy_text = "I am glad you finally came. Let's celebrate!"
        sad_text = "What are we but animals in a cage of our own volition. Waiting for Godot to arrive"

        # Audio configuration matrix
        configs = [
            # OpenAI Audio Tests
            ConfigurationAudioTest(
                name="OpenAI TTS-1 - Basic",
                audio_client_mode="openai",
                audio_model="tts-1",
                audio_voice="alloy",
                audio_description=basic_audio_description
            ),
            ConfigurationAudioTest(
                name="OpenAI TTS-1 - Happy",
                audio_client_mode="openai",
                audio_model="tts-1",
                audio_voice="nova",
                audio_description=happy_audio_description,
                test_text=happy_text
            ),
            ConfigurationAudioTest(
                name="OpenAI TTS-1-HD - Sad",
                audio_client_mode="openai",
                audio_model="tts-1",
                audio_voice="echo",
                audio_description=sad_audio_description,
                test_text=sad_text
            ),
            
            # Kokoro Audio Tests
            ConfigurationAudioTest(
                name="Kokoro Audio - Basic",
                audio_client_mode="kokoro",
                audio_model="kokoro",
                audio_voice="af_alloy",
                audio_description=basic_audio_description
            ),
            ConfigurationAudioTest(
                name="Kokoro Audio - Sad",
                audio_client_mode="kokoro",
                audio_model="kokoro",
                audio_voice="af_alloy",
                audio_description=sad_audio_description,
                test_text=sad_text
            ),
            ConfigurationAudioTest(
                name="Kokoro Audio - Happy",
                audio_client_mode="kokoro",
                audio_model="kokoro",
                audio_voice="af_alloy",
                audio_description=happy_audio_description,
                test_text=happy_text
            ),
        ]
        
        return configs
    
    async def test_text_generation(self, config: ConfigurationChatTest, test_id: str) -> TestResult:
        """Test text generation API using the same structure as postaiTMessage"""
        start_time = time.time()
        
        try:
            # Create a test theater play with proper join_key and optional history
            join_key = f"test_{test_id}"
            play = self.create_theater_play_with_history(join_key, config.play_history)
            
            # Create request object with all required fields like postaiTMessage
            request = PostMessageRequest(
                join_key=join_key,
                username=config.username,
                message=config.test_message,
                model=config.chat_model,
                system_instructions=config.system_instructions,
                charactername=config.character_name,
                message_id="msg_1",
                options={},  # Default options
                audio_description="",  # Not needed for chat tests
                audio_voice="",  # Not needed for chat tests
                audio_model=""  # Not needed for chat tests
            )
            
            # Add user message to the play (like in postaiTMessage)
            play.addUserMessage(request.message, name=request.username, message_id=request.message_id)
            
            # Call appropriate text generation function
            if config.chat_client_mode == "openai":
                response_text = self.get_response_openai(request, play)
                api_type = "openai_text"
            elif config.chat_client_mode == "ollama":
                response_text = self.get_response_ollama(request, play)
                api_type = "ollama_text"
            else:
                raise ValueError(f"Unknown chat client mode: {config.chat_client_mode}")
            
            duration = time.time() - start_time
            
            return TestResult(
                test_id=test_id,
                configuration=asdict(config),
                api_type=api_type,
                duration=duration,
                success=True,
                response_length=len(response_text),
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            duration = time.time() - start_time
            # Determine api_type based on config if not already set
            if config.chat_client_mode == "openai":
                api_type = "openai_text"
            elif config.chat_client_mode == "ollama":
                api_type = "ollama_text"
            else:
                api_type = "unknown_text"
                
            return TestResult(
                test_id=test_id,
                configuration=asdict(config),
                api_type=api_type,
                duration=duration,
                success=False,
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    async def test_audio_generation(self, config: ConfigurationAudioTest, test_id: str, response_text: Optional[str] = None) -> TestResult:
        """Test audio generation API using the same structure as postaiTMessage"""
        start_time = time.time()
        
        try:
    
            # Create meaningful filename based on configuration
            safe_config_name = config.name.replace(' ', '_').replace('-', '_').replace(':', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'./generated-audio/{safe_config_name}_{timestamp}.mp3'
            Path("./generated-audio").mkdir(exist_ok=True)
            
            
            # Determine API type based on audio client mode
            if config.audio_client_mode == "openai":
                api_type = "openai_audio"
                if self.openai_audio_client is None:
                    raise RuntimeError("Openai audio client not initialized")
                response = self.openai_audio_client.audio.speech.create(
                    model=config.audio_model,
                    voice=config.audio_voice,
                    input=config.test_text,
                    instructions=config.audio_description
                )
            elif config.audio_client_mode == "kokoro":
                api_type = "kokoro_audio"
                if self.ollama_audio_client is None:
                    raise RuntimeError("Ollama audio client not initialized")
                response = self.ollama_audio_client.audio.speech.create(
                    model=config.audio_model,
                    voice=config.audio_voice,
                    input=config.test_text,
                    instructions=config.audio_description
                )
            else:
                raise ValueError(f"Unknown audio client mode: {config.audio_client_mode}")
            
            # Save audio file like in postaiTMessage
            with open(filename, "wb") as f:
                f.write(response.content)
            
            duration = time.time() - start_time
            
            # Get audio file size
            audio_size = Path(filename).stat().st_size if Path(filename).exists() else 0
            
            return TestResult(
                test_id=test_id,
                configuration=asdict(config),
                api_type=api_type,
                duration=duration,
                success=True,
                response_length=len(config.test_text),
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            duration = time.time() - start_time
            # Determine api_type based on config if not already set
            if config.audio_client_mode == "openai":
                api_type = "openai_audio"
            elif config.audio_client_mode == "kokoro":
                api_type = "kokoro_audio"
            else:
                api_type = "unknown_audio"
                
            return TestResult(
                test_id=test_id,
                configuration=asdict(config),
                api_type=api_type,
                duration=duration,
                success=False,
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    async def run_chat_tests(self, config: ConfigurationChatTest, iterations: int = 3) -> List[TestResult]:
        """Run chat-only tests for a configuration"""
        print(f"Testing chat configuration: {config.name}")
        all_results = []
        
        for i in range(iterations):
            safe_config_name = config.name.replace(' ', '_').replace('-', '_').replace(':', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_id = f"{safe_config_name}_chat_{i+1}_{timestamp}"
            print(f"  Chat iteration {i+1}/{iterations}")
            
            try:
                # Test text generation only
                print(f"    Testing text generation...")
                text_result = await self.test_text_generation(config, test_id)
                all_results.append(text_result)
                
                # Small delay between iterations
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"    Error in chat iteration {i+1}: {e}")
                # Create error result
                error_result = TestResult(
                    test_id=test_id,
                    configuration=asdict(config),
                    api_type="chat_error",
                    duration=0.0,
                    success=False,
                    error_message=str(e),
                    timestamp=datetime.now().isoformat()
                )
                all_results.append(error_result)
        
        return all_results
    
    async def run_audio_tests(self, config: ConfigurationAudioTest, iterations: int = 3) -> List[TestResult]:
        """Run audio-only tests for a configuration"""
        print(f"Testing audio configuration: {config.name} {config.audio_voice}")
        all_results = []
        
        for i in range(iterations):
            safe_config_name = config.name.replace(' ', '_').replace('-', '_').replace(':', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_id = f"{safe_config_name}_audio_{i+1}_{timestamp}"
            print(f"  Audio iteration {i+1}/{iterations}")
            
            try:
                # Test audio generation only (uses config.test_text)
                print(f"    Testing audio generation...")
                audio_result = await self.test_audio_generation(config, test_id)
                all_results.append(audio_result)
                
                # Small delay between iterations
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"    Error in audio iteration {i+1}: {e}")
                # Create error result
                error_result = TestResult(
                    test_id=test_id,
                    configuration=asdict(config),
                    api_type="audio_error",
                    duration=0.0,
                    success=False,
                    error_message=str(e),
                    timestamp=datetime.now().isoformat()
                )
                all_results.append(error_result)
        
        return all_results
    
    
    
    
    async def run_all_chat_tests(self, iterations: int = 3) -> List[TestResult]:
        """Run chat-only tests for all configurations"""
        print(f"Starting chat-only tests with {iterations} iterations each...")
        print(f"Total chat configurations to test: {len(self.chat_configurations)}")
        
        all_results = []
        
        for i, config in enumerate(self.chat_configurations):
            print(f"\n[{i+1}/{len(self.chat_configurations)}] Testing chat: {config.name}")
            try:
                results = await self.run_chat_tests(config, iterations)
                all_results.extend(results)
                print(f"  Completed: {len(results)} chat results")
            except Exception as e:
                print(f"  Failed: {e}")
                traceback.print_exc()
        
        self.results = all_results
        return all_results
    
    async def run_all_audio_tests(self, iterations: int = 3) -> List[TestResult]:
        """Run audio-only tests for all configurations"""
        print(f"Starting audio-only tests with {iterations} iterations each...")
        print(f"Total audio configurations to test: {len(self.audio_configurations)}")
        
        all_results = []
        
        for i, config in enumerate(self.audio_configurations):
            print(f"\n[{i+1}/{len(self.audio_configurations)}] Testing audio: {config.name}")
            try:
                results = await self.run_audio_tests(config, iterations)
                all_results.extend(results)
                print(f"  Completed: {len(results)} audio results")
            except Exception as e:
                print(f"  Failed: {e}")
                traceback.print_exc()
        
        self.results = all_results
        return all_results
    
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results and generate statistics"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Group results by configuration name
        by_config_name = {}
        for result in self.results:
            config_name = result.configuration.get("name", "Unknown")
            if config_name not in by_config_name:
                by_config_name[config_name] = []
            by_config_name[config_name].append(result)
        
        # Calculate statistics for each configuration
        analysis = {
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len([r for r in self.results if r.success]),
                "failed_tests": len([r for r in self.results if not r.success]),
                "success_rate": len([r for r in self.results if r.success]) / len(self.results) * 100
            },
            "by_configuration": {}
        }
        
        for config_name, results in by_config_name.items():
            successful_results = [r for r in results if r.success]
            
            if successful_results:
                durations = [r.duration for r in successful_results]
                analysis["by_configuration"][config_name] = {
                    "total_tests": len(results),
                    "successful_tests": len(successful_results),
                    "failed_tests": len(results) - len(successful_results),
                    "success_rate": len(successful_results) / len(results) * 100,
                    "duration_stats": {
                        "mean": statistics.mean(durations),
                        "median": statistics.median(durations),
                        "min": min(durations),
                        "max": max(durations),
                        "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0
                    },
                    "api_types": list(set([r.api_type for r in results])),
                    "config_details": results[0].configuration if results else {}
                }
            else:
                analysis["by_configuration"][config_name] = {
                    "total_tests": len(results),
                    "successful_tests": 0,
                    "failed_tests": len(results),
                    "success_rate": 0,
                    "duration_stats": None,
                    "api_types": list(set([r.api_type for r in results])),
                    "config_details": results[0].configuration if results else {}
                }
        
        return analysis
    
    def save_results(self, filename: Optional[str] = None):
        """Save results to JSON and CSV files"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"config_test_results_{timestamp}"
        
        # Save as JSON
        json_file = self.output_dir / f"{filename}.json"
        with open(json_file, 'w') as f:
            json.dump([asdict(result) for result in self.results], f, indent=2)
        
        # Save as CSV
        csv_file = self.output_dir / f"{filename}.csv"
        if self.results:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=asdict(self.results[0]).keys())
                writer.writeheader()
                for result in self.results:
                    writer.writerow(asdict(result))
        
        print(f"Results saved to:")
        print(f"  JSON: {json_file}")
        print(f"  CSV: {csv_file}")
        
        return json_file, csv_file
    
    def print_summary(self):
        """Print a summary of test results"""
        analysis = self.analyze_results()
        
        print("\n" + "="*80)
        print("CONFIGURATION TEST SUMMARY")
        print("="*80)
        
        summary = analysis["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        print("\nBY CONFIGURATION:")
        print("-" * 80)
        
        # Sort configurations: chat tests first, then audio tests, then by name
        def get_config_sort_key(item):
            config_name, stats = item
            api_types = stats.get("api_types", [])
            
            # Determine if this is primarily a chat or audio configuration
            if any("text" in api_type for api_type in api_types):
                return (0, config_name)  # Chat tests first
            elif any("audio" in api_type for api_type in api_types):
                return (1, config_name)  # Audio tests second
            else:
                return (2, config_name)  # Other tests last
        
        sorted_configs = sorted(
            analysis["by_configuration"].items(),
            key=get_config_sort_key
        )
        
        current_section = None
        for config_name, stats in sorted_configs:
            api_types = stats.get("api_types", [])
            
            # Determine section and print header if changed
            if any("text" in api_type for api_type in api_types):
                section = "CHAT TESTS"
            elif any("audio" in api_type for api_type in api_types):
                section = "AUDIO TESTS"
            else:
                section = "OTHER TESTS"
            
            if current_section != section:
                if current_section is not None:
                    print()  # Add spacing between sections
                print(f"\n{section}:")
                print("-" * 40)
                current_section = section
            
            print(f"\n{config_name}:")
            print(f"  Tests: {stats['successful_tests']}/{stats['total_tests']} ({stats['success_rate']:.1f}% success)")
            print(f"  API Types: {', '.join(stats['api_types'])}")
            
            if stats["duration_stats"]:
                dur = stats["duration_stats"]
                print(f"  Duration: {dur['mean']:.2f}s avg ({dur['min']:.2f}s - {dur['max']:.2f}s)")
                print(f"  Std Dev: {dur['std_dev']:.2f}s")
            else:
                print("  Duration: No successful tests")
            
            # Show configuration details for context
            config_details = stats.get("config_details", {})
            if config_details:
                if "chat_client_mode" in config_details:
                    print(f"  Chat: {config_details.get('chat_client_mode', 'N/A')} - {config_details.get('chat_model', 'N/A')}")
                if "audio_client_mode" in config_details:
                    print(f"  Audio: {config_details.get('audio_client_mode', 'N/A')} - {config_details.get('audio_model', 'N/A')} ({config_details.get('audio_voice', 'N/A')})")
        
        print("\n" + "="*80)


