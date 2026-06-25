"""A deterministic in-memory judge backend for engine tests and consumer scenario tests."""

from __future__ import annotations

from ..errors import EddJudgeUnavailable
from .base import Verdict


class FakeJudge:
    """No-network judge double. Configure a fixed verdict, or simulate an outage."""

    def __init__(
        self,
        verified: bool = True,
        reason: str = "",
        *,
        unavailable: bool = False,
        model: str = "fake-judge-1",
        name: str = "fake",
    ) -> None:
        self._verified = verified
        self._reason = reason
        self._unavailable = unavailable
        self.model = model
        self.name = name
        self.calls: list[tuple[str, str]] = []

    def verify(self, rendered: str, criteria: str) -> Verdict:
        if self._unavailable:
            raise EddJudgeUnavailable("fake judge unavailable")
        self.calls.append((rendered, criteria))
        return Verdict(verified=self._verified, reason=self._reason)
