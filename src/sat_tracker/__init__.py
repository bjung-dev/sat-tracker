import os


def main() -> None:
    """Start the web server (run with: uv run sat-tracker)."""
    import uvicorn

    uvicorn.run(
        "sat_tracker.api:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
