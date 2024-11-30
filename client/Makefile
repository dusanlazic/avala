.PHONY: mypy ruff check

mypy:
	uv run mypy .

ruff:
	uv run ruff format
	uv run ruff check --fix

check: mypy ruff
