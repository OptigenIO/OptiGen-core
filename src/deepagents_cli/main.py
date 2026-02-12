"""Main entry point and CLI loop for deepagents."""

import argparse
import asyncio
import os
import sys
import warnings
from pathlib import Path

from deepagents_cli.optigen_config import OPTIGEN_ASCII

# Suppress UserWarnings from dependencies about field name shadowing
# These are from third-party libraries (langchain_tavily, pydantic) and not actionable
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Field name.*shadows an attribute.*"
)

# Add src directory to Python path to allow running this script directly
_script_dir = Path(__file__).parent
_src_dir = _script_dir.parent  # src/ directory
if _src_dir.exists() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import SandboxBackendProtocol

from deepagents_cli.commands import execute_bash_command, handle_command

# CRITICAL: Import config FIRST to set LANGSMITH_PROJECT before LangChain loads
from deepagents_cli.config import (
    COLORS,
    SessionState,
    console,
    settings,
)
from deepagents_cli.execution import execute_task
from deepagents_cli.input import ImageTracker, create_prompt_session
from deepagents_cli.integrations.sandbox_factory import (
    create_sandbox,
    get_default_working_dir,
)
from deepagents_cli.ui import TokenTracker, show_help

# Import the graph creation functions from react_agent
from react_agent.graph import create_graph


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DeepAgents - AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Help command
    subparsers.add_parser("help", help="Show help information")

    # Default interactive mode
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for separate memory stores (default: agent).",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting (disables human-in-the-loop)",
    )
    parser.add_argument(
        "--sandbox",
        choices=["none", "modal", "daytona", "runloop"],
        default="none",
        help="Remote sandbox for code execution (default: none - local only)",
    )
    parser.add_argument(
        "--sandbox-id",
        help="Existing sandbox ID to reuse (skips creation and cleanup)",
    )
    parser.add_argument(
        "--sandbox-setup",
        help="Path to setup script to run in sandbox after creation",
    )
    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Disable the startup splash screen",
    )

    return parser.parse_args()


