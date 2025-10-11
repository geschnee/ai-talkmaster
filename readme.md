# Hosted AI Talkmaster

We host 2 Instances of AI Talkmaster, one using OpenSource exclusively and another using OpenAi Exclusively.

They are running on the same domain at different ports:

| Instance | OpenSource | OpenAI |
|----------|------|------------|
| AI Talkmaster Port | 6000 | 7000 |
| Icecast Port | 6010 | 7010 |


# Hosting AI Talkmaster

You can host your own AI Talkmaster instance. It is recommended to use docker and requires some knowledge about networking and IT in general.

As a server hoster you can decide to use opensource large language models (e.g. Ollama) or closed source providers (e.g. OpenAI).
Similary the server hoster can decide to include or ommit the audio streaming features and can decide to use opensource (e.g. Kokoro) or closed source (e.g. OpenAI). 
There are configuration examples included in this repository at docker/hosting and aitalkmaster-server/config for the four scenarios:
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


# Server Description

The AI Talkmaster server provides three kinds of AI conversations, that can be used from OpenSimulator.
The scripts in lsl-scripts directory are examples of how these scripts can be used.

There are 3 different postMessage endpoints for generating text, these requests start the generation of text using large language models. This generation may take a few minutes, depending on the selected models and requests themselves (longer requests/responses take longer). These long response times lead to timeouts (60 seconds in [LSL](https://wiki.secondlife.com/wiki/LlHTTPRequest)). The getMessageResponse endpoints can be used to get the generated result.


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
Chat with (multiple) AI characters. AI Talkmaster conversations can be streamed to Icecast when configured properly, see config section.

- `POST /ait/postMessage` - Send message to AI instance
- `GET /ait/getMessageResponse` - Get AI response
- `POST /ait/resetJoinkey` - Reset AI instance
- `POST /ait/generateAudio` - Generate audio from text


## Return codes of the server

200 All good, response is returned
400 Bad Request
401 Undefined Endpoint
422 Request data could not be processed, e.g. wrongly named parameters in json data
425 Too Early, this can be discarded by the LSL script
500 internal error, the server owner/programmer has to fix something