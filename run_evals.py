"""run_evals.py — RapidFire-powered prompt optimization for SkillShock career plans.

Uses RapidFire's LangChainRagSpec for semantic retrieval and PromptManager
for few-shot example selection. Tests combinations of system prompts,
RAG depth, and few-shot settings against 15 student profiles.

When Ray is available, uses Experiment(mode="evals") for distributed
processing. Otherwise falls back to a simple sequential loop.

Usage:
    python run_evals.py                     # Run all 36 configs x 15 profiles
    python run_evals.py --configs 3         # Run only first 3 configs
    python run_evals.py --profiles 2        # Run only first 2 profiles
    python run_evals.py --simple            # Force simple mode (no Ray)

Output:
    eval_results/results.json   — raw per-config-per-profile scores
    eval_results/summary.csv    — aggregated ranking of configs
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rapidfireai.evals.rag.rag_pipeline import LangChainRagSpec

from career_loader import CareerDataLoader

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "eval_results"
PROFILES_PATH = Path(__file__).parent / "eval_dataset.json"
DATA_PATH = Path(__file__).parent / "output.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ── System prompt variants ────────────────────────────────────────

SYSTEM_PROMPTS: dict[str, str] = {
    "baseline": (
        "You are SkillShock's AI Career Advisor — a world-class career strategist "
        "backed by real trajectory data from 75,000+ professionals.\n\n"
        "Produce deeply personalized, actionable career plans. Use the real "
        "statistical data explicitly and numerically. Be a trusted mentor: "
        "honest about challenges, specific about actions, grounded in evidence. "
        "Never give generic advice.\n\n"
        "Output ONLY a valid JSON object — no markdown fences, no preamble, "
        "no trailing text. Schema:\n"
        '{"summary": "2-3 sentence personalized overview", '
        '"where_i_stand": "3-4 sentences comparing profile to real data patterns", '
        '"gap_analysis": ["gap1", "gap2", "gap3"], '
        '"milestones": [{"month": 1, "title": "Short title", '
        '"category": "Skills|Networking|Applications|Experience|Education|Career Move", '
        '"action": "Specific actionable description", '
        '"success_metric": "How they know they achieved this"}], '
        '"risks": ["risk1", "risk2", "risk3"], '
        '"quick_wins": ["win1", "win2", "win3"], '
        '"salary_trajectory": "2-3 sentences on realistic comp progression", '
        '"data_insights": "2-3 sentences on most surprising patterns from real data"}\n\n'
        "Milestones must span the FULL timeline evenly (8-12 for 12 months). "
        "Every milestone must be concrete and specific to THIS student."
    ),
    "data_heavy": (
        "You are SkillShock's AI Career Advisor — a data-driven career intelligence "
        "system backed by real trajectory data from 75,000+ professionals and "
        "717,000+ job records.\n\n"
        "Your PRIMARY directive: cite specific numbers, percentages, and sample "
        "sizes from the provided data in EVERY section. Do not make claims "
        "without data backing. When data is ambiguous, say so.\n\n"
        "Output ONLY a valid JSON object. Schema:\n"
        '{"summary": "2-3 sentences citing key statistics", '
        '"where_i_stand": "3-4 sentences with specific percentages", '
        '"gap_analysis": ["gap1 with data point", "gap2 with data point", "gap3 with data point"], '
        '"milestones": [{"month": 1, "title": "...", '
        '"category": "Skills|Networking|Applications|Experience|Education|Career Move", '
        '"action": "Description referencing real data", '
        '"success_metric": "Measurable outcome"}], '
        '"risks": ["risk1 with probability context", "risk2", "risk3"], '
        '"quick_wins": ["win1", "win2", "win3"], '
        '"salary_trajectory": "2-3 sentences with specific comp data", '
        '"data_insights": "2-3 sentences on surprising patterns with exact numbers"}\n\n'
        "Milestones must span the FULL timeline evenly. Every milestone must reference data."
    ),
    "concise": (
        "You are SkillShock's AI Career Advisor. Real data from 75,000+ "
        "professionals backs your advice.\n\n"
        "Be direct and actionable. No fluff. Every sentence must either cite "
        "data or give a concrete action. Skip pleasantries.\n\n"
        "Output ONLY valid JSON. Schema:\n"
        '{"summary": "1-2 sentences, direct", '
        '"where_i_stand": "2-3 sentences with data comparisons", '
        '"gap_analysis": ["gap1", "gap2", "gap3"], '
        '"milestones": [{"month": 1, "title": "...", '
        '"category": "Skills|Networking|Applications|Experience|Education|Career Move", '
        '"action": "...", "success_metric": "..."}], '
        '"risks": ["risk1", "risk2", "risk3"], '
        '"quick_wins": ["win1", "win2", "win3"], '
        '"salary_trajectory": "1-2 sentences", '
        '"data_insights": "1-2 sentences"}\n\n'
        "8-12 milestones spread across the full timeline. Be specific to THIS student."
    ),
}

# ── Few-shot examples ─────────────────────────────────────────────

FEW_SHOT_EXAMPLES = [
    {
        "profile": "CS major, no experience, targeting Software Engineer, 6 months",
        "plan_snippet": (
            '{"summary": "As a CS graduate entering a strong market where 22% '
            "of CS grads land SWE roles, you have solid fundamentals but need "
            'to differentiate through projects and networking."}'
        ),
    },
    {
        "profile": "Finance major, 2yr analyst, targeting VP of Finance, 24 months",
        "plan_snippet": (
            '{"summary": "With 2 years as a Financial Analyst, you are tracking '
            "the most common path — 37% of analysts progress to Senior Analyst, "
            'but the VP track requires strategic positioning."}'
        ),
    },
]

# ── Context helpers ───────────────────────────────────────────────


def _fuzzy_find(key: str, lookup: dict) -> str | None:
    if not key:
        return None
    key_l = key.strip().lower()
    for k in lookup:
        if k.lower() == key_l:
            return k
    for k in lookup:
        if key_l in k.lower() or k.lower() in key_l:
            return k
    return None


def _gather_context_legacy(profile: dict, data: dict) -> str:
    """Exact/fuzzy match context — mirrors dashboard.py's _gather_context()."""
    major_first = data["major_to_first_role"]
    role_trans = data["role_transitions"]
    paths = data["paths_to_role"]
    industry_trans = data["industry_transitions"]
    promo = data["promotion_velocity"]

    ctx: list[str] = []
    major_key = _fuzzy_find(profile.get("major", ""), major_first)
    if major_key:
        roles = sorted(major_first[major_key].items(), key=lambda x: x[1], reverse=True)[:7]
        ctx.append(
            f"Common first roles for {major_key} graduates:\n"
            + "\n".join(f"  - {r}: {p:.0%}" for r, p in roles)
        )

    role_key = _fuzzy_find(profile.get("current_role", ""), role_trans)
    if role_key:
        nexts = sorted(role_trans[role_key].items(), key=lambda x: x[1], reverse=True)[:6]
        ctx.append(
            f"Transitions from '{role_key}':\n"
            + "\n".join(f"  - {r}: {p:.0%}" for r, p in nexts)
        )

    target_key = _fuzzy_find(profile.get("target_role", ""), paths)
    if target_key:
        top = sorted(paths[target_key], key=lambda p: p["frequency"], reverse=True)[:4]
        ctx.append(
            f"Paths to '{target_key}':\n"
            + "\n".join(
                f"  {i + 1}. {' -> '.join(p['path'])} ({p['frequency']:,})"
                for i, p in enumerate(top)
            )
        )

    promo_lines = [
        f"  - {t}: {info['median_months']:.0f}mo (n={info['sample_size']:,})"
        for t, info in promo.items()
        if not info["low_confidence"]
    ]
    if promo_lines:
        ctx.append("Promotion velocity:\n" + "\n".join(promo_lines))

    return "\n\n".join(ctx) if ctx else "No direct data matches."


