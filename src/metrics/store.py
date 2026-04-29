import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipeline_trace import TraceResult

DB_PATH = Path(__file__).resolve().parents[2] / "metrics.db"

_DDL = """
CREATE TABLE IF NOT EXISTS query_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL    NOT NULL,
    question        TEXT    NOT NULL,
    answer          TEXT    NOT NULL,
    retrieve_s     REAL    NOT NULL,
    rerank_s       REAL    NOT NULL,
    llm_s          REAL    NOT NULL,
    total_s        REAL    NOT NULL,
    candidate_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rerank_scores (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL REFERENCES query_log(id) ON DELETE CASCADE,
    rank     INTEGER NOT NULL,
    score    REAL    NOT NULL,
    source   TEXT    NOT NULL,
    preview  TEXT    NOT NULL
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_DDL)


def record_query(result: "TraceResult", db_path: Path = DB_PATH) -> int:
    ts = time.time()
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO query_log
                (ts, question, answer, retrieve_s, rerank_s, llm_s, total_s, candidate_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                result.question,
                result.answer,
                result.timings.retrieve_s,
                result.timings.rerank_s,
                result.timings.llm_s,
                result.timings.total_s,
                result.candidate_count,
            ),
        )
        query_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO rerank_scores (query_id, rank, score, source, preview) VALUES (?,?,?,?,?)",
            [
                (query_id, row.rank, row.score, row.source, row.preview)
                for row in result.rerank_rows
            ],
        )
    return query_id


def fetch_latency_series(limit: int = 200, db_path: Path = DB_PATH) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, retrieve_s, rerank_s, llm_s, total_s FROM query_log ORDER BY ts ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_recent_queries(limit: int = 50, db_path: Path = DB_PATH) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, ts, question, retrieve_s, rerank_s, llm_s, total_s, candidate_count
            FROM query_log ORDER BY ts DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_rerank_score_distribution(db_path: Path = DB_PATH) -> list[float]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT score FROM rerank_scores").fetchall()
    return [r[0] for r in rows]


def fetch_stage_breakdown_aggregates(db_path: Path = DB_PATH) -> dict:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT AVG(retrieve_s), AVG(rerank_s), AVG(llm_s) FROM query_log"
        ).fetchone()
    return {
        "avg_retrieve_s": row[0] or 0.0,
        "avg_rerank_s": row[1] or 0.0,
        "avg_llm_s": row[2] or 0.0,
    }
