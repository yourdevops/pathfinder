# DevSSP Makefile
# Run both web server and background worker with interleaved logs

VENV := venv
PYTHON := $(VENV)/bin/python
PID_DIR := .pids
WEB_PID := $(PID_DIR)/web.pid
WORKER_PID := $(PID_DIR)/worker.pid

.PHONY: run stop clean help venv migrate build

help:
	@echo "DevSSP Development Commands"
	@echo ""
	@echo "  make run     - Start web server and worker (Ctrl+C to stop)"
	@echo "  make stop    - Stop running processes"
	@echo "  make migrate - Run database migrations"
	@echo "  make build   - Build Tailwind CSS"
	@echo "  make clean   - Stop processes and clean PID files"
	@echo "  make venv    - Create virtual environment"
	@echo ""

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		$(PYTHON) -m pip install -r requirements.txt; \
	fi

$(PID_DIR):
	@mkdir -p $(PID_DIR)

migrate: venv
	@$(PYTHON) manage.py migrate

build: venv
	@$(PYTHON) manage.py tailwind build

stop:
	@if [ -f "$(WEB_PID)" ] && kill -0 $$(cat $(WEB_PID)) 2>/dev/null; then \
		echo "Stopping web server..."; \
		kill -- -$$(cat $(WEB_PID)) 2>/dev/null || kill $$(cat $(WEB_PID)) 2>/dev/null || true; \
	fi
	@if [ -f "$(WORKER_PID)" ] && kill -0 $$(cat $(WORKER_PID)) 2>/dev/null; then \
		echo "Stopping worker..."; \
		kill -- -$$(cat $(WORKER_PID)) 2>/dev/null || kill $$(cat $(WORKER_PID)) 2>/dev/null || true; \
	fi
	@rm -f $(WEB_PID) $(WORKER_PID)
	@# Also kill any orphaned Django processes on port 8000
	@lsof -ti:8000 | xargs kill 2>/dev/null || true

clean: stop
	@rm -rf $(PID_DIR)
	@echo "Cleaned up"

run: venv $(PID_DIR) stop
	@./scripts/run-dev.sh $(PYTHON) $(WEB_PID) $(WORKER_PID)
