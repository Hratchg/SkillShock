"""Compute 5 aggregated career trajectory metrics from SQLite."""

import json
import sqlite3
from collections import Counter

import pandas as pd

LEVEL_ORDER = ["IC", "Senior", "Staff", "Manager", "Director", "VP", "C-Suite"]


def _load_jobs(db_path: str) -> pd.DataFrame:
    """Load jobs table into a pandas DataFrame, sorted by person_id and started_at."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT person_id, title, level, company_name, company_industry, started_at, ended_at FROM jobs ORDER BY person_id, started_at",
        conn,
    )
    conn.close()
    return df


def promotion_velocity(db_path: str) -> dict:
    """Compute median months between level transitions, grouped by (from_level, to_level).

    Returns dict keyed by "from_level -> to_level" with median_months, sample_size, low_confidence.
    """
    df = _load_jobs(db_path)

    # Only keep jobs with known levels in LEVEL_ORDER
    df = df[df["level"].isin(LEVEL_ORDER)].copy()
    df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce")
    df = df.dropna(subset=["started_at"])
    df = df.sort_values(["person_id", "started_at"])

    # For each person, find consecutive jobs where level changes
    transitions = []
    for person_id, group in df.groupby("person_id"):
        rows = group.reset_index(drop=True)
        for i in range(len(rows) - 1):
            from_level = rows.loc[i, "level"]
            to_level = rows.loc[i + 1, "level"]
            if from_level != to_level:
                gap = (rows.loc[i + 1, "started_at"] - rows.loc[i, "started_at"])
                gap_months = gap.days / 30.44  # approximate months
                transitions.append({
                    "from_level": from_level,
                    "to_level": to_level,
                    "gap_months": gap_months,
                })

    if not transitions:
        return {}

    tdf = pd.DataFrame(transitions)
    result = {}
    for (fl, tl), grp in tdf.groupby(["from_level", "to_level"]):
        key = f"{fl} -> {tl}"
        median = round(grp["gap_months"].median(), 1)
        size = len(grp)
        result[key] = {
            "median_months": median,
            "sample_size": size,
            "low_confidence": size < 10,
        }

    return result


def role_transitions(db_path: str) -> dict:
    """Compute transition probabilities between job titles.

    Returns dict keyed by from_title, values are dicts of to_title -> probability.
    """
    df = _load_jobs(db_path)
    df = df.dropna(subset=["title"])
    df = df.sort_values(["person_id", "started_at"])

    transitions = []
    for person_id, group in df.groupby("person_id"):
        rows = group.reset_index(drop=True)
        for i in range(len(rows) - 1):
            transitions.append({
                "from_title": rows.loc[i, "title"],
                "to_title": rows.loc[i + 1, "title"],
            })

    if not transitions:
        return {}

    tdf = pd.DataFrame(transitions)
    result = {}
    for from_title, grp in tdf.groupby("from_title"):
        counts = grp["to_title"].value_counts()
        total = counts.sum()
        result[from_title] = {title: round(count / total, 4) for title, count in counts.items()}

    return result


def major_to_first_role(db_path: str) -> dict:
    """Map education field to first job title.

    Returns dict keyed by field, values are dicts of title -> proportion (top 10).
    """
    conn = sqlite3.connect(db_path)

    # Get each person's earliest job
    first_jobs = pd.read_sql_query(
        """
        SELECT j.person_id, j.title
        FROM jobs j
        INNER JOIN (
            SELECT person_id, MIN(started_at) AS min_start
            FROM jobs
            WHERE started_at IS NOT NULL AND title IS NOT NULL
            GROUP BY person_id
        ) earliest ON j.person_id = earliest.person_id AND j.started_at = earliest.min_start
        WHERE j.title IS NOT NULL
        """,
        conn,
    )

    # Get education fields
    edu = pd.read_sql_query(
        "SELECT person_id, field FROM education WHERE field IS NOT NULL",
        conn,
    )
    conn.close()

    if first_jobs.empty or edu.empty:
        return {}

    merged = edu.merge(first_jobs, on="person_id")

    result = {}
    for field, grp in merged.groupby("field"):
        counts = grp["title"].value_counts().head(10)
        total = counts.sum()
        result[field] = {title: round(count / total, 4) for title, count in counts.items()}

    return result


def industry_transitions(db_path: str) -> dict:
    """Compute transition probabilities between industries (only where industry changed).

    Returns dict keyed by from_industry, values are dicts of to_industry -> probability.
    """
    df = _load_jobs(db_path)
    df = df.dropna(subset=["company_industry"])
    df = df.sort_values(["person_id", "started_at"])

    transitions = []
    for person_id, group in df.groupby("person_id"):
        rows = group.reset_index(drop=True)
        for i in range(len(rows) - 1):
            from_ind = rows.loc[i, "company_industry"]
            to_ind = rows.loc[i + 1, "company_industry"]
            if from_ind != to_ind:
                transitions.append({
                    "from_industry": from_ind,
                    "to_industry": to_ind,
                })

    if not transitions:
        return {}

    tdf = pd.DataFrame(transitions)
    result = {}
    for from_ind, grp in tdf.groupby("from_industry"):
        counts = grp["to_industry"].value_counts()
        total = counts.sum()
        result[from_ind] = {ind: round(count / total, 4) for ind, count in counts.items()}

    return result


def paths_to_role(db_path: str) -> dict:
    """For each final job title, find the most common career paths leading to it.

    Returns dict keyed by final title, values are lists of {"path": [...], "frequency": int}.
    """
    df = _load_jobs(db_path)
    df = df.dropna(subset=["title"])
    df = df.sort_values(["person_id", "started_at"])

    paths_by_final: dict[str, Counter] = {}
    for person_id, group in df.groupby("person_id"):
        titles = group["title"].tolist()
        if not titles:
            continue
        final = titles[-1]
        path_key = tuple(titles)
        if final not in paths_by_final:
            paths_by_final[final] = Counter()
        paths_by_final[final][path_key] += 1

    result = {}
    for final_title, counter in paths_by_final.items():
        top5 = counter.most_common(5)
        result[final_title] = [
            {"path": list(path), "frequency": freq}
            for path, freq in top5
        ]

    return result


def compute_all(db_path: str) -> dict:
    """Compute all 5 career trajectory metrics."""
    return {
        "promotion_velocity": promotion_velocity(db_path),
        "role_transitions": role_transitions(db_path),
        "major_to_first_role": major_to_first_role(db_path),
        "industry_transitions": industry_transitions(db_path),
        "paths_to_role": paths_to_role(db_path),
    }


if __name__ == "__main__":
    import os

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    db_path = os.environ.get("DB_PATH", "skillshock.db")
    result = compute_all(db_path)
    print(json.dumps(result, indent=2, default=str))
