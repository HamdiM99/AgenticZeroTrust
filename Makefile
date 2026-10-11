.PHONY: install test lint eval mutate demo agentdojo all
install:
	pip install -e ".[dev]"
test:
	python -m pytest -q
lint:
	ruff check .
eval:
	python -m evals.run_eval --write --check
mutate:
	python scripts/mutation_check.py
demo:
	python examples/demo.py
agentdojo:
	python -m integrations.agentdojo.run_replay --write
all: lint test eval mutate
