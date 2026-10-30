PYTHON := .venv/bin/python
# Docker's credential helper must also be on PATH on a fresh macOS install.
export PATH := $(PATH):/Applications/Docker.app/Contents/Resources/bin
DOCKER := $(shell command -v docker 2>/dev/null)
ifeq ($(DOCKER),)
DOCKER := /Applications/Docker.app/Contents/Resources/bin/docker
endif
COMPOSE := $(DOCKER) compose -f practice/airflow/compose.yaml

.PHONY: install test app airflow airflow-stop airflow-logs replay

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-analysis.txt

test:
	$(PYTHON) -m unittest -v test_main
	$(PYTHON) -m unittest discover -s practice -p 'test_*.py' -v

app:
	$(PYTHON) -m streamlit run app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false

airflow:
	$(COMPOSE) up -d

airflow-stop:
	$(COMPOSE) down

airflow-logs:
	$(COMPOSE) logs --tail=80 airflow

replay:
	$(PYTHON) practice/replay.py
