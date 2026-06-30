# Contributing to edd-harness

Thanks for your interest! edd-harness is a small, deliberately focused library. The most
important thing to understand before contributing is the one invariant that defines it.

## The non-negotiable rule: the engine is domain-agnostic

**`edd_harness/` must contain ZERO domain vocabulary.** No trading terms, no medical terms, no
consumer-specific concepts — nothing. All domain knowledge lives in the *consumer's* scenarios and
adapter, never in the engine. This is the entire reuse contract; if it leaks, the library stops
being usable by a second consumer.

This is enforced by a test (`tests/test_domain_purity.py`). A PR that puts a domain concept into
the engine will fail CI by design. If you need domain behavior, it belongs in your own adapter or
scorers, not here.

## Architecture in one minute

- **Scenario** = `id` + opaque `input` + an **adapter** + a list of **scorers** (+ `samples`, `tags`).
- **Adapter** = the single domain seam; it calls the consumer's system and returns a
  JSON-serializable dict. The engine never inspects `input` or imports a domain type.
- **Scorers** = one uniform `Scorer` protocol with two implementations: deterministic `check()`
  and the LLM-backed `JudgeScorer`. Every scorer is evaluated independently.
- **Judge backends** = flat-cost **by construction** (Claude CLI / Ollama). The metered API-key
  path is opt-in only and must never be returned by the factory.
- **Runner / store / compare** = run × samples → per-scorer fold → three-valued verdict → JSON-in-git
  baselines → regression gate.

The capability contract lives in `openspec/specs/`; the why/how of adopting the library is in
`docs/integration-guide.md`.

## Ground rules for changes

- **Keep judges flat-cost.** A new judge backend must default to a subscription/local path. Do not
  register a metered backend in the factory; the judge model must stay configurable and distinct
  from the model under test.
- **Don't add consumer-specific features.** If a change only serves one consumer's shape, it
  belongs in that consumer's adapter/scorers, not in the engine.
- **Behavior changes are reflected in `openspec/specs/`.** Update the relevant capability spec when
  you change observable behavior.

## Dev setup

```bash
uv sync
uv run pytest -q          # all tests must pass
uv run ruff check .       # lint must be clean
uv run ruff format .      # format before committing
```

Requires Python 3.13. The judge backends shell out to the local `claude` CLI or an Ollama server,
but the test suite uses fakes — you do not need either installed to run the tests.

## Pull requests

- New behavior or a bug fix needs a test that verifies it (TDD welcome).
- Keep PRs focused; conventional commit messages appreciated (`feat:`, `fix:`, `docs:`…).
- CI gates: `pytest` green, `ruff check`/`format` clean, and the domain-purity test passing.
- Adding a new judge backend? Subclass `JsonVerdictBackend`, and only register it in the factory
  if it is flat-cost.

By contributing you agree your contributions are licensed under the project's MIT License.
