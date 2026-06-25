"""edd-harness: a generic, domain-agnostic Evaluation-Driven Development harness.

The engine knows nothing about any consumer domain — all domain knowledge lives in
consumer-supplied scenarios and adapters. Public API:

    from edd_harness import Scenario, Suite, check, JudgeScorer, run

and persistence/comparison helpers (``write_run``, ``bless``, ``compare_run``, ``rescore``).
"""

from .adapter import Adapter, Output
from .compare import Comparison, compare, compare_run
from .errors import EddContractError, EddJudgeUnavailable
from .runner import CheckResult, RunResult, ScenarioResult, run
from .scenario import Scenario, Suite, load_suite
from .scorer import JudgeScorer, Scorer, ScoreResult, check
from .store import bless, read_run, rescore, write_run

__version__ = "0.1.0"

__all__ = [
    "Adapter",
    "Output",
    "Scenario",
    "Suite",
    "load_suite",
    "Scorer",
    "ScoreResult",
    "check",
    "JudgeScorer",
    "run",
    "RunResult",
    "ScenarioResult",
    "CheckResult",
    "write_run",
    "read_run",
    "bless",
    "rescore",
    "compare",
    "compare_run",
    "Comparison",
    "EddContractError",
    "EddJudgeUnavailable",
    "__version__",
]
