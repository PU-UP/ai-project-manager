"""项目文档索引：登记、元数据更新、关联与归档。"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from app.datetime_util import now_beijing
from app.schemas import (
    DocumentAdd,
    DocumentArchive,
    DocumentLink,
    DocumentUpdateMetadata,
    row_to_document_dict,
)

LINK_TAG_PREFIX = "link:"


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(t) for t in parsed if isinstance(t, str) and t.strip()]


def _serialize_tags(tags: list[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def assess_source_uri(source_uri: str) -> str:
    """根据 source_uri 可访问性返回建议 status（current | unknown）。"""
    uri = (source_uri or "").strip()
    if not uri:
        return "unknown"
    parsed = urlparse(uri)
    if parsed.scheme in ("http", "https"):
        return "current"
    path = Path(uri)
    if path.exists():
        return "current"
    return "unknown"


def list_documents(conn, project_id: int | None = None) -> list[dict]:
    if project_id is None:
        rows = conn.execute(
            """
            SELECT d.*, p.name AS project_name
            FROM project_documents d
            JOIN projects p ON p.id = d.project_id
            ORDER BY d.updated_at DESC, d.id DESC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT d.*, p.name AS project_name
            FROM project_documents d
            JOIN projects p ON p.id = d.project_id
            WHERE d.project_id = ?
            ORDER BY d.updated_at DESC, d.id DESC
            """,
            (project_id,),
        ).fetchall()
    return [row_to_document_dict(r) for r in rows]


def get_document(conn, project_id: int, document_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT d.*, p.name AS project_name
        FROM project_documents d
        JOIN projects p ON p.id = d.project_id
        WHERE d.project_id = ? AND d.id = ?
        """,
        (project_id, document_id),
    ).fetchone()
    return row_to_document_dict(row) if row else None


def add_document(conn, item: DocumentAdd, project: dict, now: str) -> int:
    status = item.status
    if status is None:
        status = assess_source_uri(item.source_uri)
    conn.execute(
        """
        INSERT INTO project_documents (
            project_id, title, document_type, source_uri, source_kind,
            summary, tags, version_or_date, status, added_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project["id"],
            item.title.strip(),
            item.document_type or "",
            item.source_uri or "",
            item.source_kind or "",
            item.summary or "",
            _serialize_tags(item.tags or []),
            item.version_or_date or "",
            status,
            now,
            now,
        ),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def update_document_metadata(
    conn,
    item: DocumentUpdateMetadata,
    project: dict,
    now: str,
) -> str:
    doc = get_document(conn, project["id"], item.document_id)
    if not doc:
        raise ValueError(f"文档不存在: id={item.document_id}")

    sets: list[str] = []
    values: list = []
    field_map = (
        ("title", item.title),
        ("document_type", item.document_type),
        ("source_uri", item.source_uri),
        ("source_kind", item.source_kind),
        ("summary", item.summary),
        ("version_or_date", item.version_or_date),
        ("status", item.status),
    )
    for field, val in field_map:
        if val is None:
            continue
        if field == "title" and not str(val).strip():
            raise ValueError("title 不能为空")
        sets.append(f"{field} = ?")
        values.append(val.strip() if field == "title" else val)

    if item.tags is not None:
        sets.append("tags = ?")
        values.append(_serialize_tags(item.tags))

    if item.source_uri is not None and item.status is None:
        assessed = assess_source_uri(item.source_uri)
        if assessed == "unknown" and doc.get("status") == "current":
            sets.append("status = ?")
            values.append("unknown")

    if not sets:
        return doc["title"]

    sets.append("updated_at = ?")
    values.append(now)
    values.append(item.document_id)
    conn.execute(
        f"UPDATE project_documents SET {', '.join(sets)} WHERE id = ?",
        values,
    )
    return doc["title"]


def link_document(conn, item: DocumentLink, project: dict, now: str) -> str:
    doc = get_document(conn, project["id"], item.document_id)
    if not doc:
        raise ValueError(f"文档不存在: id={item.document_id}")

    tags = list(doc.get("tags") or [])
    if item.link_ref:
        link_tag = f"{LINK_TAG_PREFIX}{item.link_ref.strip()}"
        if link_tag not in tags:
            tags.append(link_tag)

    source_uri = item.source_uri if item.source_uri is not None else doc.get("source_uri", "")
    status = doc.get("status", "current")
    if item.source_uri is not None:
        assessed = assess_source_uri(source_uri)
        if assessed == "unknown":
            status = "unknown"

    conn.execute(
        """
        UPDATE project_documents
        SET tags = ?, source_uri = ?, status = ?, updated_at = ?
        WHERE id = ?
        """,
        (_serialize_tags(tags), source_uri, status, now, item.document_id),
    )
    return doc["title"]


def archive_document(conn, item: DocumentArchive, project: dict, now: str) -> str:
    doc = get_document(conn, project["id"], item.document_id)
    if not doc:
        raise ValueError(f"文档不存在: id={item.document_id}")
    conn.execute(
        """
        UPDATE project_documents
        SET status = ?, updated_at = ?
        WHERE id = ?
        """,
        ("superseded", now, item.document_id),
    )
    return doc["title"]


def apply_document_operations(
    conn,
    document_adds: list[DocumentAdd],
    document_metadata_updates: list[DocumentUpdateMetadata],
    document_links: list[DocumentLink],
    document_archives: list[DocumentArchive],
    projects: list[dict],
    renamed_lookup: dict[str, str],
) -> dict:
    from app.services.project_updater import match_project

    added: list[str] = []
    metadata_updated: list[str] = []
    linked: list[str] = []
    archived_docs: list[str] = []
    skipped: list[str] = []
    invalid: list[dict] = []
    now = now_beijing()

    for item in document_adds:
        lookup_name = renamed_lookup.get(
            _normalize(item.project_name), item.project_name
        )
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            doc_id = add_document(conn, item, project, now)
            added.append(f"{project['name']}:{doc_id}:{item.title}")
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    for item in document_metadata_updates:
        lookup_name = renamed_lookup.get(
            _normalize(item.project_name), item.project_name
        )
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            title = update_document_metadata(conn, item, project, now)
            metadata_updated.append(f"{project['name']}:{item.document_id}:{title}")
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    for item in document_links:
        lookup_name = renamed_lookup.get(
            _normalize(item.project_name), item.project_name
        )
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            title = link_document(conn, item, project, now)
            linked.append(f"{project['name']}:{item.document_id}:{title}")
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    for item in document_archives:
        lookup_name = renamed_lookup.get(
            _normalize(item.project_name), item.project_name
        )
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            title = archive_document(conn, item, project, now)
            archived_docs.append(f"{project['name']}:{item.document_id}:{title}")
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    return {
        "documents_added": added,
        "documents_metadata_updated": metadata_updated,
        "documents_linked": linked,
        "documents_archived": archived_docs,
        "skipped": skipped,
        "invalid": invalid,
    }


def _normalize(name: str) -> str:
    return name.strip().lower()
