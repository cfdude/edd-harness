import pathlib

# The engine must contain ZERO domain vocabulary. Domain knowledge lives only in consumer
# scenarios/adapters (and in docs/specs, which are not part of the engine package).
# Illustrative consumer-domain terms — the point is the engine carries NONE of them.
BANNED = ["deliberation", "vote", "ticker", "stock", "trading", "portfolio", "diagnosis", "invoice"]

ENGINE = pathlib.Path(__file__).resolve().parent.parent / "edd_harness"


def test_engine_contains_no_domain_vocabulary():
    offenders = []
    for path in ENGINE.rglob("*.py"):
        text = path.read_text().lower()
        for term in BANNED:
            if term in text:
                offenders.append(f"{path.relative_to(ENGINE)} contains {term!r}")
    assert not offenders, offenders
