# OptiGen

<img src="https://raw.githubusercontent.com/OptigenIO/OptiGen-core/main/static/logo.png" alt="OptiGen Logo" width="200"/>


An AI-powered optimization modeling assistant built on [LangGraph](https://github.com/langchain-ai/langgraph).

OptiGen guides users through formulating optimization problems—from defining objectives and constraints to generating and validating Python solvers.

## Features

- **Guided Problem Formulation**: Step-by-step process to define objectives, constraints, and data schemas
- **Quick Start Mode**: Build initial models using popular assumptions for common problem types (VRP, scheduling, inventory)
- **Solver Generation**: Automatically generate Python optimization scripts
- **Validation**: Test solvers against example data to verify correctness

## Getting Started

1. Copy `.env.example` to `.env` and add your API keys
2. Start the development server:
   ```bash
   make start
   ```
   This will start the LangGraph dev server and open the browser automatically.

Alternatively, you can open the project in [LangGraph Studio](https://github.com/langchain-ai/langgraph-studio).

## Development Commands

Useful Make commands for development:

- `make start` - Start the development server (stops any existing server first)
- `make stop` - Stop the development server
- `make dev` - Run LangGraph dev server
- `make test` - Run unit tests
- `make integration_tests` - Run integration tests
- `make test_watch` - Run unit tests in watch mode
- `make lint` - Run linters and type checkers
- `make format` - Format code with ruff
- `make spell_check` - Check spelling
- `make help` - Show all available commands

