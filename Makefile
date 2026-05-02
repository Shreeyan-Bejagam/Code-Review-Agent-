VENV_PYTHON := ../.venv/bin/python

.PHONY: test run-api run-worker

test:
	$(VENV_PYTHON) -m pytest -q tests

run-api:
	$(VENV_PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	$(VENV_PYTHON) -m app.queue.worker

