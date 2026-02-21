"""Parse JSONL.GZ files into SQLite persons, jobs, education, changes tables."""

import gzip
import json
import logging
import re
import sqlite3
from glob import glob
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Level normalization
# ---------------------------------------------------------------------------

_LEVEL_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(c-suite|chief|ceo|cto|cfo|coo)\b", re.I), "C-Suite"),
    (re.compile(r"\b(evp|svp|vice\s*president|vp)\b", re.I), "VP"),
    (re.compile(r"\b(senior\s+director|director)\b", re.I), "Director"),
    (re.compile(r"\b(senior\s+manager|manager)\b", re.I), "Manager"),
    (re.compile(r"\b(principal|staff|lead)\b", re.I), "Staff"),
    (re.compile(r"\b(senior|sr)\b", re.I), "Senior"),
    (re.compile(r"\b(junior|associate|entry|ic)\b", re.I), "IC"),
]


def normalize_level(raw: str | None) -> str:
    """Map a raw level/title string to a canonical level."""
    if not raw:
        return "Unknown"
    for pattern, level in _LEVEL_RULES:
        if pattern.search(raw):
            return level
    return "Unknown"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def months_between(start_str: str | None, end_str: str | None) -> int | None:
    """Return the number of months between two ISO date strings, or None."""
    if not start_str or not end_str:
        return None
    try:
        sy, sm = int(start_str[:4]), int(start_str[5:7])
        ey, em = int(end_str[:4]), int(end_str[5:7])
        return max(0, (ey - sy) * 12 + (em - sm))
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS persons (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    employment_status TEXT,
    connections INTEGER,
    location_country TEXT,
    location_city TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT,
    title TEXT,
    function TEXT,
    level TEXT,
    company_name TEXT,
    company_industry TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_months INTEGER,
    company_tenure_months INTEGER
);

CREATE TABLE IF NOT EXISTS education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT,
    school TEXT,
    degree TEXT,
    field TEXT,
    started_at TEXT,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT,
    title_change_detected_at TEXT,
    company_change_detected_at TEXT,
    info_change_detected_at TEXT
);
"""


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all four tables if they don't exist."""
    conn.executescript(_CREATE_TABLES_SQL)


# ---------------------------------------------------------------------------
# Record loading
# ---------------------------------------------------------------------------

def load_record(record: dict, conn: sqlite3.Connection) -> None:
    """Insert one person record (with jobs, education, changes) into the DB."""
    pid = record["id"]

    # Location: support both nested location_details dict and flat location dict
    loc = record.get("location_details") or record.get("location") or {}
    if isinstance(loc, dict):
        country = loc.get("country") or record.get("country")
        city = loc.get("locality") or loc.get("city")
    else:
        country = record.get("country")
        city = None

    conn.execute(
        "INSERT OR IGNORE INTO persons (id, created_at, employment_status, connections, location_country, location_city) VALUES (?,?,?,?,?,?)",
        (
            pid,
            record.get("created_at"),
            record.get("employment_status"),
            record.get("connections"),
            country,
            city,
        ),
    )

    for job in record.get("jobs", []):
        started = job.get("started_at")
        ended = job.get("ended_at")

        # Company info: support nested dict or flat fields
        company = job.get("company") or {}
        if isinstance(company, dict) and company:
            company_name = company.get("name")
            company_industry = company.get("industry")
        else:
            company_name = job.get("company_name") or (company if isinstance(company, str) else None)
            company_industry = job.get("company_industry") or job.get("industry")

        # Duration/tenure: use pre-computed integers if present, else compute
        duration = job.get("duration") or months_between(started, ended)
        tenure = job.get("company_tenure") or months_between(started, ended)

        conn.execute(
            "INSERT INTO jobs (person_id, title, function, level, company_name, company_industry, started_at, ended_at, duration_months, company_tenure_months) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                pid,
                job.get("title"),
                job.get("function"),
                normalize_level(job.get("level") or job.get("seniority") or ""),
                company_name,
                company_industry,
                started,
                ended,
                duration,
                tenure,
            ),
        )

    for edu in record.get("education", []):
        conn.execute(
            "INSERT INTO education (person_id, school, degree, field, started_at, ended_at) VALUES (?,?,?,?,?,?)",
            (
                pid,
                edu.get("school"),
                edu.get("degree"),
                edu.get("field") or edu.get("major"),
                edu.get("started_at"),
                edu.get("ended_at"),
            ),
        )

    # Changes: support both top-level fields and nested "changes" dict
    chg = record.get("changes") or {}
    title_change = chg.get("title_change_detected_at") if isinstance(chg, dict) else None
    title_change = title_change or record.get("title_change_detected_at")
    company_change = chg.get("company_change_detected_at") if isinstance(chg, dict) else None
    company_change = company_change or record.get("company_change_detected_at")
    info_change = chg.get("info_change_detected_at") if isinstance(chg, dict) else None
    info_change = info_change or record.get("info_change_detected_at")

    conn.execute(
        "INSERT INTO changes (person_id, title_change_detected_at, company_change_detected_at, info_change_detected_at) VALUES (?,?,?,?)",
        (
            pid,
            title_change,
            company_change,
            info_change,
        ),
    )


# ---------------------------------------------------------------------------
# File / directory ingestion
# ---------------------------------------------------------------------------

def ingest_file(filepath, conn: sqlite3.Connection) -> tuple[int, int]:
    """Ingest a single JSONL.GZ file. Returns (loaded, skipped)."""
    filepath = Path(filepath)
    loaded = 0
    skipped = 0

    with gzip.open(filepath, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                load_record(record, conn)
                loaded += 1
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Skipping malformed line in %s: %s", filepath, exc)
                skipped += 1
                continue

    conn.commit()
    logger.info(f"{Path(filepath).name}: loaded={loaded} skipped={skipped}")
    return loaded, skipped


def run(data_dir: str, db_path: str) -> int:
    """Ingest all matching JSONL.GZ files from data_dir into db_path. Returns total loaded."""
    conn = sqlite3.connect(db_path)
    create_tables(conn)

    pattern = str(Path(data_dir) / "live_data_persons_history_*.jsonl.gz")
    files = sorted(glob(pattern))
    if not files:
        raise FileNotFoundError(f"No JSONL.GZ files in {data_dir}")

    total = 0
    for fp in files:
        loaded, _ = ingest_file(fp, conn)
        total += loaded

    conn.close()
    return total


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    data_dir = os.environ.get("DATA_DIR", "data")
    db_path = os.environ.get("DB_PATH", "skillshock.db")

    logging.basicConfig(level=logging.INFO)
    total = run(data_dir, db_path)
    logger.info("Ingested %d records total.", total)