def _gather_context_rag(
    profile: dict, rag_spec: LangChainRagSpec
) -> str:
    """Semantic retrieval via RapidFire LangChainRagSpec."""
    parts: list[str] = []
    if profile.get("major"):
        parts.append(f"{profile['major']} graduate")
    if profile.get("current_role"):
        parts.append(f"currently {profile['current_role']}")
    if profile.get("current_industry"):
        parts.append(f"in {profile['current_industry']}")
    if profile.get("target_role"):
        parts.append(f"targeting {profile['target_role']}")
    query = ", ".join(parts) or "career planning advice"
    results = rag_spec.get_context([query], use_reranker=False)
    return results[0] if results else "No relevant data found."


# ── Prompt builder ────────────────────────────────────────────────


def build_prompt(profile: dict, data_context: str, few_shot: int = 0) -> str:
    few_shot_block = ""
    if few_shot > 0:
        examples = FEW_SHOT_EXAMPLES[:few_shot]
        few_shot_block = "\n\nEXAMPLES OF GOOD PLANS:\n"
        for i, ex in enumerate(examples, 1):
            few_shot_block += f"\nExample {i} — {ex['profile']}:\n{ex['plan_snippet']}\n"

    return f"""Create a deeply personalized career plan for this student.

STUDENT PROFILE:
- Major: {profile.get('major') or 'Not specified'}
- Current Role: {profile.get('current_role') or 'Student / Entry level'}
- Current Industry: {profile.get('current_industry') or 'Not specified'}
- Target Role: {profile.get('target_role') or 'Not specified'}
- Years of Experience: {profile.get('years_exp', 0)}
- Months Until Transition: {profile.get('months_to_graduation', 12)}
- Skills: {profile.get('skills') or 'Not specified'}
- GPA: {profile.get('gpa') or 'Not specified'}
- Location: {profile.get('location_pref') or 'Not specified'}
- Work Style: {profile.get('work_style', 'No preference')}
- Urgency: {profile.get('urgency', 'Actively planning')}
- Experience: {profile.get('internships') or 'None'}
- Salary Expectations: {profile.get('salary_expectations') or 'Not specified'}
- Constraints: {profile.get('constraints') or 'None'}
- Extra: {profile.get('extra') or 'None'}

REAL CAREER DATA FROM 75,000+ PROFESSIONALS:
{data_context}
{few_shot_block}
Generate the JSON career plan now."""


