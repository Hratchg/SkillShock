# SkillShock — Design Document

**Date:** 2026-02-21
**Track:** Education & Learning
**Goal:** Real-time career outcome intelligence platform using Live Data Technologies People Data and RapidFire AI.

---

## Problem

Students make education and career decisions using unreliable signals (rankings, job boards, anecdotes). SkillShock reconstructs real career trajectories from People Data and turns them into understandable career guidance hosted on a RapidFire AI dashboard.

---

## Architecture Overview

SkillShock is a one-time data pipeline with four independently-ownable modules:

```
/mnt/data/*.jsonl.gz
        │
        ▼
   ingest.py          ← parse JSONL.GZ → load into SQLite
        │
        ▼
  analytics.py        ← compute 5 aggregated metrics from SQLite
        │
        ▼
   export.py          ← shape analytics into RapidFire AI JSON schema
        │
        ▼
    push.py           ← POST JSON payload to RapidFire AI upload endpoint
        │
        ▼
  main.py             ← orchestrator: runs all 4 steps in sequence
```

Intermediate artifacts:
- `skillshock.db` — SQLite database (local only)
- `output.json` — final payload (saved locally for inspection and fallback)

---

## Data Model

### `persons`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| created_at | TEXT | |
| employment_status | TEXT | |
| connections | INTEGER | |
| location_country | TEXT | |
| location_city | TEXT | |

### `jobs`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| person_id | TEXT | |
| title | TEXT | |
| function | TEXT | |
| level | TEXT | Normalized: IC → Senior → Staff → Director → VP → C-Suite |
| company_name | TEXT | |
| company_industry | TEXT | |
| started_at | TEXT | |
| ended_at | TEXT | |
| duration_months | INTEGER | Computed on ingest |
| company_tenure_months | INTEGER | Computed on ingest |

### `education`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| person_id | TEXT | |
| school | TEXT | |
| degree | TEXT | |
| field | TEXT | Major, e.g. "Computer Science" |
| started_at | TEXT | |
| ended_at | TEXT | |

### `changes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| person_id | TEXT | |
| title_change_detected_at | TEXT | |
| company_change_detected_at | TEXT | |
| info_change_detected_at | TEXT | |

**Design decisions:**
- `duration_months` computed on ingest so analytics queries avoid date parsing
- `level` normalized to consistent vocabulary during ingest
- All 3 JSONL.GZ partitions load into the same SQLite DB

---

## Analytics (5 Metrics)

All metrics are aggregated statistics only — no individual person data surfaces in output.

### 1. Promotion Velocity
Median months between job level changes per starting level.

### 2. Role Transition Matrix
For each `title`, probability distribution of next `title`.

### 3. Major → First Role Distribution
For each education `field`, top 10 first job titles with frequency.

### 4. Industry Transition Probability
For each `company_industry`, probability distribution of next industry.

### 5. Most Common Paths to Target Role
Top 5 ordered job sequences ending at a given target title, with frequency counts.

---

## Export Schema (`output.json`)

```json
{
  "metadata": {
    "generated_at": "2026-02-21T00:00:00Z",
    "total_persons": 150000,
    "total_jobs": 480000,
    "data_files": ["...00.jsonl.gz", "...01.jsonl.gz", "...02.jsonl.gz"]
  },
  "promotion_velocity": {
    "IC_to_Senior": { "median_months": 24, "sample_size": 12400 },
    "Senior_to_Staff": { "median_months": 30, "sample_size": 8200 }
  },
  "role_transitions": {
    "Software Engineer": {
      "Senior Software Engineer": 0.62,
      "Product Manager": 0.08
    }
  },
  "major_to_first_role": {
    "Computer Science": {
      "Software Engineer": 0.41,
      "Data Analyst": 0.12
    }
  },
  "industry_transitions": {
    "Technology": { "Finance": 0.11, "Consulting": 0.09 }
  },
  "paths_to_role": {
    "VP Engineering": [
      { "path": ["SWE", "Senior SWE", "Staff", "Director", "VP Eng"], "frequency": 342 }
    ]
  }
}
```

---

## Project Structure

```
skillshock/
├── main.py              ← orchestrator
├── ingest.py            ← parse JSONL.GZ → SQLite
├── analytics.py         ← compute 5 metrics
├── export.py            ← shape results into JSON schema
├── push.py              ← POST to RapidFire AI
├── requirements.txt     ← pandas, requests
├── .env.example         ← environment variable template
├── README.md
└── docs/
    └── plans/
        └── 2026-02-21-skillshock-design.md
```

### Environment Variables (`.env`)
```
DATA_DIR=/mnt/data
DB_PATH=./skillshock.db
OUTPUT_PATH=./output.json
RAPIDFIRE_API_KEY=
RAPIDFIRE_UPLOAD_URL=
```

### Contributor Ownership
| File | Owner | Independent? |
|---|---|---|
| `ingest.py` | Data Engineer | Yes — reads data files, writes DB |
| `analytics.py` | ML/Analytics | Yes — reads DB, returns dicts |
| `export.py` | AI Integration | Yes — shapes dicts into JSON |
| `push.py` | Backend | Yes — reads JSON, calls API |
| `main.py` | Architect | Wires all 4 together |

---

## Error Handling

- `ingest.py` — skips malformed JSONL lines with logged warning
- `analytics.py` — metrics with < 10 samples get `"low_confidence": true` flag
- `push.py` — if API key missing or push fails, saves `output.json` locally and exits cleanly
- `main.py` — prints which step failed and exits with non-zero code

---

## Testing

```
tests/
├── sample.jsonl.gz       ← 500-row fixture (no full dataset needed)
├── test_ingest.py        ← assert tables populated, row counts correct
├── test_analytics.py     ← assert all 5 metrics return expected keys
└── test_export.py        ← assert output.json matches required schema
```

Run: `python -m pytest tests/`

`push.py` is verified manually during demo — no automated test for live API calls.
