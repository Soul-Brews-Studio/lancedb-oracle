import json
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/"


def load(name: str) -> list[dict]:
    for p in (Path(__file__).parent / name, Path("../data") / name, Path(name)):
        if p.exists():
            return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    urllib.request.urlretrieve(RAW + name, name)
    return [json.loads(l) for l in Path(name).read_text(encoding="utf-8").splitlines() if l.strip()]