async def simple_cli(
    agent,
    assistant_id: str | None,
    session_state,
    baseline_tokens: int = 0,
    backend=None,
    sandbox_type: str | None = None,
    setup_script_path: str | None = None,
    no_splash: bool = False,
) -> None:
    """Main CLI loop.

    Args:
        backend: Backend for file operations (CompositeBackend)
        sandbox_type: Type of sandbox being used (e.g., "modal", "runloop", "daytona").
                     If None, running in local mode.
        sandbox_id: ID of the active sandbox
        setup_script_path: Path to setup script that was run (if any)
        no_splash: If True, skip displaying the startup splash screen
    """
    console.clear()
    if not no_splash:
        console.print(OPTIGEN_ASCII, style=f"bold {COLORS['primary']}")
        console.print()

    # Extract sandbox ID from backend if using sandbox mode
    sandbox_id: str | None = None
    if backend:
        from deepagents.backends.composite import CompositeBackend

        # Check if it's a CompositeBackend with a sandbox default backend
        if isinstance(backend, CompositeBackend):
            if isinstance(backend.default, SandboxBackendProtocol):
                sandbox_id = backend.default.id
        elif isinstance(backend, SandboxBackendProtocol):
            sandbox_id = backend.id

    # Display sandbox info persistently (survives console.clear())
    if sandbox_type and sandbox_id:
        console.print(
            f"[yellow]⚡ {sandbox_type.capitalize()} sandbox: {sandbox_id}[/yellow]"
        )
        if setup_script_path:
            console.print(
                f"[green]✓ Setup script ({setup_script_path}) completed successfully[/green]"
            )
        console.print()

    if not settings.has_tavily:
        console.print(
            "[yellow]⚠ Web search disabled:[/yellow] TAVILY_API_KEY not found.",
            style=COLORS["dim"],
        )
        console.print(
            "  To enable web search, set your Tavily API key:", style=COLORS["dim"]
        )
        console.print(
            "    export TAVILY_API_KEY=your_api_key_here", style=COLORS["dim"]
        )
        console.print(
            "  Or add it to your .env file. Get your key at: https://tavily.com",
            style=COLORS["dim"],
        )
        console.print()

    if not settings.has_anthropic:
        console.print(
            "[bold red]❌ Error:[/bold red] ANTHROPIC_API_KEY not found.",
        )
        console.print(
            "  To use Anthropic models, set your Anthropic API key:", style=COLORS["dim"]
        )
        console.print(
            "    export ANTHROPIC_API_KEY=your_api_key_here", style=COLORS["dim"]
        )
        console.print(
            "  Or add it to your .env file:", style=COLORS["dim"]
        )
        console.print(
            "    ANTHROPIC_API_KEY=your_api_key_here", style=COLORS["dim"]
        )
        console.print(
            "  Get your key at: https://console.anthropic.com/settings/keys",
            style=COLORS["dim"],
        )
        console.print()
        sys.exit(1)

    if settings.has_deepagents_langchain_project:
        console.print(
            f"[green]✓ LangSmith tracing enabled:[/green] Deepagents → '{settings.deepagents_langchain_project}'",
            style=COLORS["dim"],
        )
        if settings.user_langchain_project:
            console.print(
                f"  [dim]User code (shell) → '{settings.user_langchain_project}'[/dim]"
            )
        console.print()

    console.print(
        "... Ready to code! What would you like to build?", style=COLORS["agent"]
    )

    if sandbox_type:
        working_dir = get_default_working_dir(sandbox_type)
        console.print(f"  [dim]Local CLI directory: {Path.cwd()}[/dim]")
        console.print(f"  [dim]Code execution: Remote sandbox ({working_dir})[/dim]")
    else:
        console.print(f"  [dim]Working directory: {Path.cwd()}[/dim]")

    console.print()

    if session_state.auto_approve:
        console.print(
            "  [yellow]⚡ Auto-approve: ON[/yellow] [dim](tools run without confirmation)[/dim]"
        )
        console.print()

    # Localize modifier names and show key symbols (macOS vs others)
    if sys.platform == "darwin":
        tips = (
            "  Tips: ⏎ Enter to submit, ⌥ Option + ⏎ Enter for newline (or Esc+Enter), "
            "⌃E to open editor, ⌃T to toggle auto-approve, ⌃C to interrupt"
        )
    else:
        tips = (
            "  Tips: Enter to submit, Alt+Enter (or Esc+Enter) for newline, "
            "Ctrl+E to open editor, Ctrl+T to toggle auto-approve, Ctrl+C to interrupt"
        )
    console.print(tips, style=f"dim {COLORS['dim']}")

    console.print()

    # Create prompt session, image tracker, and token tracker
    image_tracker = ImageTracker()
    session = create_prompt_session(
        assistant_id, session_state, image_tracker=image_tracker
    )
    token_tracker = TokenTracker()
    token_tracker.set_baseline(baseline_tokens)

    while True:
        try:
            user_input = await session.prompt_async()
            if session_state.exit_hint_handle:
                session_state.exit_hint_handle.cancel()
                session_state.exit_hint_handle = None
            session_state.exit_hint_until = None
            user_input = user_input.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        if not user_input:
            continue

        # Check for slash commands first
        if user_input.startswith("/"):
            result = handle_command(user_input, agent, token_tracker)
            if result == "exit":
                console.print("\nGoodbye!", style=COLORS["primary"])
                break
            if result:
                # Command was handled, continue to next input
                continue

        # Check for bash commands (!)
        if user_input.startswith("!"):
            execute_bash_command(user_input)
            continue

        # Handle regular quit keywords
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break
        await execute_task(
            user_input,
            agent,
            assistant_id,
            session_state,
            token_tracker,
            backend=backend,
            image_tracker=image_tracker,
        )


