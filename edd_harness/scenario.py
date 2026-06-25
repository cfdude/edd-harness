"""The Scenario contract and discovery.

A ``Scenario`` is the unit of evaluation. The engine treats ``input`` as opaque — it is
handed verbatim to the consumer's adapter and never inspected for domain shape. ``id`` is the
stable join key for baselines (independent of any test-runner node id).
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .adapter import Adapter
    from .scorer import Scorer


@dataclass(frozen=True)
class Scenario:
    id: str
    input: Any
    adapter: Adapter
    scorers: list[Scorer]
    samples: int = 1
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class Suite:
    """An ordered collection of scenarios to run together."""

    def __init__(self, scenarios: Iterable[Scenario]) -> None:
        self.scenarios: list[Scenario] = list(scenarios)

    def filter_tags(self, tags: Iterable[str]) -> Suite:
        """Return a new Suite of scenarios whose tags include every requested tag."""
        wanted = set(tags)
        if not wanted:
            return Suite(self.scenarios)
        return Suite([s for s in self.scenarios if wanted.issubset(set(s.tags))])

    def __iter__(self) -> Iterator[Scenario]:
        return iter(self.scenarios)

    def __len__(self) -> int:
        return len(self.scenarios)


def load_suite(spec: str) -> Suite:
    """Load a Suite from a ``module:attr`` spec (attr defaults to ``SCENARIOS``).

    The attr may be a ``Suite`` or any iterable of ``Scenario``.
    """
    module_path, _, attr = spec.partition(":")
    obj = getattr(importlib.import_module(module_path), attr or "SCENARIOS")
    if isinstance(obj, Suite):
        return obj
    return Suite(obj)
