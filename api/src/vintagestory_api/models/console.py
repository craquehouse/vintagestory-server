"""Console-related Pydantic models."""

from pydantic import BaseModel, Field


class ConsoleCommandRequest(BaseModel):
    """Request body for console command endpoint."""

    command: str = Field(..., min_length=1, max_length=1000)
