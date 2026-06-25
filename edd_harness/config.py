"""Configuration resolution from ``[tool.edd]`` in pyproject.toml.

Environment variables (e.g. ``EDD_JUDGE_BACKEND``, read by the judge factory) take precedence
over file config at their point of use.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    judge_backend: str | None = None
    samples: int | None = None


def load_config(root: str | Path = ".") -> Config:
    path = Path(root) / "pyproject.toml"
    if not path.exists():
        return Config()
    data = tomllib.loads(path.read_text())
    edd = data.get("tool", {}).get("edd", {})
    judge = edd.get("judge", {})
    return Config(judge_backend=judge.get("backend"), samples=edd.get("samples"))
