from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, departments, students, teachers

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="University Department Management System", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # auth uses a Bearer header, not cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{API_PREFIX}/health", tags=["health"])
    def health() -> dict[str, str]:
        """Liveness check. Public, no authentication."""
        return {"status": "ok"}

    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(departments.router, prefix=API_PREFIX)
    app.include_router(teachers.router, prefix=API_PREFIX)
    app.include_router(students.router, prefix=API_PREFIX)

    return app


app = create_app()
