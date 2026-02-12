.PHONY: all check format lint spell_check spell_fix test tests test_watch integration_tests docker_tests help extended_tests stop clean

# Default target executed when no arguments are given to make.
all: help

######################
# DEVELOPMENT
######################
start: stop
	(sleep 2 && open "https://agentchat.vercel.app/?apiUrl=http://localhost:2024&assistantId=agent") & langgraph dev --no-browser

stop:
	@lsof -ti :2024 | xargs kill -9 || true
	@rm -rf .langgraph_api || true

clean: stop
	@echo "Cleared LangGraph state and stopped server"

dev:
	langgraph dev


######################
# TESTS
######################
# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/

test:
	uv run pytest $(TEST_FILE)

integration_tests:
	uv run pytest tests/integration_tests

test_watch:
	uv run ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	uv run pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	uv run pytest --only-extended $(TEST_FILE)


######################
# LINTING AND FORMATTING
######################

check: lint spell_check test

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict src/

format:
	uv run ruff format .
	uv run ruff check --fix .

spell_check:
	uv run codespell

spell_fix:
	uv run codespell -w

######################
# HELP
######################

help:
	@echo '----'
	@echo 'start                        - start LangGraph dev server (clears state from previous runs)'
	@echo 'stop                         - stop LangGraph dev server and clear state'
	@echo 'clean                        - stop server and clear all LangGraph state/checkpoints'
	@echo 'dev                          - run LangGraph dev server'
	@echo 'check                        - run all CI checks (lint + spell_check + test)'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters (ruff + mypy)'
	@echo 'spell_check                  - run codespell'
	@echo 'test                         - run unit tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'

