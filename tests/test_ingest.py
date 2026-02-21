import sqlite3
from pathlib import Path
import pytest
import ingest

FIXTURE = Path(__file__).parent / "sample.jsonl.gz"

@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    ingest.create_tables(conn)
    yield conn
    conn.close()

def test_create_tables_makes_all_four(db):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"persons", "jobs", "education", "changes"}.issubset(tables)

def test_ingest_file_loads_records(db):
    loaded, skipped = ingest.ingest_file(FIXTURE, db)
    assert loaded == 20
    assert skipped == 0

def test_persons_table_populated(db):
    ingest.ingest_file(FIXTURE, db)
    count = db.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    assert count == 20

def test_jobs_table_populated(db):
    ingest.ingest_file(FIXTURE, db)
    count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count > 20  # each person has multiple jobs

def test_education_table_populated(db):
    ingest.ingest_file(FIXTURE, db)
    count = db.execute("SELECT COUNT(*) FROM education").fetchone()[0]
    assert count == 20

def test_duration_months_computed(db):
    ingest.ingest_file(FIXTURE, db)
    nulls = db.execute("SELECT COUNT(*) FROM jobs WHERE started_at IS NOT NULL AND ended_at IS NOT NULL AND duration_months IS NULL").fetchone()[0]
    assert nulls == 0

def test_level_normalized(db):
    ingest.ingest_file(FIXTURE, db)
    valid_levels = {"IC", "Senior", "Staff", "Manager", "Director", "VP", "C-Suite", "Unknown"}
    levels = {r[0] for r in db.execute("SELECT DISTINCT level FROM jobs").fetchall()}
    assert levels.issubset(valid_levels)

def test_run_accepts_data_dir(tmp_path):
    import shutil
    shutil.copy(FIXTURE, tmp_path / "live_data_persons_history_2026-02-19_00.jsonl.gz")
    db_path = str(tmp_path / "test.db")
    total = ingest.run(str(tmp_path), db_path)
    assert total == 20

def test_malformed_lines_skipped(db, tmp_path):
    import gzip
    bad_file = tmp_path / "live_data_persons_history_bad.jsonl.gz"
    with gzip.open(bad_file, "wt") as f:
        f.write('{"id": "ok", "jobs": [], "education": [], "changes": {}}\n')
        f.write('NOT JSON\n')
        f.write('{"id": "ok2", "jobs": [], "education": [], "changes": {}}\n')
    loaded, skipped = ingest.ingest_file(bad_file, db)
    assert loaded == 2
    assert skipped == 1
