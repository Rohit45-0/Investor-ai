from __future__ import annotations

from typing import Any

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings

DDL_STATEMENTS = [
    "create extension if not exists pgcrypto;",
    """
    create table if not exists chat_runs (
        run_label text primary key,
        manifest jsonb not null default '{}'::jsonb,
        overview jsonb not null default '{}'::jsonb,
        workflow jsonb not null default '{}'::jsonb,
        indexed_documents integer not null default 0,
        indexed_chunks integer not null default 0,
        indexed_at timestamptz not null default now()
    );
    """,
    """
    create table if not exists chat_documents (
        id uuid primary key default gen_random_uuid(),
        external_id text not null unique,
        run_label text not null references chat_runs(run_label) on delete cascade,
        doc_type text not null,
        symbol text,
        company text,
        title text not null,
        content text not null,
        search_text text not null,
        metadata jsonb not null default '{}'::jsonb,
        source_url text,
        attachment_url text,
        score integer,
        event_date text,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    );
    """,
    "create index if not exists idx_chat_documents_run_symbol on chat_documents(run_label, symbol);",
    "create index if not exists idx_chat_documents_doc_type on chat_documents(doc_type);",
    "create index if not exists idx_chat_documents_metadata on chat_documents using gin(metadata);",
    "create index if not exists idx_chat_documents_search on chat_documents using gin(to_tsvector('english', search_text));",
    """
    create table if not exists chat_chunks (
        id uuid primary key default gen_random_uuid(),
        document_id uuid not null references chat_documents(id) on delete cascade,
        external_id text not null unique,
        run_label text not null references chat_runs(run_label) on delete cascade,
        doc_type text not null,
        symbol text,
        company text,
        chunk_index integer not null,
        content text not null,
        token_estimate integer not null default 0,
        metadata jsonb not null default '{}'::jsonb,
        source_url text,
        attachment_url text,
        lexical_text text not null,
        embedding jsonb,
        embedding_model text,
        created_at timestamptz not null default now()
    );
    """,
    "create index if not exists idx_chat_chunks_run_symbol on chat_chunks(run_label, symbol);",
    "create index if not exists idx_chat_chunks_doc_type on chat_chunks(doc_type);",
    "create index if not exists idx_chat_chunks_metadata on chat_chunks using gin(metadata);",
    "create index if not exists idx_chat_chunks_search on chat_chunks using gin(to_tsvector('english', lexical_text));",
    """
    create table if not exists chat_sessions (
        id uuid primary key default gen_random_uuid(),
        run_label text,
        symbol text,
        metadata jsonb not null default '{}'::jsonb,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    );
    """,
    """
    create table if not exists chat_messages (
        id uuid primary key default gen_random_uuid(),
        session_id uuid not null references chat_sessions(id) on delete cascade,
        role text not null,
        content text not null,
        citations jsonb not null default '[]'::jsonb,
        metadata jsonb not null default '{}'::jsonb,
        created_at timestamptz not null default now()
    );
    """,
    "create index if not exists idx_chat_messages_session_time on chat_messages(session_id, created_at);",
]


def require_database_url() -> str:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    return settings.database_url


def get_connection():
    return connect(require_database_url(), row_factory=dict_row)


def ensure_chat_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for statement in DDL_STATEMENTS:
                cur.execute(statement)
        conn.commit()


