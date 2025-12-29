# OptiGen

[![PyPI](https://img.shields.io/pypi/v/optigen)](https://pypi.org/project/optigen/)
[![Python Versions](https://img.shields.io/pypi/pyversions/optigen)](https://pypi.org/project/optigen/)
[![License](https://img.shields.io/github/license/OptigenIO/OptiGen-core)](LICENSE)

<p align="center">
  <img src="https://raw.githubusercontent.com/OptigenIO/OptiGen-core/main/static/logo.png" alt="OptiGen Logo" width="200"/>
</p>

AI-powered optimization modeling assistant built on [LangGraph](https://github.com/langchain-ai/langgraph) and [Deep Agents](https://github.com/langchain-ai/deepagents). OptiGen guides users from problem formulation through schema design to executable solvers.

## Quick Start (Usage First)

1. Install from PyPI:
   ```bash
   pip install optigen
   ```
2. Set environment variables (either export them or create a `.env` in the project root):
   ```bash
   # Required
   ANTHROPIC_API_KEY=your_anthropic_key  # Get your key at: https://console.anthropic.com/settings/keys

   # Optional (enables web search tools)
   TAVILY_API_KEY=your_tavily_key

   # Optional (tracing)
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_langsmith_key
   LANGSMITH_PROJECT=optigen
   ```
3. Run the CLI:
   ```bash
   optigen
   ```

## Features

- **Problem Formulation (problem_formulator)**: Clarifies objectives and constraints before any schema or code is produced.
- **Schema & Dataset Design (schema_dataset_designer)**: Creates request/response JSON schemas and example scenarios to match the agreed objectives/constraints.
- **Solver Generation & Execution (solver_coder)**: Proposes solver strategies, uses available Python deps, and registers runnable entrypoints aligned to the schemas.
- **Quick Start Mode**: Can auto-build initial models for common problem types (e.g., VRP, scheduling, inventory) with transparent assumptions.
- **Tool-Aware Workflow**: Uses search (Tavily, optional), code execution, and dependency awareness to keep solutions consistent across steps.

## Development (contributing)

### Development Installation
For contributing or modifying the source code:

1. Clone the repo:
   ```bash
   git clone https://github.com/OptigenIO/OptiGen-core.git
   cd OptiGen-core
   ```
2. Install in editable mode:
   ```bash
   pip install -e .
   ```

### Development Commands

- `make test` - Run unit tests
- `make lint` - Run linters and type checkers
- `make format` - Format code
- `make help` - Show all make commands
