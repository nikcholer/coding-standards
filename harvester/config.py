import os
from dataclasses import dataclass
from pathlib import Path


REPO = "rust-lang/rust"
DATE_FROM = "2014-06-01"
DATE_TO = "2014-08-31"
DATA_DIR = Path("data/raw")
PROGRESS_FILE = DATA_DIR / ".progress"


@dataclass
class Config:
    github_token: str
    repo: str = REPO
    date_from: str = DATE_FROM
    date_to: str = DATE_TO
    data_dir: Path = DATA_DIR
    progress_file: Path = PROGRESS_FILE


def load_config() -> Config:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "GITHUB_TOKEN environment variable is not set. "
            "Copy .env.example to .env and set your token, then: export GITHUB_TOKEN=..."
        )
    return Config(github_token=token)
