"""Thin Typer CLI over the engine. The Python API (``edd_harness.run``) is primary."""

from __future__ import annotations

import dataclasses
from typing import Annotated

import typer

from .compare import REGRESSED, compare_run
from .config import load_config
from .judge.factory import resolve_backend
from .runner import run as run_suite
from .scenario import load_suite
from .store import bless as bless_run
from .store import read_run, write_run
from .store import rescore as rescore_run

app = typer.Typer(help="Evaluation-Driven Development harness.", no_args_is_help=True)


@app.command()
def run(
    spec: Annotated[
        str, typer.Argument(help="Scenario source as 'module:attr' (attr defaults to SCENARIOS)")
    ],
    model: Annotated[str, typer.Option("--model", help="Model under test (required)")],
    baseline: Annotated[
        bool, typer.Option("--baseline", help="Compare to blessed baseline and gate")
    ] = False,
    tags: Annotated[
        list[str] | None, typer.Option("--tags", help="Only run scenarios with these tags")
    ] = None,
    samples: Annotated[
        int | None, typer.Option("--samples", help="Override samples per scenario")
    ] = None,
    no_judge: Annotated[bool, typer.Option("--no-judge", help="Skip judge scorers")] = False,
    root: Annotated[str, typer.Option("--root", help="Consumer repo root (holds .edd/)")] = ".",
) -> None:
    suite = load_suite(spec)
    if samples is not None:
        suite.scenarios = [dataclasses.replace(s, samples=samples) for s in suite.scenarios]

    cfg = load_config(root)
    judge_backend = None
    if not no_judge and cfg.judge_backend:
        judge_backend = resolve_backend(cfg.judge_backend, model_under_test=model)

    result = run_suite(
        suite,
        model_under_test=model,
        judge_backend=judge_backend,
        no_judge=no_judge,
        tags=tuple(tags or ()),
    )
    path = write_run(result, root=root)
    counts = _verdict_counts(result)
    typer.echo(f"Ran {len(result.scenarios)} scenario(s): {counts}. Recorded to {path}")

    if baseline:
        cmp = compare_run(result, root=root)
        typer.echo(_format_comparison(cmp))
        if cmp.has_regression:
            typer.echo("REGRESSION detected.")
            raise typer.Exit(code=1)


@app.command()
def bless(
    run_path: Annotated[str, typer.Argument(help="Path to a run .jsonl to promote")],
    label: Annotated[str | None, typer.Option("--label")] = None,
    root: Annotated[str, typer.Option("--root")] = ".",
) -> None:
    path = bless_run(read_run(run_path), root=root, label=label)
    typer.echo(f"Blessed baseline written to {path}")


@app.command()
def report(
    run_path: Annotated[str, typer.Argument(help="Path to a run .jsonl")],
    root: Annotated[str, typer.Option("--root")] = ".",
) -> None:
    result = read_run(run_path)
    cmp = compare_run(result, root=root)
    typer.echo(_format_comparison(cmp))


@app.command()
def rescore(
    run_path: Annotated[str, typer.Argument(help="Path to a run .jsonl")],
    spec: Annotated[str, typer.Argument(help="Scenario source 'module:attr' with current scorers")],
    root: Annotated[str, typer.Option("--root")] = ".",
) -> None:
    result = rescore_run(run_path, load_suite(spec))
    path = write_run(result, root=root)
    typer.echo(
        f"Rescored {len(result.scenarios)} scenario(s): {_verdict_counts(result)}. -> {path}"
    )


def _verdict_counts(result) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sr in result.scenarios:
        counts[sr.verdict] = counts.get(sr.verdict, 0) + 1
    return counts


def _format_comparison(cmp) -> str:
    lines = [
        f"{i.classification:11} {i.scenario_id}::{i.scorer_name} "
        f"(was={i.baseline_status}, now={i.current_status})"
        for i in cmp.items
    ]
    regressed = sum(1 for i in cmp.items if i.classification == REGRESSED)
    lines.append(f"-- {len(cmp.items)} check(s), {regressed} regressed --")
    return "\n".join(lines)
