# Translation Feature Documentation

## Overview

The Translation feature is a comprehensive system that translates text from one language to another using AI models, and then converts the translated text into audio for streaming. It uses OpenAI and open-source models for translation generation and text-to-speech.

## Key Features

- **Text Translation**: Translates text between any two languages using AI chat models
- **Audio Generation**: Converts translated text to speech (MP3 format)


## API Endpoints

### POST `/translation/translate`

Submits a translation request for processing.

**Request Body** (`TranslationRequest`):
```json
{
  "session_key": "string (required, no spaces)",
  "message": "string (required)",
  "source_language": "string (required)",
  "target_language": "string (required)",
  "message_id": "string (required, must be unique within session)",
  "model": "string (optional, defaults to chat client default)",
  "audio_voice": "string (optional)",
  "audio_model": "string (optional)"
}
```

**Note**: `audio_instructions` are automatically generated based on the `target_language` and are not a request parameter.

**Response** (HTTP 425 - Processing):
```json
{
  "message_id": "string",
  "status": "processing",
  "info": "Translation request queued for background processing",
  "stream_url": "string (if Icecast configured)"
}
```

**Error Responses**:
- `400`: Invalid session key (contains spaces) or duplicate message_id within session
- `500`: Internal server error or IP address extraction failure

**Validation**:
- Session key must not contain spaces
- Message ID must be unique within the session (duplicate message_ids return 400 error)
- Audio client must be available
- Chat model must be valid (if specified)
- Rate limiting applied per IP address

### GET `/translation/getTranslation`

Retrieves a completed translation result.

**Query Parameters**:
- `session_key`: string (required, no spaces)
- `message_id`: string (required)

**Response** (HTTP 200 - Success):
```json
{
  "message_id": "string",
  "original_message": "string",
  "translated_text": "string",
  "source_language": "string",
  "target_language": "string"
}
```

**Response** (HTTP 425 - Still Processing):
```json
{
  "message_id": "string",
  "status": "processing",
  "info": "Translation for message_id: {message_id} is not ready yet"
}
```

**Error Responses**:
- `400`: Invalid session key or session not found
- `500`: Internal server error

## Translation Process

### Step-by-Step Flow

1. **Request Submission**:
   - Client sends POST request to `/translation/translate`
   - Request is validated (session key, audio availability)
   - IP address extracted for rate limiting

2. **Background Queuing**:
   - Request is queued for background processing
   - Immediate response (HTTP 425) returned to client
   - Stream URL provided if Icecast is configured

3. **Translation Processing**:
   - Session is retrieved or created
   - Audio stream started if not already running
   - Text is translated using AI chat client:
     - **OpenAI Mode**: Uses `responses.create()` API with `input` and `instructions` parameters
     - **Ollama Mode**: Uses `generate()` API with `prompt` and `system` parameters
   - Translation instructions are built using `build_translation_instructions()` which provides language-specific instructions in the target language (e.g., Spanish instructions for Spanish translations, French instructions for French translations)
   - Fallback instructions: `"You are a professional translator. Translate the user's text accurately and naturally. Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else:"`

4. **Audio Generation**:
   - Session directory created: `./generated-audio/translation/active/{session_key}/`
   - Sequence number generated (001, 002, 003, ...)
   - Filename format: `{sequence}_translation_{source_language}_to_{target_language}_{audio_voice}.mp3`
   - Audio instructions are automatically built using `build_audio_instructions()` based on the target language (provides language-specific pronunciation guidance)
   - Audio generated using:
     - **OpenAI Mode**: OpenAI TTS API
     - **Open Source Mode**: Open source TTS API
   - Audio saved as MP3 (128kbps bitrate)
   - Metadata added (title, artist, album, genre)

5. **Audio Streaming**:
   - Audio file queued for streaming via Liquidsoap
   - Translation result stored in session

6. **Result Retrieval**:
   - Client polls `/translation/getTranslation` with session_key and message_id
   - Returns translation when ready, or "processing" status if not complete

## Session Management

### TranslationSession

Each translation session is identified by a unique `session_key` and maintains:

- **Session Key**: Unique identifier (no spaces allowed)
- **Created At**: Timestamp when session was created
- **Last Listened At**: Timestamp of last activity
- **Audio Sequence Counter**: Increments for each translation to ensure proper file ordering
- **Translations**: List of completed `TranslationResult` objects

### Session Lifecycle

1. **Creation**: Session created on first translation request for a session_key
2. **Audio Stream**: Translation stream started automatically if Liquidsoap client is configured
3. **Translation Storage**: Each completed translation is stored in the session
4. **Retrieval**: Translations can be retrieved by message_id

## Supported Models

### Translation Models

- **OpenAI**: Any OpenAI-compatible chat model
- **Ollama**: Any Ollama-compatible model
- Default model used if not specified in request

### Audio Models

