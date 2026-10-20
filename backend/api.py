import json
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from api_schemas import EventPage, EventRead, RunPage, RunRead
from auth import AuthSettings, require_event_reader, require_run_reader
from database import database_engine
from event_repository import EventRepository, assert_reader_role
from run_repository import RunRepository

logger = logging.getLogger("aegisops.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def get_repository(request: Request) -> EventRepository:
    return EventRepository(request.app.state.engine)


def get_run_repository(request: Request) -> RunRepository:
    return RunRepository(request.app.state.engine)


def create_app(
    engine_factory: Callable[[], Engine] | None = None,
    auth_settings_factory: Callable[[], AuthSettings] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.auth_settings = (auth_settings_factory or AuthSettings.from_environment)()
        engine = (engine_factory or (lambda: database_engine("DB_PASSWORD")))()
        try:
            assert_reader_role(engine)
            app.state.engine = engine
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="AegisOps local event API", version="0.1.0", lifespan=lifespan,
                  description="Read-only simulated incident events with local viewer JWTs. Development identity issuer; not a production login system.")

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id, started = uuid4().hex, perf_counter()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        logger.info(json.dumps({"event": "http_request", "request_id": request_id,
                               "method": request.method, "path": request.url.path,
                               "subject": getattr(request.state, "principal", None),
                               "status": response.status_code,
                               "duration_ms": round((perf_counter() - started) * 1000, 2)}))
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError):
        logger.warning(json.dumps({"event": "database_unavailable",
                                   "request_id": request.state.request_id,
                                   "reason": type(error).__name__}))
        return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable"})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "mode": "local-simulation"}

    @app.get("/ready")
    def ready(repository: Annotated[EventRepository, Depends(get_repository)]) -> dict:
        repository.ready()
        return {"status": "ready", "mode": "local-simulation"}

    @app.get("/events", response_model=EventPage, dependencies=[Depends(require_event_reader)])
    def list_events(
        repository: Annotated[EventRepository, Depends(get_repository)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=10000)] = 0,
        source: Literal["simulator"] | None = None,
    ) -> EventPage:
        rows = repository.list_events(limit, offset, source)
        items = [EventRead.model_validate(row) for row in rows[:limit]]
        return EventPage(items=items, limit=limit, offset=offset,
                         returned=len(items), has_more=len(rows) > limit)

    @app.get("/events/{event_id}", response_model=EventRead, dependencies=[Depends(require_event_reader)])
    def get_event(
        event_id: Annotated[str, Path(pattern=r"^[a-f0-9]{64}$")],
        repository: Annotated[EventRepository, Depends(get_repository)],
    ) -> EventRead:
        row = repository.get_event(event_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return EventRead.model_validate(row)

    @app.get("/investigations", response_model=RunPage, dependencies=[Depends(require_run_reader)])
    def list_runs(
        repository: Annotated[RunRepository, Depends(get_run_repository)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=10000)] = 0,
        event_id: Annotated[str | None, Query(pattern=r"^[a-f0-9]{64}$")] = None,
    ) -> RunPage:
        rows = repository.list_runs(limit, offset, event_id)
        items = [RunRead.model_validate(row) for row in rows[:limit]]
        return RunPage(items=items, limit=limit, offset=offset,
                       returned=len(items), has_more=len(rows) > limit)

    @app.get("/investigations/{run_id}", response_model=RunRead, dependencies=[Depends(require_run_reader)])
    def get_run(
        run_id: Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")],
        repository: Annotated[RunRepository, Depends(get_run_repository)],
    ) -> RunRead:
        row = repository.get_run(run_id)
        if row is None:
            raise HTTPException(404, "Investigation not found")
        return RunRead.model_validate(row)

    return app


app = create_app()
