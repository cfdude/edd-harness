"""Judge backend protocol, binary Verdict, and a JSON-verdict base with retry semantics."""

from __future__ import annotations

import abc
import json
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..errors import EddJudgeUnavailable

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class Verdict:
    verified: bool
    reason: str = ""


@runtime_checkable
class JudgeBackend(Protocol):
    name: str
    model: str

    def verify(self, rendered: str, criteria: str) -> Verdict: ...


def parse_verdict(text: str) -> Verdict:
    """Parse a strict ``{"verified": bool, "reason": str}`` object from judge output.

    Tolerates surrounding prose by extracting the first JSON object. Raises ``ValueError`` if
    no parseable verdict is present (the caller decides whether to retry).
    """
    candidate = text.strip()
    try:
        data = json.loads(candidate)
    except (TypeError, ValueError):
        match = _JSON_OBJECT.search(candidate)
        if not match:
            raise ValueError(f"no JSON object in judge output: {text!r}") from None
        try:
            data = json.loads(match.group(0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unparseable judge output: {text!r}") from exc
    if not isinstance(data, dict) or "verified" not in data:
        raise ValueError(f"judge output missing 'verified': {text!r}")
    return Verdict(verified=bool(data["verified"]), reason=str(data.get("reason", "")))


class JsonVerdictBackend(abc.ABC):
    """Base for backends that obtain a JSON verdict from a model invocation.

    Subclasses implement ``_invoke`` (raising ``EddJudgeUnavailable`` on outage) and set
    ``name``/``model``. ``verify`` parses the output and retries the invocation ONCE on an
    unparseable result, then raises ``EddJudgeUnavailable`` — it never returns ``verified=False``
    for a parse failure.
    """

    name: str
    model: str

    @abc.abstractmethod
    def _invoke(self, rendered: str, criteria: str) -> str:
        """Return raw model output, or raise ``EddJudgeUnavailable`` on outage."""

    def verify(self, rendered: str, criteria: str) -> Verdict:
        last_raw = ""
        for attempt in (1, 2):
            last_raw = self._invoke(rendered, criteria)  # EddJudgeUnavailable propagates
            try:
                return parse_verdict(last_raw)
            except ValueError:
                if attempt == 2:
                    raise EddJudgeUnavailable(
                        f"unparseable judge output after retry: {last_raw!r}"
                    ) from None
        raise EddJudgeUnavailable("judge produced no verdict")  # pragma: no cover
