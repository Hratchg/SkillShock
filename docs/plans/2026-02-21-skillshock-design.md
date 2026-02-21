# SkillShock — Design Document (Updated)

**Date:** 2026-02-21
**Track:** Education & Learning
**Status:** COMPLETE — all modules implemented, tested, and demo-ready
**Repo:** https://github.com/Hratchg/SkillShock

---

## Problem

Students make education and career decisions using unreliable signals (rankings, job boards, anecdotes). SkillShock reconstructs real career trajectories from People Data and turns them into interactive career guidance via a Gradio dashboard.

---

## Architecture Overview

```
C:/Users/hratc/Downloads/*.jsonl.gz   (75,139 people, 717,053 jobs)
        │
        ▼
   ingest.py          ← parse JSONL.GZ → load into SQLite
        │
        ▼
  analytics.py        ← compute 5 aggregated metrics from SQLite
        │
        ▼
   export.py          ← shape analytics into output.json (trimmed to top-N)
        │
        ▼
    push.py           ← POST to RapidFire AI (optional, skips if no API key)
        │
        ▼
  main.py             ← orchestrator: runs all 4 steps in sequence
        │
        ▼
  dashboard.py        ← Gradio + Plotly interactive dashboard (localhost:7860)
```

Intermediate artifacts:
- `skillshock.db` — SQLite database (local only, ~200MB with full data)
- `output.json` — analytics payload (~0.6MB after trimming to top-N entries)

---

## Real Data Schema

**Source:** Live Data Technologies People Data JSONL.GZ files

Each record has this structure (discovered during implementation):

```json
{
  "id": "LDP-1-...",
  "created_at": "2023-05-12T05:23:29Z",
  "title_change_detected_at": null,          // TOP-LEVEL, not nested
  "company_change_detected_at": null,        // TOP-LEVEL, not nested
  "info_change_detected_at": "2026-01-14Z",  // TOP-LEVEL, not nested
  "employment_status": "employed",
  "connections": 177,
  "country": "United States",                // TOP-LEVEL country
  "location": "Los Angeles, CA",             // string, not dict
  "location_details": {                      // nested dict for details
    "country": "United States",
    "locality": "Los Angeles",               // "locality" not "city"
    "region": "California"
  },
  "jobs": [
    {
      "title": "Software Engineer",
      "level": "Staff",                      // already normalized by data provider
      "function": "Engineering",
      "started_at": "2020-09-01T00:00:00Z",
      "ended_at": null,
      "company": {                           // NESTED dict, not flat
        "name": "Acme Corp",                 // company.name, not company_name
        "industry": "Technology"             // company.industry, not company_industry
      },
      "duration": 66,                        // pre-computed integer (months)
      "company_tenure": 66                   // pre-computed integer (months)
    }
  ],
  "education": [
    {
      "school": "UCLA",
      "field": "Computer Science",           // "field" key works
      "degree": "Bachelor of Science - BS",
      "started_at": "2014-09-01T00:00:00Z",
      "ended_at": "2018-05-01T00:00:00Z"
    }
  ]
}
```

### Key Schema Notes (for future updates to ingest.py)
- Company info is **nested**: `job["company"]["name"]`, not `job["company_name"]`
- Change timestamps are **top-level** on the record, not under a `"changes"` dict
- Location city uses `location_details["locality"]`, not `location["city"]`
- `duration` and `company_tenure` are **pre-computed integers** in the data
- `ingest.py` handles both real schema and test fixture schema via fallback aliases

---

## Data Model (SQLite)

### `persons`
| Column | Type | Source |
|---|---|---|
| id | TEXT PK | `record["id"]` |
| created_at | TEXT | `record["created_at"]` |
| employment_status | TEXT | `record["employment_status"]` |
| connections | INTEGER | `record["connections"]` |
| location_country | TEXT | `record["location_details"]["country"]` or `record["country"]` |
| location_city | TEXT | `record["location_details"]["locality"]` |

