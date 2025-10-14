# Hosted AI Talkmaster

We host 2 Instances of AI Talkmaster at http://hg.hypergrid.net, one using OpenSource exclusively and another using OpenAI exclusively.

They are running on the same domain at different ports:

| Instance | OpenSource | OpenAI |
|----------|------|------------|
| AI Talkmaster Port | 6000 | 7000 |
| AI Talkmaster URL | http://hg.hypergrid.net:6000 | http://hg.hypergrid.net:7000 |
| Icecast Port | 6010 | 7010 |
| Icecast Stream URL | http://hg.hypergrid.net:6010/stream/{join_key} | http://hg.hypergrid.net:7010/stream/{join_key} |

The lsl-scripts use the OpenSource instance.

# Information for using AI Talkmaster and LSL-Scripts in-world

There are a three kinds of conversations: Generate, Conversation and AI Talkmaster
They are example scripts for generating objects that interact with the AI Talkmaster server to generate text responses in the lsl-scripts directory.
The scripts require a few different notecards to be present as parameterization of the scripts. The scripts validate the parameters on reset using the /chat_models endpoint.

| Conversation Type | Generate | Conversation | AI Talkmaster |
|----------|------|------------|
| Description | Single response (no history) | Conversation with History | Conversation with history, multiple chracters possible, audio stream available |
| Script Name | Generate.lsl | Conversation.lsl | ait_character |
| Required Notecards | <ul><li>llm-system</li><li>llm-parameters</li></ul> | <ul><li>llm-system</li><li>llm-parameters</li></ul> | <ul><li>llm-system</li><li>llm-parameters</li><li>join_key</li></ul> |



## Notecard details

### llm-system

This notecard contains the system-instruction for the large language models. This is natural language text that describes how the large language model should reply. For example the llmsystem notecard could contain the following:

```
You are the famous Oracle of Delphi from ancient Greece. Reply as if you are talking to a traveller from a far away land.
```

### llm-parameters

This notecard contains all other parameters for the agent and parameterization of the large language model requests (when using [Ollama](https://github.com/ollama/ollama/blob/main/docs/modelfile.md#parameter)).

An [example notecard](lsl-scripts/llm-parameters.notecard) is located in the lsl-scripts directory. 

The following parameters are only used/required with the AI Talkmaster endpoints when generating an audio stream:
* audio_model
* audio_instructions
* audio_voice

## join_key

This notecard is only required for the AI Talkmaster conversations (multi-character conversations with history and audio streaming).
The notecard contains one value alone, this is called the join_key and is used as an identifier for the conversation.
It is also used in the URL of the [audio stream](#stream-mount).


# Server Description

The AI Talkmaster server provides three kinds of AI conversations, that can be used from OpenSimulator.
The scripts in lsl-scripts directory are examples of how these scripts can be used.

There are 3 different postMessage endpoints for generating text, these requests start the generation of text using large language models. This generation may take a few minutes, depending on the selected models and requests themselves. These long response times lead to timeouts (60 seconds in [LSL](https://wiki.secondlife.com/wiki/LlHTTPRequest)). The getMessageResponse endpoints can be used to get the generated result when the generation reached a timeout.


## Server Endpoints

### Status & Configuration
- `GET /statusAitalkmaster` - Server status check
- `GET /chatmodels` - Get available chat models
- `GET /audio_models` - Get available audio models/voices

### Generate (no history)

- `POST /generate/postMessage` - Generate response without history
- `GET /generate/getMessageResponse` - Get generated response

### Conversation (with history)

- `POST /conversation/start` - Start new conversation
- `POST /conversation/postMessage` - Send message to conversation
- `GET /conversation/getMessageResponse` - Get response from conversation

### AI Talkmaster
Chat with (multiple) AI characters.

- `POST /ait/postMessage` - Send message to AI instance
- `GET /ait/getMessageResponse` - Get AI response
- `POST /ait/resetJoinkey` - Reset AI instance
- `POST /ait/generateAudio` - Generate audio from text


<a name="stream-mount"></a>
AI Talkmaster conversations can be streamed to Icecast when configured properly, the AI Talkmaster conversations are then available as audio streams at the following URL:
http://{aitalkmasterUrl}:{IcecastPort}/stream/{join_key}

For example the stream for Godot is available at:
http://hg.hypergrid.net:7010/stream/Godot


## Return codes of the server

200 All good, response is returned
400 Bad Request
401 Undefined Endpoint
422 Request data could not be processed, e.g. wrongly named parameters in json data
425 Too Early, this is returned by getMessageResponse when the response is not yet generated
500 internal error, the server owner/programmer has to fix something

# Hosting AI Talkmaster

You can host your own AI Talkmaster instance. It is recommended to use docker and requires some knowledge about networking, docker and IT in general.

As a server hoster you can decide to use opensource large language models (e.g. Ollama) or closed source providers (e.g. OpenAI).
Similarly the server hoster can decide to include or ommit the audio streaming features and can decide to use opensource (e.g. Kokoro) or closed source (e.g. OpenAI) to generate the audio. 
There are configuration examples included in this repository at docker/hosting and aitalkmaster-server/config for these four scenarios:
- Ollama Text with Kokoro Audio
- Ollama Text without Audio
- OpenAI Text with OpenAI Audio
- OpenAI Text without Audio


## Opensource hosting

### Chat Client Ollama

Ollama is a program for hosting opensource large language models.
The Ollama python library is used here to send requests to Ollama.

You can use mode=="ollama" in the chat client config.

By default Ollama is only accessible from the very same host it is running on, see [FAQ](https://docs.ollama.com/faq).
In the example docker-compose files and config files in aitalkmaster-server/config we assume Ollama is running on the host machine.

We use the docker-compose-nginx.yml to make the Ollama available on port 11433 from the docker containers using host.docker.internal as adress.

Ollama provides a lot of [options](https://github.com/ollama/ollama/blob/main/docs/modelfile.md) for generating text responses, they can be sent to AI Talkmaster.


### Audio Client Kokoro

Kokoro is a light-weight opensource model for generating audio. You can host your own Kokoro server using the docker-compose-kokoro.yml file.

## Closed Source hosting

Closed source hosting is easier since it does not require you to be hosting your own services. However closed source hosting using OpenAI requires a PAID API key. Furthermore AI Talkmaster does not provide any user monitoring, this can lead to high API costs. The keyfile contains the API key and is specified in the configs.


