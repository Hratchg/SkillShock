import sqlite3
import tempfile
from pathlib import Path
import pytest
import ingest
import analytics

FIXTURE = Path(__file__).parent / "sample.jsonl.gz"

@pytest.fixture
def populated_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    ingest.create_tables(conn)
    ingest.ingest_file(FIXTURE, conn)
    conn.close()
    return db_path

def test_promotion_velocity_returns_dict(populated_db):
    result = analytics.promotion_velocity(populated_db)
    assert isinstance(result, dict)

def test_promotion_velocity_keys_have_required_fields(populated_db):
    result = analytics.promotion_velocity(populated_db)
    for key, val in result.items():
        assert "median_months" in val, f"{key} missing median_months"
        assert "sample_size" in val, f"{key} missing sample_size"
        assert "low_confidence" in val, f"{key} missing low_confidence"

def test_role_transitions_returns_dict(populated_db):
    result = analytics.role_transitions(populated_db)
    assert isinstance(result, dict)

def test_role_transitions_probabilities_sum_to_one(populated_db):
    result = analytics.role_transitions(populated_db)
    for from_role, to_roles in result.items():
        total = sum(v for v in to_roles.values() if isinstance(v, float))
        assert abs(total - 1.0) < 0.01, f"{from_role} probs sum to {total}"

def test_major_to_first_role_returns_dict(populated_db):
    result = analytics.major_to_first_role(populated_db)
    assert isinstance(result, dict)
    assert len(result) > 0

def test_major_to_first_role_top_10_max(populated_db):
    result = analytics.major_to_first_role(populated_db)
    for major, roles in result.items():
        assert len(roles) <= 10, f"{major} has more than 10 roles"

def test_industry_transitions_returns_dict(populated_db):
    result = analytics.industry_transitions(populated_db)
    assert isinstance(result, dict)

def test_paths_to_role_returns_dict(populated_db):
    result = analytics.paths_to_role(populated_db)
    assert isinstance(result, dict)

def test_paths_to_role_entries_have_path_and_frequency(populated_db):
    result = analytics.paths_to_role(populated_db)
    for role, paths in result.items():
        for entry in paths:
            assert "path" in entry
            assert "frequency" in entry
            assert isinstance(entry["path"], list)

def test_compute_all_returns_all_five_keys(populated_db):
    result = analytics.compute_all(populated_db)
    assert set(result.keys()) == {
        "promotion_velocity",
        "role_transitions",
        "major_to_first_role",
        "industry_transitions",
        "paths_to_role",
    }
