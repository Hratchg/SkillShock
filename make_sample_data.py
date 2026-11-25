"""Generate a synthetic sample dataset so the pipeline and dashboard run without the private data.

The real Live Data Technologies files are shared privately and are not in this repo.
This writes N synthetic career histories in the same JSONL.GZ shape to data/.

    python3 make_sample_data.py            # 3,000 people
    python3 make_sample_data.py 10000      # custom size
"""
import gzip
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
import make_fixture  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
random.seed(7)
out = Path(__file__).resolve().parent / "data" / "live_data_persons_history_sample.jsonl.gz"
out.parent.mkdir(exist_ok=True)
with gzip.open(out, "wt", encoding="utf-8") as f:
    for i in range(n):
        f.write(json.dumps(make_fixture.make_person(i)) + "\n")
print(f"Wrote {n} synthetic records to {out}")
