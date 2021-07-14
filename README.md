# canvas-stream

Second iteration of a [canvas-file-downloader][v1].

Uses a SQLite3 database with a simple dataclass-like ORM.

## Installation

```ps1
# Tested on python 3.9
python3.9 -m venv .venv/

# PowerShell
. .\.venv\Scripts\Activate.ps1
# Unix
. ./.venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Make a `config.toml` file on the root directory of this project.

```toml
url = 'canvas.com'
access_token = 'Your-Token'
```

You can get the access token [here][access_tokens].
Then, to run the project run `run.py`:

```ps1
python run.py
```

## Notes

- For some reason,
    ```py
    from __future__ import annotations
    ```
    changes the annotations from `type`s to `str`s.

- To improve this iteration, asynchronous programing should be used.

[access_tokens]: https://cursos.canvas.uc.cl/profile/settings#access_tokens
[v1]: https://github.com/benjavicente/canvas-file-downloader
