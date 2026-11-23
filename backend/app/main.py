from fastapi import FastAPI

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="University Department Management System", version="0.1.0")

    @app.get(f"{API_PREFIX}/health", tags=["health"])
    def health() -> dict[str, str]:
        """Liveness check. Public, no authentication."""
        return {"status": "ok"}

    return app


app = create_app()
