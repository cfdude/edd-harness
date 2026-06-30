# Integrating edd-harness into a project

This is the producer-side guide: how *any* consuming project adopts edd-harness to put a
regression/drift safety net under a non-deterministic LLM component. It is domain-agnostic — your
domain lives entirely in the scenarios and adapter you write, never in the engine.

## Why adopt it

Deterministic code has TDD, linting, and code review. A non-deterministic LLM component (a
multi-agent deliberation, a classifier, a summarizer, a free-text interpreter) has none of that:
a prompt tweak or model bump can silently degrade behavior with **no error thrown**. edd-harness
turns each change into a measured before/after experiment so a regression fails a gate instead of
shipping unnoticed.

## When it applies (the decision test)

Use edd-harness when **all** of these hold:
1. The thing you're evaluating is a **non-deterministic LLM judgment**.
2. You **cannot** check it deterministically (if you can, a plain unit test is the sharper tool).
3. It **recurs** — you change it over time and need to know if behavior held.

If the output is code or any assertable value, use TDD instead. edd-harness is for emergent
behavior, scored as a *distribution* with relational/role invariants, not exact equality.

## Where it goes in a consumer

```
your_project/
  your_pkg/                  # your real system (unchanged)
  evals/                     # NEW — the corpus you author
    adapter.py               #   the ONLY domain seam: calls your system, returns a JSON dict
    corpus.py                #   SCENARIOS: list[Scenario]  (frozen inputs + scorers)
    fixtures/                #   frozen input payloads
  .edd/                      # NEW — created by the harness
    runs/*.jsonl             #   per-run records (gitignored or committed, your call)
    baseline.json            #   the blessed baseline — COMMIT THIS (git diff = drift review)
  pyproject.toml             #   add edd-harness dep + optional [tool.edd]
```

Nothing in `evals/` touches your system's internals beyond the one adapter call. A second
component (or project) adopts by writing only its own `adapter.py` + `corpus.py`.

## How to integrate (step by step)

**1. Add the dependency**
```bash
uv add edd-harness        # or: pip install edd-harness
```

**2. Write the adapter** — the single domain seam. It calls your real system *in your process,
with your own credentials*, and returns a JSON-serializable dict of primitives:
```python
# evals/adapter.py
from your_pkg import run_my_system

def adapter(scenario_input):
    result = run_my_system(scenario_input)          # your real component, your creds
    return {                                          # normalize -> plain JSON types
        "decision": result.decision,
        "confidence": result.confidence,
        "rationale": result.rationale,
    }
```
The engine round-trips this through `json.dumps`; a non-serializable value fails loudly as
INDETERMINATE rather than corrupting the record.

