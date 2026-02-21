"""Generate a 20-record JSONL.GZ fixture for testing analytics scenarios."""

import gzip
import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

MAJORS = ["Computer Science", "Business", "Mechanical Engineering", "Biology", "Finance"]
INDUSTRIES = ["Technology", "Finance", "Healthcare", "Consulting", "Education"]
SCHOOLS = [
    "MIT", "Stanford University", "UC Berkeley",
    "University of Michigan", "Georgia Tech",
]
CITIES = [
    ("US", "San Francisco"),
    ("US", "New York"),
    ("US", "Austin"),
    ("UK", "London"),
    ("DE", "Berlin"),
]
DEGREE_TYPES = ["BS", "BA", "MS", "MBA"]

# Career ladder definitions keyed by function
LADDERS = {
    "Engineering": [
        ("Software Engineer", "IC"),
        ("Senior Software Engineer", "Senior"),
        ("Staff Engineer", "Staff"),
        ("Engineering Director", "Director"),
        ("VP of Engineering", "VP"),
    ],
    "Finance": [
        ("Financial Analyst", "IC"),
        ("Senior Financial Analyst", "Senior"),
        ("Finance Manager", "Manager"),
        ("Director of Finance", "Director"),
        ("VP of Finance", "VP"),
    ],
    "Marketing": [
        ("Marketing Associate", "IC"),
        ("Senior Marketing Manager", "Senior"),
        ("Marketing Director", "Director"),
        ("VP of Marketing", "VP"),
    ],
    "Product": [
        ("Product Analyst", "IC"),
        ("Product Manager", "Senior"),
        ("Senior Product Manager", "Staff"),
        ("Director of Product", "Director"),
        ("VP of Product", "VP"),
    ],
    "Operations": [
        ("Operations Analyst", "IC"),
        ("Operations Manager", "Manager"),
        ("Senior Operations Manager", "Senior"),
        ("Director of Operations", "Director"),
    ],
}

COMPANY_NAMES = [
    "Acme Corp", "Globex Inc", "Initech", "Umbrella Ltd",
    "Stark Industries", "Wayne Enterprises", "Pied Piper",
    "Hooli", "Dunder Mifflin", "Cyberdyne",
]

EMPLOYMENT_STATUSES = ["employed", "unemployed"]


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def _months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def make_person(idx: int) -> dict:
    person_id = f"person_{idx:03d}"

    # Education
    major = MAJORS[idx % len(MAJORS)]
    school = random.choice(SCHOOLS)
    degree = random.choice(DEGREE_TYPES)
    edu_start = date(random.randint(2008, 2014), 9, 1)
    edu_end = edu_start.replace(year=edu_start.year + (2 if degree in ("MS", "MBA") else 4),
                                month=5, day=1)

    education = [{
        "school": school,
        "degree": degree,
        "field": major,
        "started_at": edu_start.isoformat(),
        "ended_at": edu_end.isoformat(),
    }]

    # Pick a primary function/ladder
    func_name = random.choice(list(LADDERS.keys()))
    ladder = LADDERS[func_name]

    num_jobs = random.randint(2, 4)
    # Start career shortly after graduation
    job_start = edu_end + timedelta(days=random.randint(30, 180))

    jobs = []
    # Decide if this person switches industries mid-career
    switch_industry = idx % 3 == 0  # roughly 1/3 of people switch
    base_industry = random.choice(INDUSTRIES)

    for j in range(num_jobs):
        rung = min(j, len(ladder) - 1)
        title, level = ladder[rung]
        company = random.choice(COMPANY_NAMES)

        if switch_industry and j >= num_jobs // 2:
            industry = random.choice([i for i in INDUSTRIES if i != base_industry])
        else:
            industry = base_industry

        duration_months = random.randint(12, 42)
        end_dt = job_start + timedelta(days=duration_months * 30)

        # Last job may still be current
        is_current = (j == num_jobs - 1) and random.random() < 0.6
        ended_at = None if is_current else end_dt.isoformat()
        dur = None if is_current else duration_months

        jobs.append({
            "title": title,
            "function": func_name,
            "level": level,
            "company_name": company,
            "company_industry": industry,
            "started_at": job_start.isoformat(),
            "ended_at": ended_at,
            "duration": dur,
            "company_tenure": dur,
        })

        job_start = end_dt + timedelta(days=random.randint(14, 90))

    # Employment status
    last_job = jobs[-1]
    emp_status = "employed" if last_job["ended_at"] is None else random.choice(EMPLOYMENT_STATUSES)

    # Connections
    connections = random.randint(50, 2000)

    # Location
    country, city = random.choice(CITIES)

    # Changes
    created_at = _random_date(date(2023, 1, 1), date(2024, 6, 1))
    title_change = created_at - timedelta(days=random.randint(0, 365)) if random.random() < 0.5 else None
    company_change = created_at - timedelta(days=random.randint(0, 365)) if random.random() < 0.3 else None
    info_change = created_at - timedelta(days=random.randint(0, 180)) if random.random() < 0.6 else None

    return {
        "id": person_id,
        "created_at": created_at.isoformat(),
        "employment_status": emp_status,
        "connections": connections,
        "location": {"country": country, "city": city},
        "jobs": jobs,
        "education": education,
        "changes": {
            "title_change_detected_at": title_change.isoformat() if title_change else None,
            "company_change_detected_at": company_change.isoformat() if company_change else None,
            "info_change_detected_at": info_change.isoformat() if info_change else None,
        },
    }


def main():
    out_path = Path(__file__).resolve().parent / "sample.jsonl.gz"
    records = [make_person(i) for i in range(20)]

    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
