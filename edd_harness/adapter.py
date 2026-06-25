"""The Adapter seam — the only domain-shaped boundary.

The consumer supplies an ``Adapter``: a callable that runs their real target in their own
process with their own credentials and returns a JSON-serializable mapping. The engine never
imports a domain type; it only ever sees nested dicts/lists/scalars.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .errors import EddContractError

Output = Mapping[str, Any]


@runtime_checkable
class Adapter(Protocol):
    def __call__(self, scenario_input: Any) -> Output: ...


@dataclass(frozen=True)
class Capture:
    """One adapter invocation's normalized, JSON-round-tripped output plus timing."""

    output: dict[str, Any]
    duration_s: float


def invoke_adapter(adapter: Adapter, scenario_input: Any) -> Capture:
    """Invoke the adapter, enforce the JSON-serialization guarantee, and time it.

    - An exception raised *by the adapter* propagates (the runner maps it to INDETERMINATE).
    - A non-JSON-serializable output raises ``EddContractError`` loudly (never silent
      corruption); the runner maps that to INDETERMINATE too.
    - The output is round-tripped through ``json.dumps``/``json.loads`` so the engine and the
      persisted record only ever hold plain JSON types.
    """
    start = time.perf_counter()
    raw = adapter(scenario_input)
    duration = time.perf_counter() - start

    try:
        normalized = json.loads(json.dumps(raw))
    except (TypeError, ValueError) as exc:
        raise EddContractError(f"adapter output is not JSON-serializable: {exc}") from exc

    if not isinstance(normalized, dict):
        raise EddContractError(
            f"adapter output must be a JSON object (mapping), got {type(raw).__name__}"
        )
    return Capture(output=normalized, duration_s=duration)
