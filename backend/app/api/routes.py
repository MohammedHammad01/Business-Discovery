"""HTTP boundary. Handlers parse/validate and delegate to the service layer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.api import (
    AnalysisRead,
    HealthRead,
    ProjectCreate,
    ProjectRead,
    SourceRead,
    UrlSourceCreate,
)
from app.schemas.canonical import CanonicalInput
from app.services import project_service
from app.services.discovery_agent import DiscoveryAgentError
from app.services.ingestion.base import ExtractorUnavailableError, IngestionError
from app.services.ingestion.registry import extractor_status
from app.services.project_service import NotFoundError

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthRead, tags=["system"])
def health() -> HealthRead:
    settings = get_settings()
    return HealthRead(
        status="ok",
        ai_configured=settings.ai_configured,
        mock_enabled=settings.allow_mock_llm,
        model=settings.gemini_model if settings.ai_configured else "mock",
        extractors=extractor_status(),
    )


# --- projects -------------------------------------------------------------
@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, tags=["projects"])
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    return project_service.create_project(db, payload)


@router.get("/projects", response_model=list[ProjectRead], tags=["projects"])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return project_service.list_projects(db)


@router.get("/projects/{project_id}", response_model=ProjectRead, tags=["projects"])
def read_project(project_id: str, db: Session = Depends(get_db)) -> ProjectRead:
    try:
        return project_service.read_project(db, project_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/projects/{project_id}/reset", response_model=ProjectRead, tags=["projects"])
def reset_project(project_id: str, db: Session = Depends(get_db)) -> ProjectRead:
    try:
        return project_service.reset_project(db, project_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# --- sources --------------------------------------------------------------
@router.post(
    "/projects/{project_id}/sources",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
    tags=["sources"],
)
async def upload_source(
    project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> SourceRead:
    data = await file.read()
    try:
        return project_service.add_file_source(
            db, project_id, file.filename or "upload", file.content_type or "", data
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ExtractorUnavailableError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc
    except IngestionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post(
    "/projects/{project_id}/sources/url",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
    tags=["sources"],
)
def add_url_source(project_id: str, payload: UrlSourceCreate, db: Session = Depends(get_db)) -> SourceRead:
    try:
        return project_service.add_url_source(db, project_id, payload.url)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except IngestionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/projects/{project_id}/sources", response_model=list[SourceRead], tags=["sources"])
def list_sources(project_id: str, db: Session = Depends(get_db)) -> list[SourceRead]:
    try:
        return project_service.list_sources(db, project_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete(
    "/projects/{project_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["sources"],
)
def delete_source(project_id: str, source_id: str, db: Session = Depends(get_db)) -> None:
    try:
        project_service.delete_source(db, project_id, source_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/projects/{project_id}/canonical-input", response_model=CanonicalInput, tags=["sources"])
def canonical_input(project_id: str, db: Session = Depends(get_db)) -> CanonicalInput:
    """Exposed so the demo can show the exact contract handed to the AI agent."""
    try:
        return project_service.build_canonical_input(db, project_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# --- analysis -------------------------------------------------------------
@router.post("/projects/{project_id}/analyze", response_model=AnalysisRead, tags=["analysis"])
def analyze(project_id: str, db: Session = Depends(get_db)) -> AnalysisRead:
    try:
        return project_service.analyze(db, project_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except DiscoveryAgentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/projects/{project_id}/discovery", response_model=AnalysisRead, tags=["analysis"])
def get_discovery(project_id: str, db: Session = Depends(get_db)) -> AnalysisRead:
    try:
        return project_service.get_latest_analysis(db, project_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
