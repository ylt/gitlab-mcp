.PHONY: help check test format lint pylint typecheck pyrefly clean all

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

all: format lint pylint typecheck test ## Run all checks

check: lint pylint typecheck test ## Run all checks except formatting

format: ## Format code with ruff
	@echo "==> Formatting code with ruff..."
	uv run ruff format src/ tests/

lint: ## Lint code with ruff
	@echo "==> Linting code with ruff..."
	-uv run ruff check src/ tests/

pylint: ## Check architectural rules with pylint
	@echo "==> Checking architectural rules with pylint..."
	-uv run pylint src/gitlab_mcp/tools/

typecheck: pyrefly ## Run type checker (alias for pyrefly)

pyrefly: ## Type check with pyrefly
	@echo "==> Type checking with pyrefly..."
	-uv run pyrefly check src/

test: ## Run tests with pytest
	@echo "==> Running tests..."
	-uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "==> Running tests with coverage..."
	uv run pytest tests/ -v --cov=src/gitlab_mcp --cov-report=term-missing

clean: ## Clean up cache and build artifacts
	@echo "==> Cleaning up..."
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

fix: ## Auto-fix linting issues
	@echo "==> Auto-fixing with ruff..."
	uv run ruff check src/ tests/ --fix --unsafe-fixes

ci: format lint pylint typecheck test ## Run CI pipeline
