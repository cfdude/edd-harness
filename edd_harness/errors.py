"""Engine error types.

These are the only exceptions the engine raises by name. Both map to a runner-level
INDETERMINATE outcome for the affected scenario/check (never a silent pass or a false fail).
"""

from __future__ import annotations


class EddContractError(Exception):
    """A consumer-supplied component violated the engine contract.

    Raised, for example, when an adapter returns a non-JSON-serializable ``Output``.
    """


class EddJudgeUnavailable(Exception):
    """A judge backend could not produce a usable verdict.

    Raised on backend outage, or when output is unparseable after the allowed retry.
    Never represents a ``verified=False`` verdict — only the absence of a usable one.
    """
