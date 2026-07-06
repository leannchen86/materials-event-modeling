# The fast, mostly-correct verification loop (the AI-iteration ethos of engineering.md,
# translated from the TS stack to Python): ruff for real bug classes + import hygiene,
# ty for types on the reusable library, pytest for behavior. `make check` is the gate.
PY := .venv/bin/python

.PHONY: check lint types test fix

check: lint types test

lint:
	.venv/bin/ruff check src/ scripts/ tests/

types:  # gated on src+tests (see [tool.ty.src]); scripts are run-once, ruff-only
	.venv/bin/ty check

test:
	$(PY) -m pytest tests/ -q

fix:  # auto-fix the safe lint findings
	.venv/bin/ruff check --fix src/ scripts/ tests/
