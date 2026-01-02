"""React Agent.

This module defines a custom reasoning and action agent graph.
It invokes tools in a simple loop.
"""

import warnings

# Suppress Pydantic serialization warnings for Context field
# This warning occurs because langgraph/deepagents expects context to serialize
# to None, but receives a Context object. This is expected behavior.
warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings:",
    category=UserWarning,
    module="pydantic.main",
)

from react_agent.graph import graph

__all__ = ["graph"]
