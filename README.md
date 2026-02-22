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

### 1. Create and activate a virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install numpy==2.2.0
pip install -r requirements.txt
```

> **Note:** The RAG dependencies (`faiss-cpu`, `langchain`, `sentence-transformers`) are ~2GB and only needed if you want AI-powered semantic retrieval. The dashboard works fine without them — set `USE_RAG=false` in your `.env` to skip RAG entirely.

### 3. Set up environment variables
```bash
cp .env.example .env
```
Open `.env` and add your API keys:

| Variable | Required? | Description |
|---|---|---|
| `GOOGLE_API_KEY` | **Yes** (for AI Career Planner) | Google Gemini API key. Get one at [AI Studio](https://aistudio.google.com/app/apikey) |
| `USE_RAG` | No | Set to `true` to enable RAG-powered context retrieval (requires heavy deps). Default: `false` |
| `RAPIDFIRE_API_KEY` | No | RapidFire AI API key for publishing to RapidFire |
| `RAPIDFIRE_UPLOAD_URL` | No | RapidFire upload endpoint URL |
| `DATA_DIR` | No | Path to data files. Default: `./data` |
| `DB_PATH` | No | SQLite database path. Default: `./skillshock.db` |
| `OUTPUT_PATH` | No | Pipeline output path. Default: `./output.json` |

> The dashboard's data visualizations work without any API keys. The `GOOGLE_API_KEY` is only needed for the AI Career Planner feature.

### 4. Add the data files
Download the Live Data Technologies `.jsonl.gz` files from the team Google Drive (link in Discord) and place them in the `data/` folder:
```
SkillShock/
└── data/
    ├── live_data_persons_history_2026-02-19_00.jsonl.gz
    ├── live_data_persons_history_2026-02-19_01.jsonl.gz
    └── live_data_persons_history_2026-02-19_02.jsonl.gz
```

### 5. Run the pipeline
Run these in order — each must finish before the next:

**macOS / Linux:**
```bash
DATA_DIR=data python3 ingest.py
python3 analytics.py
python3 export.py
```

**Windows:**
```bash
set DATA_DIR=data
python ingest.py
python analytics.py
python export.py
```

You should see:
- `ingest.py` → `Ingested 75139 records total`
- `analytics.py` → processes and analyzes the data
- `export.py` → `Wrote ./output.json`

### 6. Launch the dashboard
```bash
python dashboard.py
```

Opens at http://localhost:7860 with interactive charts:

- **Promotion Velocity** — median months between career levels
- **Role Transitions** — what title comes next?
- **Major to First Role** — what jobs do graduates actually get?
- **Industry Transitions** — where do people switch industries to?
- **Career Paths** — most common paths to any target role
- **AI Career Planner** — personalized career roadmap powered by Gemini + real data

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
| `main.py` | Orchestrate the full pipeline |
| `dashboard.py` | FastAPI backend + interactive UI |
| `rag_config.py` | RAG pipeline setup (FAISS + LangChain) |
| `ui.html` | Frontend (HTML/CSS/JS + Plotly CDN) |

## Data

Uses Live Data Technologies People Data (75,139 people, 717,053 jobs).
Files are shared privately with the team — do not commit to GitHub.

## Tech Stack

Python, SQLite, pandas, FastAPI, Plotly, Google Gemini, RapidFire AI
