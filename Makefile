# 🚀 Makefile for Industrial Inspection System Development
.PHONY: help install dev test clean lint format profile monitor docs

# Default target
help:
	@echo "🚀 Industrial Inspection System Development Commands:"
	@echo ""
	@echo "📦 Setup & Install:"
	@echo "  install     - Install all dependencies"
	@echo "  dev         - Setup development environment"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test        - Run all tests"
	@echo "  test-fast   - Run tests without coverage (faster)"
	@echo "  test-unit   - Run unit tests only"
	@echo "  test-int    - Run integration tests only"
	@echo ""
	@echo "🔧 Code Quality:"
	@echo "  lint        - Run linting (flake8, mypy)"
	@echo "  format      - Format code (black, isort)"
	@echo "  clean       - Clean cache and temporary files"
	@echo ""
	@echo "📊 Performance:"
	@echo "  profile     - Profile the application"
	@echo "  monitor     - Start performance monitor"
	@echo "  memory      - Check memory usage"
	@echo ""
	@echo "🚀 Development:"
	@echo "  dev-server  - Start hot reload development server"
	@echo "  multi-agent - Run multi-agent development"
	@echo "  debug       - Start debug session"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  docs        - Generate documentation"
	@echo "  docs-serve  - Serve documentation locally"

# Installation
install:
	pip install -r requirements-dev.txt
	pre-commit install

dev:
	@./scripts/setup_dev_environment.sh

# Testing
test:
	pytest test/ -v --cov=inspectors --cov=utils --cov-report=html --cov-report=term-missing

test-fast:
	pytest test/ -v --tb=short

test-unit:
	pytest test/ -v -m "unit" --tb=short

test-int:
	pytest test/ -v -m "integration" --tb=short

# Code Quality
lint:
	flake8 inspectors/ utils/ test/ --max-line-length=88
	mypy inspectors/ utils/ --ignore-missing-imports

format:
	black inspectors/ utils/ test/ --line-length=88
	isort inspectors/ utils/ test/ --profile=black

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ dist/ build/
	rm -rf temp_crops_* cache/ test_results/
	rm -f *.prof profile_output.prof

# Performance Monitoring
profile:
	python -m cProfile -o profile_output.prof test/test_mixed_inference.py
	@echo "📊 Profile saved to profile_output.prof"
	@echo "📈 View with: python -m pstats profile_output.prof"

monitor:
	python performance_monitor.py

memory:
	python -c "import psutil; import os; p = psutil.Process(os.getpid()); print(f'🧠 Memory: {p.memory_info().rss / 1024 / 1024:.1f}MB')"

# Development Tools
dev-server:
	python dev_server.py

multi-agent:
	python multi_agent_setup.py

debug:
	python -m pdb main.py

# Documentation
docs:
	mkdocs build

docs-serve:
	mkdocs serve

# Quick Development Cycle
dev-cycle: clean format lint test-fast
	@echo "✅ Development cycle complete!"

# Production Build
build: clean test lint format
	@echo "🏗️ Production build ready!"

# Continuous Integration
ci: install lint test
	@echo "✅ CI pipeline passed!"
