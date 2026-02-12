"""MCP (Model Context Protocol) integration for Context7 documentation search."""

import os
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient


async def get_mcp_tools() -> list[Any]:
    """Load MCP tools from Context7 if API key is configured.

    Returns:
        List of MCP tools if CONTEXT7_API_KEY is set, empty list otherwise.
    """
    context7_api_key = os.getenv("CONTEXT7_API_KEY")

    if not context7_api_key:
        # Context7 integration is disabled - return empty list
        return []

    try:
        # Configure MCP client to run Context7 server via npx
        # The Context7 MCP server is published as @upstash/context7-mcp
        client = MultiServerMCPClient(
            {
                "context7": {
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp"],
                    "transport": "stdio",
                    "env": {
                        "CONTEXT7_API_KEY": context7_api_key,
                    },
                }
            }
        )

        # Get tools from the MCP server
        tools = await client.get_tools()
        return tools

    except Exception as e:
        # If there's any error loading MCP tools, log it and return empty list
        # This ensures the agent can still function without Context7
        print(f"Warning: Failed to load Context7 MCP tools: {e}")
        return []