### `jobs`
| Column | Type | Source |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | auto |
| person_id | TEXT | `record["id"]` |
| title | TEXT | `job["title"]` |
| function | TEXT | `job["function"]` |
| level | TEXT | `normalize_level(job["level"])` → IC/Senior/Staff/Manager/Director/VP/C-Suite/Unknown |
| company_name | TEXT | `job["company"]["name"]` |
| company_industry | TEXT | `job["company"]["industry"]` |
| started_at | TEXT | `job["started_at"]` |
| ended_at | TEXT | `job["ended_at"]` |
| duration_months | INTEGER | `job["duration"]` or computed from dates |
| company_tenure_months | INTEGER | `job["company_tenure"]` or computed from dates |

### `education`
| Column | Type | Source |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | auto |
| person_id | TEXT | `record["id"]` |
| school | TEXT | `edu["school"]` |
| degree | TEXT | `edu["degree"]` |
| field | TEXT | `edu["field"]` |
| started_at | TEXT | `edu["started_at"]` |
| ended_at | TEXT | `edu["ended_at"]` |

### `changes`
| Column | Type | Source |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | auto |
| person_id | TEXT | `record["id"]` |
| title_change_detected_at | TEXT | `record["title_change_detected_at"]` (top-level) |
| company_change_detected_at | TEXT | `record["company_change_detected_at"]` (top-level) |
| info_change_detected_at | TEXT | `record["info_change_detected_at"]` (top-level) |

---

## Analytics (5 Metrics)

All metrics are aggregated statistics only — no individual person data surfaces in output.

### 1. Promotion Velocity
Median months between job level changes per from→to level pair.
- Key format: `"IC -> Senior"` (arrow-separated)
- Includes: `median_months` (float), `sample_size` (int), `low_confidence` (bool, true if < 10 samples)
- Real data: 12 transitions found

### 2. Role Transition Matrix
For each `title`, probability distribution of next `title`.
- Probabilities sum to 1.0 per source role
- Real data: 231,703 unique source roles (trimmed to top 200 in output.json)

### 3. Major → First Role Distribution
For each education `field`, top 10 first job titles with frequency.
- Joins education table with earliest job per person
- Real data: 41,610 unique majors (trimmed to top 200 in output.json)

### 4. Industry Transition Probability
For each `company_industry`, probability distribution of next industry (only actual changes).
- Real data: 397 industries (trimmed to top 100 in output.json)

### 5. Most Common Paths to Target Role
Top 5 ordered job sequences ending at each final title, with frequency counts.
- Real data: 37,583 target roles (trimmed to top 200 in output.json)

---

## Output Trimming

The raw output.json was 59MB due to the extreme granularity of job titles (231k unique roles). After the pipeline runs, the data is trimmed:

| Metric | Raw Count | Trimmed To | Top-N kept per entry |
|---|---|---|---|
| Role transitions | 231,703 | 200 | 20 targets per source |
| Major → first role | 41,610 | 200 | all targets |
| Industry transitions | 397 | 100 | 20 targets per source |
| Paths to role | 37,583 | 200 | 5 paths per target |

Final output.json: ~0.6MB

The trimming is done inline after `main.py` runs (see main.py or run the trimming script manually).

---

## Dashboard (Gradio + Plotly)

`dashboard.py` — self-contained interactive dashboard.

**Launch:** `python dashboard.py` → opens at http://localhost:7860

### 6 Tabs:
| Tab | Visualization | Interactivity |
|---|---|---|
| Overview | Stats cards | None (static) |
| Promotion Velocity | Horizontal bar chart | None (static) |
| Role Transitions | Horizontal bar chart | Dropdown: top 50 source roles |
| Major → First Role | Horizontal bar chart | Dropdown: top 50 majors (filtered for quality) |
| Industry Transitions | Horizontal bar chart | Dropdown: top 30 industries |
| Career Paths | HTML table | Dropdown: top 50 target roles |

