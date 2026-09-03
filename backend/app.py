import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import router
from src.db import Base, create_database


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Ticket Tailor Revenue API",
        version="0.1.0",
        description="Revenue and payout reporting for a single event organizer.",
    )

    engine, session_factory = create_database(
        database_url or os.getenv("DATABASE_URL", "sqlite:///./ticket_tailor.db")
    )
    Base.metadata.create_all(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


app = create_app()
