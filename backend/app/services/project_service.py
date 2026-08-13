"""Application service layer.

Route handlers stay thin: they parse HTTP and delegate here. This module owns
project/source lifecycle, canonical-input assembly, the single AI invocation and
persistence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Analysis, Project, Source
from app.schemas.api import AnalysisRead, ProjectCreate, ProjectRead, SourceRead
from app.schemas.canonical import CanonicalInput, CanonicalSource, SourceMetadata, SourceType
from app.schemas.discovery import DiscoveryOutput
from app.services.discovery_agent import BusinessDiscoveryAgent
from app.services.ingestion.base import IngestionError, NormalizedSource
from app.services.ingestion.registry import extract_file, fetch_url
from app.services.normalization.classifier import truncate
from app.services.poc_service import build_blueprint

PREVIEW_CHARS = 280


class NotFoundError(Exception):
    pass


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------
def create_project(db: Session, payload: ProjectCreate) -> ProjectRead:
    project = Project(
        name=payload.name,
        client_name=payload.client_name.strip(),
        description=payload.description.strip(),
    )
    db.add(project)
    db.commit()
    return _project_read(db, project)


def list_projects(db: Session) -> list[ProjectRead]:
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return [_project_read(db, p) for p in projects]


def get_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project '{project_id}' was not found.")
    return project


def read_project(db: Session, project_id: str) -> ProjectRead:
    return _project_read(db, get_project(db, project_id))


def _project_read(db: Session, project: Project) -> ProjectRead:
    source_count = db.scalar(
        select(func.count()).select_from(Source).where(Source.project_id == project.id)
    )
    has_analysis = db.scalar(
        select(func.count()).select_from(Analysis).where(Analysis.project_id == project.id)
    )
    return ProjectRead(
        project_id=project.id,
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        created_at=project.created_at,
        source_count=int(source_count or 0),
        has_analysis=bool(has_analysis),
    )


def reset_project(db: Session, project_id: str) -> ProjectRead:
    project = get_project(db, project_id)
    for source in list(project.sources):
        db.delete(source)
    for analysis in list(project.analyses):
        db.delete(analysis)
    db.commit()
    return _project_read(db, project)


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
def add_file_source(db: Session, project_id: str, filename: str, content_type: str, data: bytes) -> SourceRead:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise IngestionError(
            f"'{filename}' is {len(data) / 1_048_576:.1f} MB, over the "
            f"{settings.max_upload_bytes / 1_048_576:.0f} MB upload limit."
        )
    project = get_project(db, project_id)
    normalized = extract_file(filename, content_type, data)
    return _persist_source(db, project, normalized)


def add_url_source(db: Session, project_id: str, url: str) -> SourceRead:
    project = get_project(db, project_id)
    normalized = fetch_url(url)
    return _persist_source(db, project, normalized)


def _persist_source(db: Session, project: Project, normalized: NormalizedSource) -> SourceRead:
    settings = get_settings()
    content, was_truncated = truncate(normalized.content, settings.max_source_chars)

    next_ordinal = int(
        db.scalar(select(func.coalesce(func.max(Source.ordinal), 0)).where(Source.project_id == project.id)) or 0
    ) + 1

    metadata = dict(normalized.metadata)
    metadata.update(
        {
            "original_filename": normalized.name,
            "char_count": len(content),
            "truncated": was_truncated,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    source = Source(
        project_id=project.id,
        ordinal=next_ordinal,
        type=normalized.source_type.value,
        name=normalized.name,
        content=content,
        metadata_json=json.dumps(metadata),
    )
    db.add(source)
    db.commit()
    return _source_read(source)


def list_sources(db: Session, project_id: str) -> list[SourceRead]:
    get_project(db, project_id)
    sources = db.scalars(
        select(Source).where(Source.project_id == project_id).order_by(Source.ordinal)
    ).all()
    return [_source_read(s) for s in sources]


def delete_source(db: Session, project_id: str, source_id: str) -> None:
    source = next((s for s in list_source_rows(db, project_id) if s.source_id == source_id or s.id == source_id), None)
    if source is None:
        raise NotFoundError(f"Source '{source_id}' was not found in project '{project_id}'.")
    db.delete(source)
    db.commit()


def list_source_rows(db: Session, project_id: str) -> list[Source]:
    get_project(db, project_id)
    return list(
        db.scalars(select(Source).where(Source.project_id == project_id).order_by(Source.ordinal)).all()
    )


def _metadata(source: Source) -> SourceMetadata:
    try:
        raw = json.loads(source.metadata_json or "{}")
    except json.JSONDecodeError:
        raw = {}
    known = set(SourceMetadata.model_fields) - {"extra"}
    payload = {k: v for k, v in raw.items() if k in known}
    payload["extra"] = {k: v for k, v in raw.items() if k not in known}
    return SourceMetadata.model_validate(payload)


def _source_read(source: Source) -> SourceRead:
    preview = source.content[:PREVIEW_CHARS]
    if len(source.content) > PREVIEW_CHARS:
        preview += "..."
    return SourceRead(
        source_id=source.source_id,
        type=SourceType(source.type),
        name=source.name,
        char_count=len(source.content),
        preview=preview,
        metadata=_metadata(source),
        created_at=source.created_at,
    )


# --------------------------------------------------------------------------
# Canonical input + analysis
# --------------------------------------------------------------------------
def build_canonical_input(db: Session, project_id: str) -> CanonicalInput:
    rows = list_source_rows(db, project_id)
    return CanonicalInput(
        project_id=project_id,
        sources=[
            CanonicalSource(
                source_id=row.source_id,
                type=SourceType(row.type),
                name=row.name,
                content=row.content,
                metadata=_metadata(row),
            )
            for row in rows
        ],
    )


def analyze(db: Session, project_id: str, agent: BusinessDiscoveryAgent | None = None) -> AnalysisRead:
    project = get_project(db, project_id)
    canonical_input = build_canonical_input(db, project_id)

    result = (agent or BusinessDiscoveryAgent()).run(
        canonical_input,
        project_name=project.name,
        client_name=project.client_name,
        project_description=project.description,
    )

    record = Analysis(
        project_id=project.id,
        canonical_input_json=canonical_input.model_dump_json(),
        discovery_output_json=result.discovery.model_dump_json(),
        model=result.model,
        prompt_version=result.prompt_version,
        mocked=int(result.mocked),
    )
    db.add(record)
    db.commit()
    return _analysis_read(record, canonical_input, result.discovery)


def get_latest_analysis(db: Session, project_id: str) -> AnalysisRead:
    get_project(db, project_id)
    record = db.scalars(
        select(Analysis).where(Analysis.project_id == project_id).order_by(Analysis.created_at.desc()).limit(1)
    ).first()
    if record is None:
        raise NotFoundError(f"Project '{project_id}' has no analysis yet. Run Analyze first.")

    canonical_input = CanonicalInput.model_validate_json(record.canonical_input_json)
    discovery = DiscoveryOutput.model_validate_json(record.discovery_output_json)
    return _analysis_read(record, canonical_input, discovery)


def _analysis_read(record: Analysis, canonical_input: CanonicalInput, discovery: DiscoveryOutput) -> AnalysisRead:
    return AnalysisRead(
        analysis_id=record.id,
        project_id=record.project_id,
        created_at=record.created_at,
        model=record.model,
        mocked=bool(record.mocked),
        canonical_input=canonical_input,
        discovery=discovery,
        poc_blueprint=build_blueprint(discovery),
    )
