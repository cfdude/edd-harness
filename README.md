# edd-harness

Evaluation-Driven Development (EDD) harness — a generic, **domain-agnostic** Python library for
measuring non-deterministic LLM output against an answer key, with before/after baselines to
catch regression and drift. The agent-era analog of TDD.

The engine knows nothing about your domain. You supply **scenarios** (frozen inputs + an
**adapter** that calls your real system + **scorers**); the engine runs them, scores every
scorer independently, folds across samples, persists results as JSON-in-git, and compares each
run to a blessed baseline.

## Install

```bash
uv add edd-harness            # or: pip install edd-harness
```

A judge backend is needed only if you use `JudgeScorer`s: the flat-cost
`claude` CLI (Haiku) or a local Ollama server. Deterministic `check()` scorers need neither.

## Quick start (generic example)

```python
from edd_harness import Scenario, check, JudgeScorer, run, write_run, bless, compare_run

def my_adapter(scenario_input):
    # Call YOUR real system here, return a JSON-serializable dict.
    result = my_system(scenario_input)
    return {"answer": result.answer, "rationale": result.rationale}

SCENARIOS = [
    Scenario(
        id="greeting/polite",
        input={"prompt": "say hello"},
        adapter=my_adapter,
        samples=3,
        scorers=[
            check("non_empty", lambda o: len(o["answer"]) > 0),
            JudgeScorer("is_polite", "Is the answer polite and friendly?",
                        render=lambda o: o["answer"]),
        ],
    ),
]

result = run(SCENARIOS, model_under_test="my-system@v1")
write_run(result)                       # -> .edd/runs/<ts>__my-system@v1.jsonl
bless(result)                           # promote to .edd/baseline.json (first time)

# Later, after a change:
after = run(SCENARIOS, model_under_test="my-system@v2")
if compare_run(after).has_regression:   # joins to baseline per (scenario, scorer)
    raise SystemExit("regression!")
```

## CLI

```bash
edd run mypkg.corpus:SCENARIOS --model my-system@v1 --baseline   # gate on regression
edd bless .edd/runs/<run>.jsonl --label clean                    # set the baseline
edd report .edd/runs/<run>.jsonl                                 # classify vs baseline
edd rescore .edd/runs/<run>.jsonl mypkg.corpus:SCENARIOS         # re-grade stored outputs, no LLM
```

`--no-judge` skips judge scorers for fast deterministic iteration; `--tags` filters scenarios;
`--samples` overrides the per-scenario sample count.

## Design

See `openspec/changes/edd-harness-v1/` (spec) and
`docs/superpowers/specs/2026-06-25-edd-harness-v1-design.md` (approved design).
