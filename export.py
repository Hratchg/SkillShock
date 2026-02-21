"""Shape analytics dicts + metadata into the output.json schema."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def build_payload(metrics: dict, db_path: str, data_files: list[str]) -> dict:
    """Build the full output payload with metadata and all 5 metric keys.

    Args:
        metrics: dict returned by analytics.compute_all()
        db_path: path to the SQLite database
        data_files: list of source data file paths

    Returns:
        dict ready for JSON serialization
    """
    conn = sqlite3.connect(db_path)
    total_persons = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_persons": total_persons,
        "total_jobs": total_jobs,
        "data_files": [Path(f).name for f in data_files],
    }

    payload = {"metadata": metadata}
    payload.update(metrics)
    return payload


def save(payload: dict, output_path: str) -> None:
    """Write payload dict to a JSON file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run(metrics: dict, db_path: str, data_files: list[str], output_path: str) -> dict:
    """Build payload and save to file. Returns the payload."""
    payload = build_payload(metrics, db_path, data_files)
    save(payload, output_path)
    return payload


if __name__ == "__main__":
    import os

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    import analytics

    db_path = os.environ.get("DB_PATH", "skillshock.db")
    output_path = os.environ.get("OUTPUT_PATH", "output.json")
    data_dir = os.environ.get("DATA_DIR", "data")

    from glob import glob
    data_files = sorted(glob(str(Path(data_dir) / "*.jsonl.gz")))

    metrics = analytics.compute_all(db_path)
    payload = run(metrics, db_path, data_files, output_path)
    print(f"Wrote {output_path} ({len(json.dumps(payload))} bytes)")