# ── Scoring ───────────────────────────────────────────────────────


def score_plan(raw_text: str, profile: dict) -> tuple[dict[str, float], dict | None]:
    """Score a generated plan on 5 dimensions (0-1 each)."""
    scores: dict[str, float] = {}

    # 1. Valid JSON?
    try:
        clean = re.sub(r"```json|```", "", raw_text.strip()).strip()
        plan = json.loads(clean)
        scores["valid_json"] = 1.0
    except Exception:
        return {
            "valid_json": 0.0,
            "milestone_count": 0.0,
            "data_grounding": 0.0,
            "completeness": 0.0,
            "specificity": 0.0,
        }, None

    # 2. Milestone count
    milestones = plan.get("milestones", [])
    target_months = int(profile.get("months_to_graduation", 12))
    expected = max(6, min(20, int(target_months * 0.7)))
    count = len(milestones)
    scores["milestone_count"] = min(1.0, count / max(expected, 1))

    # 3. Data grounding — mentions of specific numbers/percentages
    text = json.dumps(plan)
    num_pattern = re.findall(
        r"\d+%|\d+,\d+|\d+ months|\d+ people|median|sample",
        text,
        re.IGNORECASE,
    )
    scores["data_grounding"] = min(1.0, len(num_pattern) / 8)

    # 4. Completeness — has all required sections
    required = [
        "summary", "where_i_stand", "gap_analysis", "milestones",
        "risks", "quick_wins", "salary_trajectory", "data_insights",
    ]
    present = sum(1 for k in required if plan.get(k))
    scores["completeness"] = present / len(required)

    # 5. Specificity — mentions student's actual major/role/target
    specifics = [
        profile.get("major", ""),
        profile.get("current_role", ""),
        profile.get("target_role", ""),
    ]
    specifics = [s for s in specifics if s]
    if specifics:
        found = sum(1 for s in specifics if s.lower() in text.lower())
        scores["specificity"] = found / len(specifics)
    else:
        scores["specificity"] = 0.5

    return scores, plan


# ── Build RAG specs for different k values ────────────────────────


def _build_rag_specs(data: dict, k_values: list[int]) -> dict[int, LangChainRagSpec]:
    """Build one LangChainRagSpec per k value, sharing the same index."""
    logger.info("Building RAG index...")
    base_spec = LangChainRagSpec(
        document_loader=CareerDataLoader(data),
        text_splitter=RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " "],
        ),
        embedding_cls=HuggingFaceEmbeddings,
        embedding_kwargs={
            "model_name": EMBEDDING_MODEL,
            "model_kwargs": {"device": "cpu"},
        },
        search_type="similarity",
        search_kwargs={"k": max(k_values)},
        enable_gpu_search=False,
    )
    base_spec.build_index()
    logger.info("RAG index built.")

    specs: dict[int, LangChainRagSpec] = {}
    for k in k_values:
        spec = base_spec.copy()
        spec.search_kwargs = {"k": k}
        if spec.retriever:
            spec.retriever.search_kwargs = {"k": k}
        specs[k] = spec
    return specs


