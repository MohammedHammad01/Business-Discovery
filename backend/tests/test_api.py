"""End-to-end API tests over the mock agent."""

from __future__ import annotations

TRANSCRIPT = (
    "[00:00:12] Anita Rao: Let's walk through how purchase requests work today.\n"
    "[00:00:30] Sam Fisher: The requester emails the manager and then waits for a reply.\n"
    "[00:01:02] Anita Rao: Finance re-keys everything into a spreadsheet, which is slow.\n"
    "[00:01:20] Sam Fisher: We need one place where the approval status is visible.\n"
)

CHAT = (
    "12/03/2026, 09:15 - Priya Nair: approvals are taking 2 days and I keep chasing on email\n"
    "12/03/2026, 09:18 - Ravi Menon: we need a dashboard that shows the status\n"
)


def _upload(client, project_id, filename, text):
    return client.post(
        f"/api/projects/{project_id}/sources",
        files={"file": (filename, text.encode(), "text/plain")},
    )


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "pdf" in body["extractors"]


def test_project_creation_requires_a_name(client):
    assert client.post("/api/projects", json={"name": "   "}).status_code == 422


def test_full_flow(client, project):
    project_id = project["project_id"]

    assert _upload(client, project_id, "meeting-1.txt", TRANSCRIPT).status_code == 201
    assert _upload(client, project_id, "whatsapp.txt", CHAT).status_code == 201

    sources = client.get(f"/api/projects/{project_id}/sources").json()
    assert [s["source_id"] for s in sources] == ["src-001", "src-002"]
    assert sources[0]["type"] == "meeting_transcript"
    assert sources[1]["type"] == "whatsapp_export"

    canonical = client.get(f"/api/projects/{project_id}/canonical-input").json()
    assert canonical["project_id"] == project_id
    assert len(canonical["sources"]) == 2

    analysis = client.post(f"/api/projects/{project_id}/analyze")
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["mocked"] is True
    assert body["discovery"]["business_need"]["summary"]
    assert body["poc_blueprint"]["stages"]

    stored = client.get(f"/api/projects/{project_id}/discovery").json()
    assert stored["analysis_id"] == body["analysis_id"]


def test_analyze_without_sources_is_a_422(client, project):
    response = client.post(f"/api/projects/{project['project_id']}/analyze")
    assert response.status_code == 422
    assert "at least one source" in response.json()["detail"]


def test_discovery_before_analysis_is_a_404(client, project):
    assert client.get(f"/api/projects/{project['project_id']}/discovery").status_code == 404


def test_unknown_project_is_a_404(client):
    assert client.get("/api/projects/does-not-exist/sources").status_code == 404


def test_unsupported_upload_is_a_400(client, project):
    response = client.post(
        f"/api/projects/{project['project_id']}/sources",
        files={"file": ("archive.zip", b"PK\x03\x04", "application/zip")},
    )
    assert response.status_code == 400


def test_empty_upload_is_a_400(client, project):
    response = client.post(
        f"/api/projects/{project['project_id']}/sources",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400


def test_reset_clears_sources_and_analysis(client, project):
    project_id = project["project_id"]
    _upload(client, project_id, "meeting-1.txt", TRANSCRIPT)
    client.post(f"/api/projects/{project_id}/analyze")

    reset = client.post(f"/api/projects/{project_id}/reset").json()
    assert reset["source_count"] == 0
    assert reset["has_analysis"] is False
    assert client.get(f"/api/projects/{project_id}/discovery").status_code == 404


def test_source_delete(client, project):
    project_id = project["project_id"]
    _upload(client, project_id, "meeting-1.txt", TRANSCRIPT)
    assert client.delete(f"/api/projects/{project_id}/sources/src-001").status_code == 204
    assert client.get(f"/api/projects/{project_id}/sources").json() == []
