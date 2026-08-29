.PHONY: setup lint test test-unit test-property test-leakage test-integration \
        fixtures corpus label features train eval ablate figures results reproduce

setup:
	uv sync --all-extras
	uv run pre-commit install

lint:
	uv run ruff check src/a1 tests
	uv run ruff format --check src/a1 tests
	uv run mypy --strict src/a1

test:
	uv run pytest tests/ -x --tb=short

test-ci:
	uv run pytest tests/ --tb=short

test-unit:
	uv run pytest tests/unit -x

test-property:
	uv run pytest tests/property -x

test-leakage:
	uv run pytest tests/leakage -x

test-integration:
	uv run pytest tests/integration -x

fixtures:
	uv run python scripts/download_fixtures.py

# --- Stubs: implemented in later phases ---

corpus:
	uv run python scripts/acquire_corpus.py

corpus-dry:
	uv run python scripts/acquire_corpus.py --dry-run

label:
	@echo "S1 free supervision not yet implemented (P1)"
	@exit 1

features:
	@echo "S2-S6 feature extraction not yet implemented (P2+)"
	@exit 1

train:
	@echo "Training not yet implemented (P2+)"
	@exit 1

eval:
	@echo "Evaluation not yet implemented (P3)"
	@exit 1

ablate:
	@echo "Ablation matrix not yet implemented (P3+)"
	@exit 1

figures:
	@echo "Figure generation not yet implemented (P3+)"
	@exit 1

results:
	@echo "RESULTS.md generation not yet implemented (P3+)"
	@exit 1

reproduce:
	@echo "Reproduction not yet implemented (P8)"
	@exit 1
