"""Local-only safe document input."""

from pathlib import Path
from typing import Any

import yaml

from .specification import WorldSpec


def load_spec(path: Path) -> WorldSpec:
    data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return WorldSpec.model_validate(data)
