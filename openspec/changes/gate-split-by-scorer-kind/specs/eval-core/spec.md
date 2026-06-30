## MODIFIED Requirements

### Requirement: Run API and CLI entry point
The library SHALL provide `run(Suite, model_under_test=...)` and an `edd run` command that REQUIRES `--model` (the model under test) and supports `--baseline`, `--tags`, `--samples`, `--no-judge`, and `--strict`. The `--baseline` flag (`baseline=True`) enables comparison against the blessed baseline and the regression gate (see the `results-baselines` capability); it MUST NOT write the baseline (only `bless` does). The `--strict` flag (only meaningful with `--baseline`) makes judge (advisory) regressions blocking; without it, only deterministic regressions gate. Supplied without `--baseline`, `--strict` has no effect.

#### Scenario: model_under_test is required
- **WHEN** a run is invoked without `model_under_test` / `--model`
- **THEN** the engine raises a clear error and does not run scenarios

#### Scenario: no-judge mode skips judge scorers
- **WHEN** `--no-judge` is set
- **THEN** only deterministic scorers are evaluated and no judge backend is invoked

#### Scenario: Baseline flag enables the regression gate
- **WHEN** `edd run --baseline` (or `run(..., baseline=True)`) is invoked
- **THEN** the run is compared against the blessed baseline and exits non-zero on a blocking (deterministic) regression; without `--baseline` the run only records results and never gates, and in neither case does `run` write the baseline

#### Scenario: Strict flag blocks on any regression
- **WHEN** `edd run --baseline --strict` is invoked
- **THEN** both deterministic and judge regressions are treated as blocking and cause a non-zero exit

#### Scenario: Tag filtering selects scenarios
- **WHEN** `--tags <tag>` is supplied
- **THEN** only scenarios whose `tags` include the requested tag(s) are run
