"""File storage abstraction for JSON files."""

import os
import tempfile
from pathlib import Path


class JsonFileStore:
    """Minimal storage abstraction for JSON file operations."""

    def __init__(self, path: Path):
        """Initialize the store with a file path.

        Args:
            path: Path to the JSON file to store/load.
        """
        self.path = path

    def load(self) -> str | None:
        """Load content from the file if it exists.

        Returns:
            File content as string, or None if file doesn't exist.
        """
        if self.path.exists():
            return self.path.read_text()
        return None

    def save_atomic(self, content: str) -> None:
        """Save content to file atomically.

        Performs atomic write by writing to a temporary file first,
        then renaming it to the target file. This ensures the file
        is either fully written or not modified at all.

        Args:
            content: The content to write to the file.

        Raises:
            OSError: If the write operation fails.
        """
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent, prefix=".optigen_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            # os.replace is atomic on POSIX systems
            os.replace(tmp_path, self.path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
