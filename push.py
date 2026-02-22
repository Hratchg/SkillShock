"""push.py — Upload output.json to RapidFire AI."""
import json
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def run(output_path, api_key, upload_url):
    if not api_key:
        logger.warning("RAPIDFIRE_API_KEY not set — skipping push. Output saved locally.")
        return False

    if not upload_url:
        logger.warning("RAPIDFIRE_UPLOAD_URL not set — skipping push.")
        return False

    payload = json.loads(Path(output_path).read_text(encoding="utf-8"))

    logger.info(f"Pushing to RapidFire AI: {upload_url}")
    response = requests.post(
        upload_url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    response.raise_for_status()
    logger.info(f"Push successful — status {response.status_code}")
    return True


from dotenv import load_dotenv
if __name__ == "__main__":
    load_dotenv()
    run(
        output_path=os.getenv("OUTPUT_PATH", "./output.json"),
        api_key=os.getenv("RAPIDFIRE_API_KEY", ""),
        upload_url=os.getenv("RAPIDFIRE_UPLOAD_URL", ""),
    )
