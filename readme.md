

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
