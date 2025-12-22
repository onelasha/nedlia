"""Nedlia API entry point."""

from fastapi import FastAPI


app = FastAPI(
    title="Nedlia API",
    description="Product placement validation platform API and saas",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to Nedlia API"}
