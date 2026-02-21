# SkillShock

Career outcome intelligence pipeline. Parses People Data into analytics and pushes to RapidFire AI dashboard.

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATA_DIR and RAPIDFIRE_API_KEY
```

## Run

```bash
python main.py
```

## Test

```bash
pytest tests/ -v
```

## Modules

| File | Role |
|---|---|
| `ingest.py` | Parse JSONL.GZ → SQLite |
| `analytics.py` | Compute 5 metrics from SQLite |
| `export.py` | Shape metrics into output.json |
| `push.py` | POST output.json to RapidFire AI |
| `main.py` | Orchestrate all 4 steps |
