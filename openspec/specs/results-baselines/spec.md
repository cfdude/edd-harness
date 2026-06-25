# results-baselines Specification

## Purpose
TBD - created by archiving change edd-harness-v1. Update Purpose after archive.
## Requirements
### Requirement: Run persistence in JSON-in-git
The engine SHALL append each run to `.edd/runs/<ISO-ts>__<model_under_test>.jsonl` in the consumer repo, recording one full per-scenario record — including the verbatim `Output`, every deterministic and judge check, the verdict, `model_under_test`, `judge_model`, and `samples` — for pass, fail, AND indeterminate scenarios alike.

#### Scenario: Every run is recorded
- **WHEN** a suite runs
- **THEN** each scenario (pass, fail, or indeterminate) is appended to the run log with its verbatim `Output`

### Requirement: Bless writes an axis-keyed baseline
The `bless` operation SHALL write `.edd/baseline.json` keyed by `(scenario_id, scorer_name)` under an axis key derived from `{model_under_test, judge_model}`, so a model or judge swap is recorded as a deliberate, auditable transition rather than silent drift.

#### Scenario: Blessing records the axis
- **WHEN** `edd bless <run-id>` is invoked
- **THEN** `baseline.json` is written keyed by `(scenario_id, scorer_name)` under the `{model_under_test, judge_model}` axis key

### Requirement: Before/after comparison and regression gate
When a run is invoked with `--baseline` (`baseline=True`) and a blessed baseline exists for the current axis key, the engine SHALL join the current run to the baseline per `(scenario_id, scorer_name)` for the same axis key and classify each as NEW, REGRESSED, FIXED, STABLE, or INDETERMINATE. Any REGRESSED result MUST cause `edd run --baseline` to exit non-zero. INDETERMINATE results MUST be excluded from regression accounting and MUST never be classified as REGRESSED. Comparison and the gate are owned by `edd run --baseline` (and reported by `edd report`); `bless` never gates.

#### Scenario: Regression fails the gate
- **WHEN** `edd run --baseline` is invoked and a check that was `pass` in the baseline is now `fail` (or a judge verdict flips verified true→false)
- **THEN** it is classified REGRESSED and the run exits non-zero

#### Scenario: Indeterminate is not a regression
- **WHEN** a check that was `pass` in the baseline is now indeterminate
- **THEN** it is excluded from regression accounting and does not cause a non-zero exit

#### Scenario: No baseline for the current axis
- **WHEN** `edd run --baseline` is invoked but the current `{model_under_test, judge_model}` axis key has no blessed baseline entry (e.g. a deliberate model or judge swap)
- **THEN** every check is classified NEW and the run does NOT exit non-zero (there is no prior baseline for that axis to regress against)

### Requirement: Rescore without re-invoking the target
The `rescore` operation SHALL re-grade the persisted verbatim `Output` of a prior run against the current scorers WITHOUT invoking the adapter or any LLM/judge call that costs money against the target.

#### Scenario: Rescore uses stored output
- **WHEN** `edd rescore <run-id>` is invoked
- **THEN** scorers are re-applied to the stored `Output` and no adapter or metered call is made

### Requirement: Human-readable drift review and CLI
Baselines and runs SHALL be plain JSON in git so that `git diff .edd/baseline.json` is a human-readable drift review. The library SHALL provide `bless`, `report`, and `rescore` CLI commands alongside `run`.

#### Scenario: Baseline diff is reviewable
- **WHEN** a baseline is re-blessed and the change is committed
- **THEN** `git diff` shows the per-check change in human-readable JSON

#### Scenario: Report summarizes a run
- **WHEN** `edd report <run-id>` is invoked
- **THEN** it prints a regression-focused classification summary of the run versus its baseline