**3. Author scenarios** — frozen input + scorers. Prefer **relational invariants** you can assert
without knowing the "right" answer (e.g. ordering between roles, "at least one X", "must not
unanimously Y"). Deterministic `check()`s cost nothing; `JudgeScorer`s call a flat-cost judge.
```python
# evals/corpus.py
from edd_harness import Scenario, check, JudgeScorer
from evals.adapter import adapter

SCENARIOS = [
    Scenario(
        id="case/clean-positive",
        input=load_fixture("clean_positive.json"),
        adapter=adapter,
        samples=3,                                    # K>=3 (see "Lessons"); K=2 was not stable
        tags=("smoke",),
        scorers=[
            check("decided", lambda o: o["decision"] in {"YES", "NO"}),
            check("confident_enough", lambda o: o["confidence"] >= 0.5),
            JudgeScorer("rationale_is_specific",
                        "Does the rationale cite a concrete, specific reason (not boilerplate)?",
                        render=lambda o: o["rationale"]),
        ],
    ),
]
```

**4. Set up the judge backend (cost rule)** — judge calls MUST be flat-cost. Default is the local
`claude` CLI pinned to Haiku; alternative is a local Ollama server. The metered API-key path is
opt-in only and never auto-selected.
```toml
# pyproject.toml
[tool.edd]
judge = { backend = "claude-cli" }   # or "ollama"; or set EDD_JUDGE_BACKEND
```
Deterministic-only corpora need no judge at all (`--no-judge`).

**5. Establish the baseline** — run once, eyeball it, bless it, commit it:
```bash
edd run your_pkg.evals.corpus:SCENARIOS --model my-system@v1
edd bless .edd/runs/<that-run>.jsonl --label baseline-v1
git add .edd/baseline.json && git commit -m "edd: bless baseline-v1"
```

**6. Wire the gate** — in CI or a pre-merge check, run with `--baseline`; it exits non-zero on any
REGRESSED check:
```bash
edd run your_pkg.evals.corpus:SCENARIOS --model my-system@v1 --baseline
```
The baseline is axis-keyed by `{model_under_test, judge_model}`, so a deliberate model or judge
swap classifies as NEW (not a regression) until you re-bless under the new axis.

**7. Iterate cheaply** — after improving a scorer, re-grade *stored outputs* without re-running
your system or paying for the judge:
```bash
edd rescore .edd/runs/<run>.jsonl your_pkg.evals.corpus:SCENARIOS
```

## What you get

- A failing gate when behavior regresses, instead of silent drift.
- A git-reviewable history of behavior (`git diff .edd/baseline.json`).
- Drift detection across model versions via the axis key.
- A measured answer to "did changing this prompt/model actually help?"

## Mental model

`run` records and (with `--baseline`) gates · `bless` is the only writer of the baseline ·
`report` classifies a run vs baseline · `rescore` re-grades stored outputs for free. Verdicts are
three-valued: **pass / fail / indeterminate**, and `indeterminate` (adapter raised, judge
unavailable, shape drift) is excluded from regression accounting so flakes never masquerade as
regressions.

## Lessons from the first consumer (consumer)

The a consumer project multi-agent deliberation was the first real adopter. Two empirical findings worth
heeding before you trust your gate:

- **Use K ≥ 3 samples for a trustworthy deterministic gate.** At `samples=2`, *no-change* runs
  produced **false deterministic regressions** — the gate cried wolf. At `samples=3`, two
  back-to-back no-change runs showed **zero** deterministic regressions. So a deterministic
  REGRESSED at K ≥ 3 genuinely means behavior changed; below that, it may just be noise.
- **Treat deterministic and judge regressions differently.** Judge invariants flip run-to-run
  **even with no change** (the judge is itself stochastic), whereas deterministic relational
  invariants are stable at K ≥ 3. Practical rule:
  - a **deterministic** REGRESSED → **do-not-ship** (block the merge);
  - a **judge** REGRESSED → **advisory** — review it, don't auto-block.

  edd-harness's `compare` currently classifies all checks uniformly; the deliberation consumer split
  its own gate on `scorer_type` (deterministic block vs stochastic judge review). Until the engine
  promotes that split (see the v2 backlog), do the same in your CI: gate on deterministic
  REGRESSED, surface judge REGRESSED as a warning.
- **Scope a relational invariant to the cases where it discriminates — don't blanket-apply it.**
  The deliberation's "Role A ≥ Role C proceed-lean" ordering is the gold signal on *proceed-dimension*
  cases (clean-buy, role-a-drift), but it MISSED on a clean-avoid case: a correctly-bearish Role A
  legitimately held higher PASS conviction than Role C, which strict ordering misreads as a role
  inversion. The fix was to disable that ordering check on avoid cases, not to weaken it. Lesson:
  a relational invariant that's sound in one direction can be wrong in another — attach it only to
  the scenarios where it's actually discriminating.
- **Judge scorers need rationale PROSE in the captured Output.** The deliberation's judges had thin
  signal on proceed votes because the adapter captured structured JSON and the prose rationale had
  been parsed away upstream — leaving the judge little to evaluate. Any field a `JudgeScorer`
  reads (via `render`/`context_keys`) must contain real natural-language rationale; if your
  adapter normalizes output down to structured fields only, your judges are starved. (One more
  reason judges are advisory and deterministic checks are the gold signal.)

## Project-specific adoption

A consumer's actual adoption (which component, which scenarios, where the baseline lives, how the
gate runs) is tracked in *that project's* own plan. For the a consumer project deliberation, see the
`consumer` OpenSpec change in the a consumer project repo.
