"Utilities"

import unicodedata
import re
from pathlib import Path
import requests


def slugify(value: str) -> str:
    "Makes a string a valid file path"
    value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .replace(r"/", "-")
        .replace("\\", "-")
        .replace("*", "")
    )
    return re.sub(r"[-]+", "-", value).strip("_-.")


def download(url: str, path: Path):
    "Downloads a file from a url"
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = requests.get(url, stream=True)
    content_length = stream.headers.get("content-length", None)
    with path.open("wb") as file:
        if not content_length:
            print(f"???% -- {path}")
            file.write(stream.content)
            return

        progress = 0
        total_bytes = int(content_length)
        for data in stream.iter_content(chunk_size=4096):
            file.write(data)
            progress += len(data)
            print(f"{progress / total_bytes:4.0%} -- {path}", end="\r")
        print(end="\n")