async def _run_agent_session(
    assistant_id: str,
    session_state,
    sandbox_backend=None,
    sandbox_type: str | None = None,
    setup_script_path: str | None = None,
) -> None:
    """Helper to create agent and run CLI session.

    Extracted to avoid duplication between sandbox and local modes.

    Args:
        model: LLM model to use
        assistant_id: Agent identifier for memory storage
        session_state: Session state with auto-approve settings
        sandbox_backend: Optional sandbox backend for remote execution
        sandbox_type: Type of sandbox being used
        setup_script_path: Path to setup script that was run (if any)
    """
    # Determine the backend to use for the graph
    if sandbox_backend is not None:
        # Use the sandbox backend for remote execution
        graph_backend = sandbox_backend
    else:
        # Use local filesystem backend with explicit CWD
        graph_backend = FilesystemBackend(root_dir=Path.cwd(), virtual_mode=True)

    # Create the graph with the provided model and backend
    # Use create_graph to load MCP tools (e.g., Context7) if configured
    agent = await create_graph(backend=graph_backend)

    # Baseline tokens set to 0 since we're using a different graph configuration
    baseline_tokens = 0

    await simple_cli(
        agent,
        assistant_id,
        session_state,
        baseline_tokens,
        backend=graph_backend,
        sandbox_type=sandbox_type,
        setup_script_path=setup_script_path,
        no_splash=session_state.no_splash,
    )


async def main(
    assistant_id: str,
    session_state,
    sandbox_type: str = "none",
    sandbox_id: str | None = None,
    setup_script_path: str | None = None,
) -> None:
    """Main entry point with conditional sandbox support.

    Args:
        assistant_id: Agent identifier for memory storage
        session_state: Session state with auto-approve settings
        sandbox_type: Type of sandbox ("none", "modal", "runloop", "daytona")
        sandbox_id: Optional existing sandbox ID to reuse
        setup_script_path: Optional path to setup script to run in sandbox
    """

    # Branch 1: User wants a sandbox
    if sandbox_type != "none":
        # Try to create sandbox
        try:
            console.print()
            with create_sandbox(
                sandbox_type, sandbox_id=sandbox_id, setup_script_path=setup_script_path
            ) as sandbox_backend:
                console.print(
                    f"[yellow]⚡ Remote execution enabled ({sandbox_type})[/yellow]"
                )
                console.print()

                await _run_agent_session(
                    assistant_id,
                    session_state,
                    sandbox_backend,
                    sandbox_type=sandbox_type,
                    setup_script_path=setup_script_path,
                )
        except (ImportError, ValueError, RuntimeError, NotImplementedError) as e:
            # Sandbox creation failed - fail hard (no silent fallback)
            console.print()
            console.print("[red]❌ Sandbox creation failed[/red]")
            console.print(f"[dim]{e}[/dim]")
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[bold red]❌ Error:[/bold red] {e}\n")
            console.print_exception()
            sys.exit(1)

    # Branch 2: User wants local mode (none or default)
    else:
        try:
            await _run_agent_session(assistant_id, session_state, sandbox_backend=None)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[bold red]❌ Error:[/bold red] {e}\n")
            console.print_exception()
            sys.exit(1)


def cli_main() -> None:
    """Entry point for console script."""
    # Fix for gRPC fork issue on macOS
    # https://github.com/grpc/grpc/issues/37642
    if sys.platform == "darwin":
        os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"

    # Note: LANGSMITH_PROJECT is already overridden in config.py (before LangChain imports)
    # This ensures agent traces → DEEPAGENTS_LANGSMITH_PROJECT
    # Shell commands → user's original LANGSMITH_PROJECT (via ShellMiddleware env)

    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        else:
            # Create session state from args
            session_state = SessionState(
                auto_approve=args.auto_approve, no_splash=args.no_splash
            )

            # API key validation happens in create_model()
            asyncio.run(
                main(
                    args.agent,
                    session_state,
                    args.sandbox,
                    args.sandbox_id,
                    args.sandbox_setup,
                )
            )
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C - suppress ugly traceback
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
