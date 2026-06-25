# judge-backend Specification

## Purpose
TBD - created by archiving change edd-harness-v1. Update Purpose after archive.
## Requirements
### Requirement: JudgeBackend protocol and binary verdict
The library SHALL define a `JudgeBackend` Protocol with `name`, `model`, and `verify(rendered, criteria) -> Verdict`, where `Verdict` carries a binary `verified: bool` and a short `reason`. Backends MUST raise `EddJudgeUnavailable` on outage rather than returning a verdict.

#### Scenario: Backend returns a binary verdict
- **WHEN** `verify` is called with rendered output and criteria
- **THEN** it returns a `Verdict` with a boolean `verified` and a `reason` string

### Requirement: Cost-rule-enforcing backend factory
The factory SHALL resolve a backend from config/env to a flat-cost path only: `ClaudeCliJudge` (Haiku, default) or `OllamaJudge`. The metered `ApiKeyJudge` MUST NOT be returnable by the factory or selectable by any config string/auto-detection; it is reachable only by explicit consumer construction. If no flat-cost backend is available, the factory MUST raise rather than fall back to a metered path.

#### Scenario: Default resolves to flat-cost backend
- **WHEN** no backend is configured and the Claude CLI is available
- **THEN** the factory returns `ClaudeCliJudge` (Haiku), never a metered backend

#### Scenario: No flat-cost backend available
- **WHEN** neither the Claude CLI nor Ollama is available
- **THEN** the factory raises a clear error and does not return a metered backend

#### Scenario: Metered path is opt-in only
- **WHEN** any config string or auto-detection is used to select a backend
- **THEN** `ApiKeyJudge` is never selected; it is constructible only explicitly by the consumer

### Requirement: Judge must differ from model under test
The engine SHALL hard-error when `judge_model == model_under_test`. `judge_model` MUST be recorded on every verdict and MUST be part of the baseline axis key.

#### Scenario: Identical models rejected
- **WHEN** the resolved `judge_model` equals the supplied `model_under_test`
- **THEN** the engine raises before running any scenario

### Requirement: Judge failure handling
A judge that is unavailable MUST cause the check to be recorded INDETERMINATE. A judge whose output is unparseable MUST be retried once and, if still unparseable, recorded INDETERMINATE — it MUST NEVER be mapped to `verified = False`.

#### Scenario: Judge unavailable
- **WHEN** the backend raises `EddJudgeUnavailable`
- **THEN** the check is recorded INDETERMINATE and excluded from regression accounting

#### Scenario: Judge output unparseable
- **WHEN** the backend returns unparseable output twice (initial + one retry)
- **THEN** the check is recorded INDETERMINATE, never `verified = False`

