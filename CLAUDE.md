# CLAUDE.md — edd-harness

Guidance for AI agents and contributors working in this repo.

## What this is

`edd-harness` is a generic, **domain-agnostic** Python library for Evaluation-Driven Development
(EDD): measure non-deterministic LLM output against an answer key, with before/after baselines to
catch regression and drift. The agent-era analog of TDD.

## The one non-negotiable invariant

**`edd_harness/` must contain ZERO domain vocabulary.** No trading/medical/consumer-specific terms
— nothing. All domain knowledge lives in the *consumer's* scenarios and adapter, never in the
engine. This is the entire reuse contract. It is enforced by `tests/test_domain_purity.py`; a
change that puts a domain concept into the engine fails CI by design.

## Architecture (one minute)

- **Scenario** = `id` + opaque `input` + an **adapter** + a list of **scorers** (+ `samples`, `tags`).
- **Adapter** = the single domain seam; calls the consumer's system, returns a JSON-serializable dict.
  The engine never inspects `input` or imports a domain type.
- **Scorers** = one uniform `Scorer` protocol: deterministic `check()` and LLM-backed `JudgeScorer`,
  each evaluated independently.
- **Judge backends** = flat-cost **by construction** (Claude CLI Haiku / Ollama). The metered
  API-key path is opt-in only and never returned by the factory; the judge model must differ from
  the model under test.
- **Runner / store / compare** = run × samples → per-scorer fold → three-valued verdict
  (pass / fail / indeterminate) → JSON-in-git baselines → regression gate.

Capability contract: `openspec/specs/`. Adoption guide: `docs/integration-guide.md`.

## Build flow (OpenSpec lane)

New capability work goes through OpenSpec + two review gates:
`openspec new change <id>` → write proposal/design/specs/tasks → `openspec validate --strict` →
**🚦 Gate 1** (spec review) → implement with TDD (RED→GREEN), one commit per task → **🚦 Gate 2**
(implementation review) → docs → `openspec archive <id>`.

## Toolchain

Python 3.13 + `uv` + `pytest` + `ruff`.

```bash
uv run pytest -q          # all tests must pass
uv run ruff check .       # lint clean
uv run ruff format .      # format before committing
```

The judge backends shell out to the local `claude` CLI or an Ollama server, but the test suite
uses fakes — neither is needed to run the tests.

## Ground rules

- Keep the engine domain-agnostic (see the invariant above).
- Keep judges flat-cost; never register a metered backend in the factory.
- Reflect observable behavior changes in `openspec/specs/`.
- Behavior changes need a test; conventional commit messages appreciated.

See `CONTRIBUTING.md` for the contributor-facing version of these rules.
