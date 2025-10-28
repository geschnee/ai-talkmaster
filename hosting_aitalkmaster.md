# Hosting AI Talkmaster

You can host your own AI Talkmaster instance. It is recommended to use Docker and requires some knowledge about networking, Docker and IT in general.

As a server hoster you can decide to use open-source large language text models (e.g. Ollama) or closed source providers (e.g. OpenAI).
Similarly the server hoster can decide to include or ommit the audio streaming features and can decide to use open-source (e.g. Kokoro TTS) or closed source (e.g. OpenAI) to generate the audio.

Configuration and hosting examples are included at [docker-hosting](./docker-hosting/) and [aitalkmaster-server/configs](./aitalkmaster-server/configs/) for these four scenarios:
- Ollama Text with Kokoro Audio
- Ollama Text without Audio
- OpenAI Text with OpenAI Audio
- OpenAI Text without Audio


## Open-source hosting

### Chat Client Ollama

Ollama is a program for hosting open-source large language models.
The Ollama python library is used here to send requests to Ollama.

Set mode=="ollama" in the chat client config.

In the example docker-compose files and config files in aitalkmaster-server/config we assume Ollama is running on the host machine.

By default Ollama is only accessible from the very same host it is running on, see [FAQ](https://docs.ollama.com/faq).
We use the docker-compose-nginx.yml to make the Ollama available on port 11433 from the docker containers using host.docker.internal as address.

Ollama provides a lot of [options](https://github.com/ollama/ollama/blob/main/docs/modelfile.md) for generating text responses, they can be sent to AI Talkmaster using the "options" parameter. This provides AI Talkmaster users more control over the behaviour.


### Audio Client Kokoro TTS

Kokoro TTS is a light-weight open-source model for generating audio. You can host your own Kokoro server using the docker-compose-kokoro.yml file.

## Closed Source hosting

Closed source hosting is easier since it does not require you to be hosting your own services. However closed source hosting using OpenAI requires a PAID API key. The keyfile contains the API key and is specified in the configs.


The most powerful model for audio creation by OpenAI is gpt-4o-mini-tts, it can be [prompted to change aspects of speech](https://platform.openai.com/docs/guides/text-to-speech#text-to-speech-models) using the audio_instructions parameter.


## Model Control

The administrator of an AI Talkmaster server can specify in the configs which models are available. This can be used to restrict the access to [cheaper models](https://platform.openai.com/docs/pricing#text-tokens).


## Daily Usage Limit

AI Talkmaster provides configurations for IP-based rate limiting. It is important to check the usage section of the configuration to prevent to high API costs with paid hosting (OpenAI).  IP-based rate limiting can be abused by malicious actors, it is recommended to use API keys with a limited budget.

The rate limiting throttles requests for IPs based on the amount of tokens (text-generation) and audio duration in a 24h long timeframe. Each text token (input and output) contributes to the limit, as well as the duration of generated audio in seconds multiplied by a configurable factor. 

What IP do LSL-Scripts use? 
Since the scripts are executed by the simulator, the IP is the one of the region/parcel host server.
