PY := .venv/bin/python

.PHONY: check lint types test fix

check: lint types test

lint:
	.venv/bin/ruff check src/ scripts/ tests/

types:
	.venv/bin/ty check

test:
	$(PY) -m pytest tests/ -q

fix:
	.venv/bin/ruff check --fix src/ scripts/ tests/
