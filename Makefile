.PHONY: demo setup seed run test test-unit clean help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Install Python dependencies
	pip install -r requirements.txt

seed:  ## Seed mock data into SQLite (demo.db)
	python -m channel_analytics.data.seed

seed-reset:  ## Reset + seed mock data
	python -m channel_analytics.data.seed --reset

run:  ## Start API server on :8602
	python -m uvicorn app.main:app --host 127.0.0.1 --port 8602 --reload

test:  ## Run all unit tests
	python -m pytest tests/unit -x -v

test-original:  ## Run original tests (requires MySQL)
	python -m pytest tests/original -x -v

demo:  ## One-click: setup → seed → run (open http://127.0.0.1:8602)
	@echo "=== Channel Analytics Demo ==="
	@echo "Step 1: Installing dependencies..."
	pip install -q fastapi uvicorn sqlalchemy pydantic python-multipart pyjwt passlib[bcrypt] openpyxl pandas numpy apscheduler slowapi prometheus-client python-dotenv
	@echo "Step 2: Seeding mock data..."
	python -m channel_analytics.data.seed --reset
	@echo "Step 3: Starting API server on http://127.0.0.1:8602 ..."
	@echo "  Login: admin / admin123"
	@echo ""
	python -m uvicorn app.main:app --host 127.0.0.1 --port 8602

demo-bg:  ## Start demo in background
	pip install -q fastapi uvicorn sqlalchemy pydantic python-multipart pyjwt passlib[bcrypt] openpyxl pandas numpy apscheduler slowapi prometheus-client python-dotenv 2>/dev/null
	python -m channel_analytics.data.seed --reset 2>/dev/null
	python -m uvicorn app.main:app --host 127.0.0.1 --port 8602 &

clean:  ## Remove demo database
	rm -f data/demo.db
	rm -rf __pycache__ */__pycache__ */*/__pycache__