- **OpenAI**: OpenAI TTS models (e.g., tts-1, tts-1-hd)
- **Open Source**: Open source TTS models
- Voice selection via `audio_voice` parameter
- Audio instructions are automatically generated based on the target language to provide proper pronunciation and intonation guidance

## Rate Limiting

The translation feature tracks resource usage for rate limiting:

- **Translation**: Token usage (OpenAI) or eval_count (Ollama)
- **Audio Generation**: Duration in seconds × `audio_cost_per_second` configuration

Resource usage is tracked per IP address and can be used to enforce rate limits.

## File Storage

### Directory Structure

```
./generated-audio/translation/active/{session_key}/
  ├── 001_translation_en_to_es_alloy.mp3
  ├── 002_translation_es_to_en_nova.mp3
  └── ...
```

### File Naming Convention

- Format: `{sequence}_translation_{source_language}_to_{target_language}_{audio_voice}.mp3`
- Sequence: Zero-padded 3-digit number (001, 002, 003, ...)
- Example: `001_translation_English_to_Spanish_alloy.mp3`

### Audio Metadata

Each generated audio file includes ID3 metadata:
- **Title**: Session key
- **Artist**: "Translation"
- **Album**: Session key
- **Genre**: "Speech"

## Audio Streaming

### Stream Configuration

- Translation streams use mount point: `/translation/stream/{session_key}`
- Stream URL format: `{base_url}/translation/stream/{session_key}`
- Audio files are queued sequentially for playback
- Stream starts automatically when first translation is processed

### Integration

- **Liquidsoap**: Manages audio streaming
- **Icecast**: Provides stream endpoint
- Audio files queued via `queue_translation_audio()` function

## Error Handling

### Translation Failures

- If translation fails, original message is returned
- Errors are logged with stack traces
- Client receives error response with details

### Audio Generation Failures

- Errors logged with stack traces
- Processing continues if possible
- Failed requests don't block subsequent translations

### Validation Errors

- Invalid session keys (containing spaces) return 400 error
- Duplicate message_id within the same session returns 400 error
- Missing audio client returns 400 error
- Invalid chat model returns 400 error
- Rate limit violations handled by rate limiter decorator

## Usage Examples

### Basic Translation Request

```python
import requests

response = requests.post(
    "http://localhost:8000/translation/translate",
    json={
        "session_key": "user123",
        "message": "Hello, how are you?",
        "source_language": "English",
        "target_language": "Spanish",
        "message_id": "msg_001",
        "audio_voice": "alloy"
    }
)

# Response: HTTP 425
# {
#   "message_id": "msg_001",
#   "status": "processing",
#   "info": "Translation request queued for background processing",
#   "stream_url": "http://localhost:8000/translation/stream/user123"
# }
```

### Retrieving Translation Result

```python
response = requests.get(
    "http://localhost:8000/translation/getTranslation",
    params={
        "session_key": "user123",
        "message_id": "msg_001"
    }
)

# If ready (HTTP 200):
# {
#   "message_id": "msg_001",
#   "original_message": "Hello, how are you?",
#   "translated_text": "Hola, ¿cómo estás?",
#   "source_language": "English",
#   "target_language": "Spanish"
# }

# If still processing (HTTP 425):
# {
#   "message_id": "msg_001",
#   "status": "processing",
#   "info": "Translation for message_id: msg_001 is not ready yet"
# }
```

## Configuration Requirements

### Required Services

- **Chat Client**: OpenAI or Ollama for text translation
- **Audio Client**: OpenAI or Open Source TTS for audio generation
- **Liquidsoap Client** (optional): For audio streaming
- **Icecast Client** (optional): For stream endpoint

### Configuration Options

- `chat_client.mode`: ChatClientMode.OPENAI or ChatClientMode.OLLAMA
- `chat_client.default_model`: Default translation model
- `audio_client.mode`: AudioClientMode.OPENAI or AudioClientMode.OPENSOURCE
- `icecast_client.translation_stream_endpoint_prefix`: Full URL prefix for translation stream endpoints (e.g., `"http://localhost:7000/translation/stream/"`)
- `server.usage.audio_cost_per_second`: Cost multiplier for audio rate limiting

## Implementation Details

### Key Functions

- `translate_text()`: Performs text translation using AI models
- `save_audio()`: Generates and saves audio file
- `save_metadata()`: Adds ID3 metadata to audio file
- `process_translation()`: Main background processing function
- `get_or_create_translation_session()`: Session management
- `queue_translation_audio()`: Queues audio for streaming

### Decorators

- `@validate_session_key_decorator`: Validates session key format (no spaces)
- `@validate_audio_decorator`: Ensures audio client is available
- `@validate_chat_model_decorator`: Validates chat model (if specified)
- `@rate_limit_decorator`: Applies rate limiting per IP address

## Notes

- Translation requests are processed asynchronously in the background
- Multiple translations can be processed concurrently for different sessions
- Audio files are stored temporarily in the `active` directory
- Session data is stored in memory (not persisted across server restarts)
- The system supports any language pair supported by the underlying AI models

