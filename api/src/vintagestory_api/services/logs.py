"""Log file service for streaming VintageStory server logs."""

import asyncio
from pathlib import Path

import structlog

logger = structlog.get_logger()


class LogFileNotFoundError(Exception):
    """Raised when a requested log file does not exist."""

    pass


class LogFileAccessError(Exception):
    """Raised when a log file cannot be accessed (permissions, etc.)."""

    pass


def validate_log_filename(filename: str) -> bool:
    """Validate that a log filename is safe and allowed.

    Prevents path traversal attacks and restricts to expected log file types.

    Args:
        filename: The filename to validate.

    Returns:
        True if the filename is valid, False otherwise.
    """
    # Reject empty or whitespace-only filenames
    if not filename or not filename.strip():
        return False

    # Reject path traversal attempts
    if "/" in filename or "\\" in filename or ".." in filename:
        return False

    # Must have a valid log extension
    path = Path(filename)
    if path.suffix not in (".log", ".txt"):
        return False

    # Reject hidden files
    if filename.startswith("."):
        return False

    return True


async def tail_log_file(
    logs_dir: Path,
    filename: str,
    lines: int = 100,
) -> list[str]:
    """Read the last N lines from a log file.

    Args:
        logs_dir: Path to the logs directory.
        filename: Name of the log file (validated, no path traversal).
        lines: Number of lines to return from the end.

    Returns:
        List of lines from the end of the file.

    Raises:
        LogFileNotFoundError: If the file doesn't exist.
        LogFileAccessError: If the file can't be read.
    """
    if not validate_log_filename(filename):
        raise LogFileAccessError(f"Invalid log filename: {filename}")

    file_path = logs_dir / filename

    if not file_path.exists():
        raise LogFileNotFoundError(f"Log file not found: {filename}")

    if not file_path.is_file():
        raise LogFileAccessError(f"Not a file: {filename}")

    try:
        # Read file in a thread pool to avoid blocking
        def read_tail() -> list[str]:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                # Read all lines and return last N
                all_lines = f.readlines()
                return [line.rstrip("\n\r") for line in all_lines[-lines:]]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, read_tail)

    except PermissionError as e:
        raise LogFileAccessError(f"Permission denied: {filename}") from e
    except OSError as e:
        raise LogFileAccessError(f"Error reading file: {e}") from e


