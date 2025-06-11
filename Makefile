.PHONY: install test run clean

# Variables
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# Install dependencies
install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

# Run tests

test:
	$(PYTHON) -m pytest tests/

# Run the application
run:
	$(PYTHON) -m coboarding.main

# Clean up
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.py[co]" -delete

# Format code
format:
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

# Lint code
lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy .

# Install pre-commit hooks
install-hooks:
	$(PIP) install pre-commit
	pre-commit install

# Run the job application automation
apply-job:
	$(PYTHON) -m coboarding.automation.job_applicator --url https://bewerbung.jobs/325696/buchhalter-m-w-d
