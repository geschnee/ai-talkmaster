

# Ollama Models

Install new model:

ollama run deepseek-r1

List installed models:

ollama list


# options

right now the options can only be used with the Ollama Client

possible params:
https://github.com/ollama/ollama/blob/main/docs/modelfile.md



# docker rebuild no dependencies


docker compose up --build --no-deps --force-recreate


# Issues

## Audio Delay

There is a delay between the creation of the MP3 Files (+ Liquidsoap file detection) and hearing them in the Icecast stream.
This delay is higher for the OpenSimulator viewers compared to other media players (e.g. VLC).
About 16 seconds delay when hearing the audio via VLC.
About 50 seconds delay when hearing the audio via Firestorm Viewer.

The length of the text / audio does not affect this delay.

### Attempted Solutions

https://icecast.org/docs/icecast-2.3.1/config-file.html

disabling burst-on-connect might reduce the delay!

Result:

testing showed no improvement when setting burst-on-connect to 0 for listening to the stream on Firestorm


# Return codes of the server

200 All good, response is returned
400 Bad Request, the result of this should be shown to the LSL script owner/user
401 Undefined Endpoint
422 Request data could not be processes, e.g. wrongly named parameters in json data
425 Too Early, this can be discarded by the LSL script
500 internal error, the server owner/programmer has to fix something


# Endpoints

## Status & Configuration
- `GET /statusAitalkmaster` - Server status check
- `GET /chatmodels` - Get available chat models
- `GET /audio_models` - Get available audio models/voices

## Generate (no history)

- `POST /generate/postMessage` - Generate response without history
- `GET /generate/getResponse` - Get generated response

## Conversation (with history)

- `POST /conversation/start` - Start new conversation
- `POST /conversation/sendMessage` - Send message to conversation
- `GET /conversation/getMessageResponse` - Get response from conversation

## AI Talkmaster
Chat with (multiple) AI characters. AI Talkmaster conversations can be streamed to Icecast when configured properly, see config section.


- `POST /ait/postMessage` - Send message to AI instance
- `GET /ait/getMessageResponse` - Get AI response
- `POST /ait/resetJoinkey` - Reset AI instance
- `POST /ait/generateAudio` - Generate audio from text
