import json
import os


def save_to_file(body: str, file_name: str):
    if os.path.exists(file_name):
        os.remove(file_name)
    with open(file_name, "w") as f:
        json.dump(body, f)


def read_from_file(file_name: str) -> str:
    return open(file_name, "r").read()
