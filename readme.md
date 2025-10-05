# Ollama



## RAM Memory check

hypergrid@Ubuntu-2404-noble-amd64-base:~$ free -m
               total        used        free      shared  buff/cache   available
Mem:           64079        3565       51698          65        9597       60514
Swap:          32734           0       32734


total is in MB --> 64 GB RAM



## Check Response

POST requests:

curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'

curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Why is the sky blue?",
  "stream": false
}'

## Check curently loaded models

GET request:

http://localhost:11434/api/ps


# Linux install

curl -fsSL https://ollama.com/install.sh | sh


--> installs to /usr/local/bin/ollama


# Access restriction using fastAPI python
Install:
```
pip install fastapi uvicorn httpx
```

Run webserver:
```
uvicorn OllamaProxy:app --host 0.0.0.0 --port 7999
```

Restrict Ollama Ports using Hetzner:
11434


Calling it using curls with the secret token:

```
curl -H "Authorization: Bearer supersecret123" \
     -H "Content-Type: application/json" \
     -d '{"model": "llama3", "prompt": "hello!"}' \
     http://localhost:8000/api/generate
```

## OllamaProxy.py Description

The script forwards /api/generate requests to Ollama directly and returns the results. The script thus provides access to Ollama (it is only directly availible on the Hetzner host)

The lsl llHTTPRequest method reaches a timeout quite quickly, thus the Ollama might not respond quick enough. The script also saves the Ollama results in a "cache" for the LSL scripts. 

The responses from Ollama can be recieved using /api/getResponse from the cache. 
This caching method requires the parameters "username", "model" and "prompt", both for /api/generate and /apt/getResponse endpoints.



## Copy file to Hetzner

scp OllamaProxy.py hypergrid@138.201.134.14:/opt/OllamaProxy/OllamaProxy.py

scp ./* hypergrid@138.201.134.14:/opt/OllamaProxy/.

ssh hypergrid@138.201.134.14

# Ollama Models

Install new model:

ollama run deepseek-r1

List installed models:

ollama list



# TODOs

Oracle parameter notecard

possible params:
https://github.com/ollama/ollama/blob/main/docs/modelfile.md

temperature default is 0.8

ja, siehe modelfile_oracle.txt



current error in OllamaProxy
obtained json: {'error': 'option "stop" must be of type array'}


## Frage?

wandelt Ollama die Modelfile parameter noch weiter um, bevor diese an die Models weitergegeben werden?


Meine Vermutung:

Ollama ist ein Server für Modelle im GGUF Dateityp:
https://huggingface.co/docs/transformers/gguf

Dort sind diese Parameter verwendet.
https://github.com/ollama/ollama/blob/bd68d3ae50c67ba46ee94a584fa6d0386e4b8522/api/types.go#L279



## usage tracking





# Split Text

OpenSim/SecondLife can only output 1024 Chars at a time to the console.

The splitText was developed with ClaudeAI.

- Request 1: 
llSay has a limit for 1024 character strings, write me a script, that takes a long text string and splits it appropriately (newlines or so)
- Request 2:
lsl scripting language


The resulting script had break instructions which do not exist in LSL, the script was manually modified to work without the breaks.

# Debugging


Exceptions angucken

screen -r OllamaProxy


# starten

uvicorn OllamaProxy:app --host 0.0.0.0 --port 7999

# Audio Stream

http://138.201.134.14:7999/aiT/stream-audio/Godot

http://hg.hypergrid.net:7999/aiT/stream-audio/Godot

# start kokoro

docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest


# TODO 

actor should stop polling after XXX seconds




# docker rebuild no dependencies


docker compose up --build --no-deps --force-recreate