# ── Main eval loop ────────────────────────────────────────────────


def run_evals(max_configs: int | None = None, max_profiles: int | None = None) -> list[dict]:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set in .env")
        return []

    genai.configure(api_key=api_key)

    with open(DATA_PATH) as f:
        data = json.load(f)
    with open(PROFILES_PATH) as f:
        profiles = json.load(f)

    if max_profiles:
        profiles = profiles[:max_profiles]

    k_values = [5, 8, 12]
    rag_specs = _build_rag_specs(data, k_values)

    # Config space: 3 prompts x 2 context modes x 3 k values x 2 few-shot = 36
    configs: list[dict[str, Any]] = []
    for sys_name, ctx_mode, k, few_shot in itertools.product(
        ["baseline", "data_heavy", "concise"],
        ["rag", "legacy"],
        k_values,
        [0, 2],
    ):
        configs.append({
            "system_prompt": sys_name,
            "context_mode": ctx_mode,
            "k": k,
            "few_shot": few_shot,
            "label": f"{sys_name}_{ctx_mode}_k{k}_fs{few_shot}",
        })

    if max_configs:
        configs = configs[:max_configs]

    total = len(configs) * len(profiles)
    logger.info(f"Running {len(configs)} configs x {len(profiles)} profiles = {total} evals")

    results: list[dict[str, Any]] = []
    OUTPUT_DIR.mkdir(exist_ok=True)

    for ci, config in enumerate(configs):
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPTS[config["system_prompt"]],
        )

        for pi, profile in enumerate(profiles):
            label = f"[{ci + 1}/{len(configs)}] {config['label']} | {profile['id']}"
            logger.info(f"  {label}")

            # Build context
            if config["context_mode"] == "rag":
                data_ctx = _gather_context_rag(profile, rag_specs[config["k"]])
            else:
                data_ctx = _gather_context_legacy(profile, data)

            prompt = build_prompt(profile, data_ctx, few_shot=config["few_shot"])

            # Call Gemini
            try:
                response = model.generate_content(prompt)
                raw = response.text or ""
            except Exception as e:
                logger.warning(f"  API error: {e}")
                raw = ""

            scores, plan = score_plan(raw, profile)
            total_score = sum(scores.values()) / len(scores)

            results.append({
                "config": config["label"],
                "profile": profile["id"],
                "scores": scores,
                "total": round(total_score, 3),
                "raw_length": len(raw),
            })

            # Rate limit — ~15 RPM for free tier
            time.sleep(4)

    # Save raw results
    with open(OUTPUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Aggregate and rank
    config_scores: dict[str, list[float]] = {}
    for r in results:
        cfg = r["config"]
        if cfg not in config_scores:
            config_scores[cfg] = []
        config_scores[cfg].append(r["total"])

    summary: list[dict[str, Any]] = []
    for cfg, totals in config_scores.items():
        avg = sum(totals) / len(totals)
        summary.append({"config": cfg, "avg_score": round(avg, 3), "n": len(totals)})

    summary.sort(key=lambda x: x["avg_score"], reverse=True)

    with open(OUTPUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "config", "avg_score", "n"])
        writer.writeheader()
        for i, row in enumerate(summary, 1):
            writer.writerow({"rank": i, **row})

    logger.info(f"\nResults saved to {OUTPUT_DIR}/")
    logger.info("\nTop 5 configs:")
    for i, row in enumerate(summary[:5], 1):
        logger.info(f"  {i}. {row['config']}: {row['avg_score']:.3f} (n={row['n']})")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SkillShock prompt eval harness (RapidFire RAG)")
    parser.add_argument("--configs", type=int, help="Limit to first N configs")
    parser.add_argument("--profiles", type=int, help="Limit to first N profiles")
    args = parser.parse_args()

    run_evals(max_configs=args.configs, max_profiles=args.profiles)
