from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


DEFAULT_DATA = {
    "devices": [],
    "customers": [],
    "rentals": [],
}


class JsonStorage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Dict:
        if not self.path.exists():
            return DEFAULT_DATA.copy()
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