def replace_run_index(
    *,
    run_label: str,
    manifest: dict[str, Any],
    overview: dict[str, Any],
    workflow: dict[str, Any],
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> None:
    ensure_chat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into chat_runs (
                    run_label, manifest, overview, workflow, indexed_documents, indexed_chunks, indexed_at
                )
                values (%s, %s, %s, %s, %s, %s, now())
                on conflict (run_label) do update set
                    manifest = excluded.manifest,
                    overview = excluded.overview,
                    workflow = excluded.workflow,
                    indexed_documents = excluded.indexed_documents,
                    indexed_chunks = excluded.indexed_chunks,
                    indexed_at = now()
                """,
                (
                    run_label,
                    Jsonb(manifest),
                    Jsonb(overview),
                    Jsonb(workflow),
                    len(documents),
                    len(chunks),
                ),
            )
            cur.execute("delete from chat_documents where run_label = %s", (run_label,))

            document_ids: dict[str, str] = {}
            for document in documents:
                cur.execute(
                    """
                    insert into chat_documents (
                        external_id, run_label, doc_type, symbol, company, title, content,
                        search_text, metadata, source_url, attachment_url, score, event_date, updated_at
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    returning id
                    """,
                    (
                        document["external_id"],
                        run_label,
                        document["doc_type"],
                        document.get("symbol"),
                        document.get("company"),
                        document["title"],
                        document["content"],
                        document["search_text"],
                        Jsonb(document.get("metadata") or {}),
                        document.get("source_url"),
                        document.get("attachment_url"),
                        document.get("score"),
                        document.get("event_date"),
                    ),
                )
                row = cur.fetchone()
                document_ids[document["external_id"]] = str(row["id"])

            for chunk in chunks:
                cur.execute(
                    """
                    insert into chat_chunks (
                        document_id, external_id, run_label, doc_type, symbol, company,
                        chunk_index, content, token_estimate, metadata, source_url, attachment_url,
                        lexical_text, embedding, embedding_model
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document_ids[chunk["document_external_id"]],
                        chunk["external_id"],
                        run_label,
                        chunk["doc_type"],
                        chunk.get("symbol"),
                        chunk.get("company"),
                        chunk["chunk_index"],
                        chunk["content"],
                        chunk.get("token_estimate", 0),
                        Jsonb(chunk.get("metadata") or {}),
                        chunk.get("source_url"),
                        chunk.get("attachment_url"),
                        chunk["lexical_text"],
                        Jsonb(chunk.get("embedding")) if chunk.get("embedding") is not None else None,
                        chunk.get("embedding_model"),
                    ),
                )
        conn.commit()


def fetch_candidate_chunks(
    *,
    query: str,
    run_label: str,
    symbol: str | None = None,
    watchlist: list[str] | None = None,
    direction: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    ensure_chat_schema()
    watchlist = [item.strip().upper() for item in (watchlist or []) if str(item).strip()]
    where = ["c.run_label = %s"]
    params: list[Any] = [query, run_label]

    if symbol:
        where.append("c.symbol = %s")
        params.append(symbol.strip().upper())
    elif watchlist:
        where.append("c.symbol = any(%s)")
        params.append(watchlist)
    if direction:
        where.append("coalesce(c.metadata->>'direction', '') = %s")
        params.append(direction)

    params.append(limit)
    sql = f"""
        select
            c.external_id,
            c.doc_type,
            c.symbol,
            c.company,
            c.chunk_index,
            c.content,
            c.metadata,
            c.source_url,
            c.attachment_url,
            c.embedding,
            c.embedding_model,
            d.title,
            coalesce(
                ts_rank_cd(
                    to_tsvector('english', c.lexical_text),
                    websearch_to_tsquery('english', %s)
                ),
                0
            ) as lexical_score
        from chat_chunks c
        join chat_documents d on d.id = c.document_id
        where {' and '.join(where)}
        order by lexical_score desc, c.created_at desc
        limit %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_recent_chunks(
    *,
    run_label: str,
    symbol: str | None = None,
    watchlist: list[str] | None = None,
    direction: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    ensure_chat_schema()
    watchlist = [item.strip().upper() for item in (watchlist or []) if str(item).strip()]
    where = ["c.run_label = %s"]
    params: list[Any] = [run_label]

    if symbol:
        where.append("c.symbol = %s")
        params.append(symbol.strip().upper())
    elif watchlist:
        where.append("c.symbol = any(%s)")
        params.append(watchlist)
    if direction:
        where.append("coalesce(c.metadata->>'direction', '') = %s")
        params.append(direction)

    params.append(limit)
    sql = f"""
        select
            c.external_id,
            c.doc_type,
            c.symbol,
            c.company,
            c.chunk_index,
            c.content,
            c.metadata,
            c.source_url,
            c.attachment_url,
            c.embedding,
            c.embedding_model,
            d.title,
            0.0 as lexical_score
        from chat_chunks c
        join chat_documents d on d.id = c.document_id
        where {' and '.join(where)}
        order by c.created_at desc
        limit %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def get_index_status() -> list[dict[str, Any]]:
    ensure_chat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select run_label, indexed_documents, indexed_chunks, indexed_at, manifest, overview
                from chat_runs
                order by indexed_at desc, run_label desc
                """
            )
            return list(cur.fetchall())


def is_run_indexed(run_label: str) -> bool:
    ensure_chat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from chat_runs where run_label = %s limit 1", (run_label,))
            return cur.fetchone() is not None


def create_chat_session(
    *,
    run_label: str | None,
    symbol: str | None,
    metadata: dict[str, Any] | None = None,
) -> str:
    ensure_chat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into chat_sessions (run_label, symbol, metadata)
                values (%s, %s, %s)
                returning id
                """,
                (run_label, symbol, Jsonb(metadata or {})),
            )
            row = cur.fetchone()
        conn.commit()
        return str(row["id"])


def add_chat_message(
    *,
    session_id: str,
    role: str,
    content: str,
    citations: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    ensure_chat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into chat_messages (session_id, role, content, citations, metadata)
                values (%s, %s, %s, %s, %s)
                """,
                (session_id, role, content, Jsonb(citations or []), Jsonb(metadata or {})),
            )
            cur.execute(
                "update chat_sessions set updated_at = now() where id = %s",
                (session_id,),
            )
        conn.commit()


def fetch_recent_messages(session_id: str, *, limit: int = 6) -> list[dict[str, Any]]:
    ensure_chat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select role, content, citations, metadata, created_at
                from (
                    select role, content, citations, metadata, created_at
                    from chat_messages
                    where session_id = %s
                    order by created_at desc
                    limit %s
                ) recent
                order by created_at asc
                """,
                (session_id, limit),
            )
            return list(cur.fetchall())
