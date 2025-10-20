# AI Talkmaster

AI Talkmaster is a server for creating engaging conversations using large language models. AI Talkmaster was developed for presentation at the [Open Simulator Community Conference 2025](https://conference.opensimulator.org/). AI Talkmaster was designed to be usable from within virtual worlds, first and foremost the [OpenSimulator environment](https://en.wikipedia.org/wiki/OpenSimulator). AI Talkmaster provides several interfaces for creating conversations using open-source or proprietary (OpenAI) large language models. The large language models can be instructed to behave in many different ways, for example they can behave like an oracle, an actor in a theater play or a debate participant. 

Although the powerful large language models of OpenAI can be used in AI Talkmaster it is important to note that their behaviour is not comparable to ChatGPT. ChatGPT and other online assistants have additional add-ons, such as live online search.

AI Talkmaster is open-source, we provide instructions for hosting your own instance.
We are also hosting 2 instances for public use.


# Hosted AI Talkmaster

We host 2 Instances of AI Talkmaster at http://hg.hypergrid.net, one using OpenSource exclusively and another using OpenAI exclusively. We are hosting the 2 instances for public use until 2026, then we might shutdown the OpenAI instance.

They are running on the same domain at different ports:

| Instance | OpenSource | OpenAI |
|----------|------------|--------|
| AI Talkmaster Port | 6000 | 7000 |
| AI Talkmaster URL | http://hg.hypergrid.net:6000 | http://hg.hypergrid.net:7000 |
| Icecast Port | 6010 | 7010 |
| Icecast Stream URL | http://hg.hypergrid.net:6010/stream/{join_key} | http://hg.hypergrid.net:7010/stream/{join_key} |
| [Daily Usage Limit](#daily-usage-limit) | 1.000.000 Tokens per IP | 50.000 Tokens per IP |

The lsl-scripts use the OpenSource instance.

# Information for using AI Talkmaster and LSL-Scripts in-world

How to use the LSL-Scripts in-world:
- select a script and place it on an object that you own
  - modify the ait_endpoint variable if you want (to your own AIT server or a [hosted AI Talkmaster](hosted-ai-talkmaster))
- place the notecards on the object
  - the script will tell you which notecards are required
  - the script will validate the content of the notecards
- click on the object to start using it


There are a three kinds of interactions with the large language models: Generate, Conversation and AI Talkmaster. 
Generate and Conversation are precursors of the multi-character conversations of AI Talkmaster. Generate replies to each message with a single message without keeping a history or extended context. Conversation allows for a back-and-forth with many consecutive messages that share a history/context.
The AI Talkmaster conversations go a step further and allow many participants to be a part of the conversation. Furthermore the AI Talkmaster conversations are converted to a live [audio-stream](#audio-stream).

There are example scripts for generating objects that interact with the AI Talkmaster server to generate text responses in the lsl-scripts directory.
The scripts require a few different notecards to be present as parameterization of the scripts. The scripts validate the parameters on reset.

| Conversation Type | Generate | Conversation | AI Talkmaster |
|----------|------|------------|------|
| Description | Single response (no history) | Conversation with History | Conversation with history, multiple chracters possible, audio stream available |
| Script Name | Generate.lsl | Conversation.lsl | ait_character.lsl |
| Required Notecards | llm-system, llm-parameters | llm-system, llm-parameters | llm-system, llm-parameters, join_key |


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

### join_key

This notecard is only required for the AI Talkmaster conversations (multi-character conversations with history and audio streaming).
The notecard contains one value alone, this is called the join_key and is used as an identifier for the conversation.
It is also used in the URL of the [audio stream](#audio-stream).


# Server Description

The AI Talkmaster server provides three kinds of AI conversations, that can be used from OpenSimulator.
The scripts in lsl-scripts directory are examples of how these scripts can be used.

There are 3 different postMessage endpoints for generating text, these requests start the generation of text using large language models. This generation may take a few minutes, depending on the selected models and requests themselves. These long response times lead to timeouts (30 seconds in OpenSimulator and 60 seconds in [LSL](https://wiki.secondlife.com/wiki/LlHTTPRequest#Caveats)). The getMessageResponse endpoints can be used to get the generated result when the generation reached a timeout.


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
- `POST /ait/resetJoinkey` - Reset AI instance (history)
- `POST /ait/generateAudio` - Generate audio from text


#### Audio Stream
AI Talkmaster conversations can be streamed to Icecast when configured properly, the AI Talkmaster conversations are then available as audio streams at the following URL:
http://{aitalkmasterUrl}:{IcecastPort}/stream/{join_key}


This stream URL can be set as audio source for parcel sound in OpenSimulator regions.


## Server return codes

- 200 All good, response is returned
- 400 Bad Request
- 401 Undefined Endpoint
- 422 Request data could not be processed, e.g. wrongly named parameters in json data
- 425 Too Early, this is returned by getMessageResponse when the response is not yet generated
- 500 internal error, the server owner/programmer has to fix something

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

Set mode=="ollama" in the chat client config.

In the example docker-compose files and config files in aitalkmaster-server/config we assume Ollama is running on the host machine.

By default Ollama is only accessible from the very same host it is running on, see [FAQ](https://docs.ollama.com/faq).
We use the docker-compose-nginx.yml to make the Ollama available on port 11433 from the docker containers using host.docker.internal as address.

Ollama provides a lot of [options](https://github.com/ollama/ollama/blob/main/docs/modelfile.md) for generating text responses, they can be sent to AI Talkmaster using the "options" parameter. This provides AI Talkmaster users more control over the behaviour.


### Audio Client Kokoro

Kokoro is a light-weight opensource model for generating audio. You can host your own Kokoro server using the docker-compose-kokoro.yml file.

## Closed Source hosting

Closed source hosting is easier since it does not require you to be hosting your own services. However closed source hosting using OpenAI requires a PAID API key. The keyfile contains the API key and is specified in the configs.

## Model Control

The administrator of an AI Talkmaster server can specify in the configs which models are available. This can be used to restrict the access to [cheaper models](https://platform.openai.com/docs/pricing#text-tokens).


## Daily Usage Limit

AI Talkmaster provides configurations for IP-based rate limiting. It is important to check the usage section of the configuration to prevent to high API costs with paid hosting (OpenAI).  IP-based rate limiting can be abused by malicious actors, it is recommended to use API keys with a limited budget.

The rate limiting throttles requests for IPs based on the amount of tokens (text-generation) and audio duration in a 24h long timeframe. Each text token (input and output) contributes to the limit, as well as the duration of generated audio in seconds multiplied by a configurable factor. 

What IP do LSL-Scripts use? 
Since the scripts are executed by the simulator, the IP is the one of the region/parcel host server.
