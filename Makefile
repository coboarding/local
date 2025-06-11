.PHONY: install test run clean setup-ollama start-ollama stop-ollama check-ollama

# Variables
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
OLLAMA_URL = http://localhost:11434

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
	$(PYTHON) -m coboarding.automation.job_applicator --url https://example.com/job-application

# Run with visual analysis enabled
apply-job-visual:
	$(PYTHON) -m coboarding.automation.job_applicator --url $(URL) --visual

# Setup Ollama and LLaVA model
setup-ollama:
	chmod +x install_ollama.sh
	./install_ollama.sh

# Start Ollama service
start-ollama:
	sudo systemctl start ollama
	@echo "Ollama service started. Waiting for it to be ready..."
	@until curl -s $(OLLAMA_URL)/api/tags >/dev/null; do sleep 1; done
	@echo "Ollama is ready!"

# Stop Ollama service
stop-ollama:
	sudo systemctl stop ollama
	@echo "Ollama service stopped"

# Check Ollama status
check-ollama:
	@if curl -s $(OLLAMA_URL)/api/tags >/dev/null; then \
		echo "Ollama is running"; \
	else \
		echo "Ollama is not running"; \
		exit 1; \
	fi

# Prepare test files for upload
setup-test-files:
	mkdir -p data
	touch data/resume.pdf data/cover_letter.pdf data/certificates.pdf data/photo.jpg
	echo "Sample files created in data/ directory"

# Clean uploaded files
clean-uploads:
	rm -f upload_analysis.png upload_element_*.png form_initial.png after_uploads.png
	echo "Cleaned up upload artifacts"
