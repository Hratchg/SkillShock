import json
import sqlite3
import tempfile
from pathlib import Path
import pytest
import ingest
import analytics
import export

FIXTURE = Path(__file__).parent / "sample.jsonl.gz"

@pytest.fixture
def metrics_and_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    ingest.create_tables(conn)
    ingest.ingest_file(FIXTURE, conn)
    conn.close()
    metrics = analytics.compute_all(db_path)
    return metrics, db_path

def test_build_payload_has_required_top_level_keys(metrics_and_db):
    metrics, db_path = metrics_and_db
    payload = export.build_payload(metrics, db_path, data_files=["file00.jsonl.gz"])
    required = {"metadata", "promotion_velocity", "role_transitions",
                "major_to_first_role", "industry_transitions", "paths_to_role"}
    assert required.issubset(set(payload.keys()))

def test_metadata_has_required_fields(metrics_and_db):
    metrics, db_path = metrics_and_db
    payload = export.build_payload(metrics, db_path, data_files=["file00.jsonl.gz"])
    meta = payload["metadata"]
    assert "generated_at" in meta
    assert "total_persons" in meta
    assert "total_jobs" in meta
    assert "data_files" in meta
    assert isinstance(meta["data_files"], list)

def test_metadata_counts_match_db(metrics_and_db):
    metrics, db_path = metrics_and_db
    payload = export.build_payload(metrics, db_path, data_files=[])
    assert payload["metadata"]["total_persons"] == 20

def test_payload_is_json_serializable(metrics_and_db):
    metrics, db_path = metrics_and_db
    payload = export.build_payload(metrics, db_path, data_files=[])
    serialized = json.dumps(payload)
    assert len(serialized) > 100

def test_save_writes_file(metrics_and_db, tmp_path):
    metrics, db_path = metrics_and_db
    out = tmp_path / "output.json"
    payload = export.build_payload(metrics, db_path, data_files=[])
    export.save(payload, str(out))
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert "metadata" in loaded
