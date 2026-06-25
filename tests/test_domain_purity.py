import pathlib

# The engine must contain ZERO domain vocabulary. Domain knowledge lives only in consumer
# scenarios/adapters (and in docs/specs, which are not part of the engine package).
BANNED = ["role-a", "role-c", "role-b", "deliberation", "vote", "ticker", "stock", "trading", "portfolio"]

ENGINE = pathlib.Path(__file__).resolve().parent.parent / "edd_harness"


def test_engine_contains_no_domain_vocabulary():
    offenders = []
    for path in ENGINE.rglob("*.py"):
        text = path.read_text().lower()
        for term in BANNED:
            if term in text:
                offenders.append(f"{path.relative_to(ENGINE)} contains {term!r}")
    assert not offenders, offenders
