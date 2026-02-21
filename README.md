# SkillShock

Career outcome intelligence platform. Reconstructs real career trajectories from Live Data Technologies People Data and turns them into interactive visualizations.

**Track:** Education & Learning

## What It Does

Students make education and career decisions using unreliable signals. SkillShock analyzes 75,000+ real career trajectories to answer:

- How long does it take to get promoted from IC to Senior? Senior to Director?
- What jobs do Computer Science majors actually get?
- What industries do people switch to from Tech? Finance?
- What career paths lead to VP of Engineering?

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATA_DIR to your JSONL.GZ folder
```

## Run Pipeline

```bash
python main.py
```

This ingests the data, computes analytics, and produces `output.json`.

## Launch Dashboard

```bash
python dashboard.py
```

Opens at http://localhost:7860 with interactive charts:

- **Promotion Velocity** — median months between career levels
- **Role Transitions** — what title comes next?
- **Major to First Role** — what jobs do graduates actually get?
- **Industry Transitions** — where do people switch industries to?
- **Career Paths** — most common paths to any target role

## Test

```bash
pytest tests/ -v
```

## Architecture

```
JSONL.GZ data → ingest.py → SQLite → analytics.py → export.py → output.json → dashboard.py
```

| File | Role |
|---|---|
| `ingest.py` | Parse JSONL.GZ → SQLite |
| `analytics.py` | Compute 5 career metrics |
| `export.py` | Shape metrics into output.json |
| `push.py` | POST to RapidFire AI (optional) |
| `main.py` | Orchestrate the pipeline |
| `dashboard.py` | Interactive Gradio dashboard |

## Data

Uses Live Data Technologies People Data (75,139 people, 717,053 jobs).

## Tech Stack

Python, SQLite, pandas, Gradio, Plotly, RapidFire AI
