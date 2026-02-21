"""main.py — Run the full SkillShock pipeline."""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import analytics
import export
import ingest
import push


def main():
    data_dir    = os.getenv("DATA_DIR",    "/mnt/data")
    db_path     = os.getenv("DB_PATH",     "./skillshock.db")
    output_path = os.getenv("OUTPUT_PATH", "./output.json")
    api_key     = os.getenv("RAPIDFIRE_API_KEY", "")
    upload_url  = os.getenv("RAPIDFIRE_UPLOAD_URL", "")

    data_files = sorted(
        list(Path(data_dir).glob("live_data_persons_history_*.jsonl.gz"))
        + list(Path(data_dir).glob("live_data_persons_history_*.jsonl"))
    )

    # Step 1: Ingest
    logger.info("=== Step 1/4: Ingest ===")
    try:
        total = ingest.run(data_dir, db_path)
        logger.info(f"Ingested {total} records.")
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        sys.exit(1)

    # Step 2: Analytics
    logger.info("=== Step 2/4: Analytics ===")
    try:
        metrics = analytics.compute_all(db_path)
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        sys.exit(1)

    # Step 3: Export
    logger.info("=== Step 3/4: Export ===")
    try:
        export.run(metrics, db_path, data_files=[str(f) for f in data_files], output_path=output_path)
        logger.info(f"Output written to {output_path}")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)

    # Step 4: Push
    logger.info("=== Step 4/4: Push ===")
    try:
        pushed = push.run(output_path, api_key, upload_url)
        if pushed:
            logger.info("Pipeline complete — dashboard live on RapidFire AI.")
        else:
            logger.info(f"Pipeline complete — output saved locally to {output_path}.")
    except Exception as e:
        logger.error(f"Push failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
