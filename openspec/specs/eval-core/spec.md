# eval-core Specification

## Purpose
TBD - created by archiving change edd-harness-v1. Update Purpose after archive.
## Requirements
### Requirement: Domain-agnostic Scenario contract
The library SHALL expose an immutable `Scenario` (`id`, opaque `input`, `adapter`, `scorers`, `samples`, `tags`, `metadata`). The engine SHALL pass `input` verbatim to the adapter and SHALL NOT inspect its shape or import any consumer/domain type. The `Scenario.id` SHALL be the stable join key for baselines (independent of any test-runner node id).

#### Scenario: Engine treats input as opaque
- **WHEN** a `Scenario` is run
- **THEN** the engine passes `input` to the adapter unchanged and never accesses its internal fields

#### Scenario: Domain purity is enforced
- **WHEN** the engine source tree `edd_harness/` is searched for domain vocabulary (e.g. consumer role names like `role-a`, `role-c`, `vote`, `deliberation`)
- **THEN** no matches are found

### Requirement: Adapter seam and serialization guarantee
The engine SHALL invoke the consumer-supplied `Adapter` with the scenario `input` and SHALL require the returned `Output` to be JSON-serializable. A non-serializable `Output` MUST raise `EddContractError` and be recorded as INDETERMINATE. The engine MUST persist the `Output` verbatim to enable later rescoring without re-invoking the target.

#### Scenario: Serializable output is captured
- **WHEN** the adapter returns a JSON-serializable mapping
- **THEN** the engine round-trips it through `json.dumps`, records it verbatim, and proceeds to scoring

#### Scenario: Non-serializable output is surfaced
- **WHEN** the adapter returns a value that is not JSON-serializable
- **THEN** the engine raises `EddContractError` and records the scenario verdict INDETERMINATE (never pass or fail)

#### Scenario: Adapter raises
- **WHEN** the adapter raises an exception
- **THEN** the scenario verdict is INDETERMINATE and the suite continues with remaining scenarios

### Requirement: Uniform Scorer Protocol with independent evaluation
All scorers SHALL implement a single `Scorer` Protocol returning a binary `ScoreResult`. The engine SHALL evaluate every scorer independently, so every check is recorded on every run regardless of any other scorer's outcome.

#### Scenario: A failing check does not suppress others
- **WHEN** one deterministic scorer fails
- **THEN** every other scorer (including judge scorers) still runs and is recorded

### Requirement: Deterministic check scorer
The library SHALL provide a `check(name, fn, reason)` helper producing a deterministic `Scorer` over the `Output`. A check whose predicate raises (e.g. `KeyError` from capture-shape drift) MUST be recorded INDETERMINATE, never FAIL.

#### Scenario: Predicate evaluates
- **WHEN** the predicate returns `True` or `False`
- **THEN** the check records `passed` accordingly

#### Scenario: Predicate raises on shape drift
- **WHEN** the predicate raises (e.g. a renamed output key)
- **THEN** the check is recorded INDETERMINATE, not FAIL

### Requirement: Binary judge scorer
`JudgeScorer` SHALL send only selected `Output` slices (via `render` or `context_keys`) to the judge backend and SHALL coerce the result to a binary verified/not-verified verdict (never a Likert scale). It MUST record `{name, criteria, verified, reason, backend, judge_model}` on every run regardless of outcome.

#### Scenario: Judge result is recorded binary
- **WHEN** the judge backend returns a verdict
- **THEN** `JudgeScorer` records a binary verified/not-verified result plus metadata, regardless of pass or fail

### Requirement: Runner injects the judge backend
The runner SHALL resolve the judge backend once per run (via the cost-rule factory) and inject it, together with `judge_model`, into each `JudgeScorer` at evaluation time. The consumer-facing `JudgeScorer` constructor MUST NOT accept a backend argument, and `Scorer.score(output)` MUST remain output-only — consumers never supply or reference a backend.

#### Scenario: Backend is injected, not consumer-supplied
- **WHEN** a suite containing a `JudgeScorer` is run
- **THEN** the runner injects the resolved backend and `judge_model` into the scorer, and the consumer's `JudgeScorer(...)` construction includes no backend argument

### Requirement: Three-valued scenario verdict
The engine SHALL classify each scenario as `pass`, `fail`, or `indeterminate` with precedence: any failing check → `fail`; else any indeterminate check → `indeterminate`; else `pass`. An `indeterminate` verdict MUST NOT count as `pass` and MUST be excluded from regression accounting.

#### Scenario: Any failing check fails the scenario
- **WHEN** at least one scorer fails its fold
- **THEN** the scenario verdict is `fail`

#### Scenario: Indeterminate without failure
- **WHEN** no scorer fails but at least one check is indeterminate
- **THEN** the scenario verdict is `indeterminate`, not `pass`

### Requirement: Per-scorer samples fold
For `samples > 1` the engine SHALL invoke the adapter `samples` times on the same frozen input and fold results per scorer: a deterministic check passes only if ALL N samples pass; a judge check passes if at least `k` of N verify, where `k` defaults to `ceil(N/2)` and is per-scorer configurable. Deterministic and judge checks MUST NOT be pooled into a single shared threshold.

#### Scenario: Deterministic fold requires all samples
- **WHEN** one of N samples fails a deterministic check
- **THEN** that check fails

#### Scenario: Judge fold uses k-of-N
- **WHEN** at least `ceil(N/2)` of N samples verify a judge check
- **THEN** that check passes

#### Scenario: Judge fold fails below k
- **WHEN** fewer than `k` of N samples verify a judge check
- **THEN** that check fails

#### Scenario: k is per-scorer configurable
- **WHEN** a judge scorer declares its own `k`
- **THEN** the engine applies that `k` for that scorer instead of the `ceil(N/2)` default

### Requirement: Run API and CLI entry point
The library SHALL provide `run(Suite, model_under_test=...)` and an `edd run` command that REQUIRES `--model` (the model under test) and supports `--baseline`, `--tags`, `--samples`, and `--no-judge`. The `--baseline` flag (`baseline=True`) enables comparison against the blessed baseline and the regression gate (see the `results-baselines` capability); it MUST NOT write the baseline (only `bless` does).

#### Scenario: model_under_test is required
- **WHEN** a run is invoked without `model_under_test` / `--model`
- **THEN** the engine raises a clear error and does not run scenarios

#### Scenario: no-judge mode skips judge scorers
- **WHEN** `--no-judge` is set
- **THEN** only deterministic scorers are evaluated and no judge backend is invoked

#### Scenario: Baseline flag enables the regression gate
- **WHEN** `edd run --baseline` (or `run(..., baseline=True)`) is invoked
- **THEN** the run is compared against the blessed baseline and exits non-zero on any REGRESSED check; without `--baseline` the run only records results and never gates, and in neither case does `run` write the baseline

#### Scenario: Tag filtering selects scenarios
- **WHEN** `--tags <tag>` is supplied
- **THEN** only scenarios whose `tags` include the requested tag(s) are run

