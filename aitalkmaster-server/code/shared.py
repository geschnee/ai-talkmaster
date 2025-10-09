from fastapi import FastAPI

from code.config import get_config

config = get_config()

def log(message):
    with open(config.server.log_file, "a") as file:
        file.write(message + "\n")
    print(message)

app = FastAPI()