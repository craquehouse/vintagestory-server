"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="VintageStory Server API",
    description="API for managing VintageStory dedicated game server",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"status": "ok", "message": "VintageStory Server API"}
