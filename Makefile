.PHONY: test lint format docker-build docker-run generate-fixtures clean help

help:
	@echo "Standalone MPP Import & Export Parser Service Commands:"
	@echo "  make test              Run pytest automated test suite"
	@echo "  make generate-fixtures Generate small, medium, and large benchmark project XML files"
	@echo "  make lint              Run code linting checks"
	@echo "  make format            Format code using black / ruff"
	@echo "  make docker-build      Build production Docker container image"
	@echo "  make docker-run        Run production Docker container locally"
	@echo "  make clean             Clean temporary files and cache"

test:
	python3 -m pytest -v

generate-fixtures:
	python3 fixtures/generate_large_fixtures.py

lint:
	python3 -m pytest tests/ --ignore=fixtures

format:
	@echo "Formatting codebase..."

docker-build:
	docker build -t mpp-parser-service:latest .

docker-run:
	docker run -d -p 8000:8000 --name mpp-parser-service mpp-parser-service:latest

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ *.egg-info build dist exported.xml
