"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from . import prompts
from .project_snapshot import ProjectSettings


class Context(BaseModel):
    """The context for the agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    system_prompt: str = Field(
        default=prompts.BASE_SYSTEM_PROMPT,
        description="The system prompt to use for the agent's interactions. "
        "This prompt sets the context and behavior for the agent.",
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = Field(
        default="anthropic/claude-haiku-4-5",
        description="The name of the language model to use for the agent's main interactions. "
        "Should be in the form: provider/model-name.",
    )

    max_search_results: int = Field(
        default=5,
        description="The maximum number of search results to return when using the search tool.",
    )

    project_settings: Annotated[Optional[ProjectSettings], SkipJsonSchema()] = Field(
        default_factory=lambda: ProjectSettings(directory=Path.cwd()),
        description="The project settings containing problem specification, "
        "constraints, and schema definitions.",
        exclude=True,
    )

    def __init__(self, **data: Any) -> None:
        """Initialize the context, fetching environment variables for attributes not passed as args."""
        super().__init__(**data)
        # Fetch env vars for attributes that were not passed as args.
        for name in self.__class__.model_fields:
            if name not in self.model_fields_set:
                env_val = os.environ.get(name.upper())
                if env_val is not None:
                    setattr(self, name, env_val)