### Styling
- Dark theme (Catppuccin Mocha palette)
- Colors: blue (#89b4fa), green (#a6e3a1), yellow (#f9e2af), purple (#cba6f7), red (#f38ba8)
- Text annotations on all bar charts

---

## Project Structure (Final)

```
skillshock/
├── main.py              ← orchestrator (runs ingest→analytics→export→push)
├── ingest.py            ← parse JSONL.GZ → SQLite (handles real + fixture schemas)
├── analytics.py         ← compute 5 metrics using pandas
├── export.py            ← shape metrics + metadata into output.json
├── push.py              ← POST to RapidFire AI (optional)
├── dashboard.py         ← Gradio + Plotly interactive dashboard
├── requirements.txt     ← pandas, requests, python-dotenv, pytest, gradio, plotly, rapidfireai
├── .env.example         ← environment variable template
├── .env                 ← local config (gitignored)
├── .gitignore           ← *.db, output.json, .env, __pycache__/
├── README.md
├── skillshock.db        ← SQLite database (gitignored, generated by pipeline)
├── output.json          ← analytics payload (gitignored, generated by pipeline)
├── docs/
│   └── plans/
│       ├── 2026-02-21-skillshock-design.md      ← this file
│       └── 2026-02-21-skillshock-implementation.md
└── tests/
    ├── __init__.py
    ├── make_fixture.py   ← generates 20-record synthetic fixture
    ├── sample.jsonl.gz   ← test fixture (matches real data schema)
    ├── test_ingest.py    ← 9 tests
    ├── test_analytics.py ← 10 tests
    └── test_export.py    ← 5 tests
```

---

## Environment Variables (`.env`)

```
DATA_DIR=C:/Users/hratc/Downloads     # folder containing *.jsonl.gz files
DB_PATH=./skillshock.db                # SQLite database output
OUTPUT_PATH=./output.json              # analytics JSON output
RAPIDFIRE_API_KEY=                     # optional: RapidFire AI API key
RAPIDFIRE_UPLOAD_URL=                  # optional: RapidFire AI upload endpoint
```

---

## How to Run

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Set data directory
cp .env.example .env
# Edit .env: set DATA_DIR to your JSONL.GZ folder

# 3. Run pipeline (ingests data, computes analytics, writes output.json)
python main.py

# 4. Launch dashboard
python dashboard.py
# Opens at http://localhost:7860

# 5. Run tests
pytest tests/ -v
```

---

## Known Issues & Future Improvements

### Performance
- `analytics.py` opens 5 separate DB connections (one per metric). For large datasets, refactor `compute_all()` to load DataFrames once and pass them to each metric function.
- No indexes on `person_id` in jobs/education/changes tables. Adding `CREATE INDEX idx_jobs_person ON jobs(person_id, started_at)` would speed up analytics on large datasets.

### Data Quality
- Job titles are extremely granular (231k unique). Consider title normalization/clustering for cleaner analytics.
- Major/field names contain junk entries (quoted text, numeric values). The dashboard filters these in the dropdown, but the underlying data is unclean.
- Level normalization uses regex keyword matching — some levels may be misclassified.

### Features Not Yet Built
- Search page: user inputs major + target career → filtered combined report
- AI-powered career briefing (was planned for RapidFire AI integration)
- Public sharing via `share=True` in Gradio launch
- Scheduled/repeatable pipeline (currently one-time)

### Testing Gaps
- No test for `ingest.load_record` with missing `id` field
- No edge-case tests (empty DB, single-job persons)
- No test for `push.py` (live API, verified manually)

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Database | SQLite (stdlib) |
| Data Processing | pandas |
| Dashboard | Gradio 6.x + Plotly |
| HTTP | requests |
| Config | python-dotenv |
| Testing | pytest |
| ML Platform | rapidfireai (installed, available for future AI features) |
