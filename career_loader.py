"""
SkillShock CareerDataLoader -- LangChain BaseLoader for output.json

Converts SkillShock analytics (promotion velocity, role transitions,
major-to-first-role, industry transitions, paths-to-role) into
LangChain Document objects suitable for RapidFire's LangChainRagSpec.

Applies the same junk-filtering rules as dashboard.py (lines 39-46)
and caps entry counts to keep the vector index at a reasonable size.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

# ── Junk-detection regexes (matching dashboard.py lines 39-46) ───────
_NUMERIC_JUNK_RE = re.compile(r"^[\d.\-\s/,]+$")


def _is_junk_major(name: str, roles: dict[str, Any]) -> bool:
    """Return True if a major name should be filtered out."""
    if len(name) < 4:
        return True
    if _NUMERIC_JUNK_RE.match(name):
        return True
    if name.startswith('"'):
        return True
    if len(roles) < 3:
        return True
    if re.match(r"^\d", name):
        return True
    return False


def _is_junk_role(name: str) -> bool:
    """Return True if a role name should be filtered out."""
    if len(name) < 3:
        return True
    if _NUMERIC_JUNK_RE.match(name):
        return True
    return False


def _fmt_pct(value: float) -> str:
    """Format a probability float as a rounded whole-number percentage."""
    return f"{value * 100:.0f}%"


def _fmt_count(value: int) -> str:
    """Format an integer with thousands separators."""
    return f"{value:,}"


class CareerDataLoader(BaseLoader):
    """LangChain document loader for SkillShock output.json data.

    Reads the five analytics sections from a parsed output.json dict,
    applies junk filtering and entry caps, and produces one Document
    per logical record (promotion pair, source role, major, industry,
    or target role).

    Args:
        data: Parsed output.json dictionary containing the keys
              ``promotion_velocity``, ``role_transitions``,
              ``major_to_first_role``, ``industry_transitions``,
              and ``paths_to_role``.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    # ── Public API ───────────────────────────────────────────────────

    def load(self) -> list[Document]:
        """Load all sections into a flat list of Documents."""
        docs: list[Document] = []
        docs.extend(self._load_promotions())
        docs.extend(self._load_role_transitions())
        docs.extend(self._load_majors())
        docs.extend(self._load_industry_transitions())
        docs.extend(self._load_paths())
        return docs

    # ── Promotion velocity (all ~12 entries) ─────────────────────────

    def _load_promotions(self) -> list[Document]:
        promo: dict[str, Any] = self.data.get("promotion_velocity", {})
        docs: list[Document] = []
        for transition, info in promo.items():
            median = info["median_months"]
            sample = info["sample_size"]
            text = (
                f"Promotion velocity -- {transition}: "
                f"{median:.0f} months median "
                f"(sample size: {_fmt_count(sample)} professionals)"
            )
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "type": "promotion_velocity",
                        "transition": transition,
                    },
                )
            )
        return docs

    # ── Role transitions (top 800 by destination count) ──────────────

    def _load_role_transitions(self) -> list[Document]:
        role_trans: dict[str, dict[str, float]] = self.data.get(
            "role_transitions", {}
        )

        # Filter junk roles, then sort by number of destinations desc
        clean: dict[str, dict[str, float]] = {
            role: dests
            for role, dests in role_trans.items()
            if not _is_junk_role(role)
        }
        sorted_roles = sorted(
            clean, key=lambda r: len(clean[r]), reverse=True
        )[:800]

        docs: list[Document] = []
        for role in sorted_roles:
            dests = clean[role]
            # Also filter junk destination role names
            filtered_dests = {
                d: p for d, p in dests.items() if not _is_junk_role(d)
            }
            top = sorted(
                filtered_dests.items(), key=lambda x: x[1], reverse=True
            )[:7]
            if not top:
                continue
            dest_parts = ", ".join(
                f"{name} ({_fmt_pct(prob)})" for name, prob in top
            )
            text = f"Career transitions from {role}: {dest_parts}"
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "type": "role_transition",
                        "source_role": role,
                    },
                )
            )
        return docs

    # ── Major to first role (top 750 by role count) ──────────────────

    def _load_majors(self) -> list[Document]:
        major_first: dict[str, dict[str, float]] = self.data.get(
            "major_to_first_role", {}
        )

        clean: dict[str, dict[str, float]] = {
            m: roles
            for m, roles in major_first.items()
            if not _is_junk_major(m, roles)
        }
        sorted_majors = sorted(
            clean, key=lambda m: len(clean[m]), reverse=True
        )[:750]

        docs: list[Document] = []
        for major in sorted_majors:
            roles = clean[major]
            # Filter junk role names in destinations too
            filtered_roles = {
                r: p for r, p in roles.items() if not _is_junk_role(r)
            }
            top = sorted(
                filtered_roles.items(), key=lambda x: x[1], reverse=True
            )[:7]
            if not top:
                continue
            role_parts = ", ".join(
                f"{name} ({_fmt_pct(prob)})" for name, prob in top
            )
            text = f"First jobs for {major} graduates: {role_parts}"
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "type": "major_to_first_role",
                        "major": major,
                    },
                )
            )
        return docs

    # ── Industry transitions (all ~397 entries) ──────────────────────

    def _load_industry_transitions(self) -> list[Document]:
        industry_trans: dict[str, dict[str, float]] = self.data.get(
            "industry_transitions", {}
        )

        docs: list[Document] = []
        for industry, dests in industry_trans.items():
            top = sorted(dests.items(), key=lambda x: x[1], reverse=True)[:5]
            if not top:
                continue
            dest_parts = ", ".join(
                f"{name} ({_fmt_pct(prob)})" for name, prob in top
            )
            text = f"Industry mobility from {industry}: {dest_parts}"
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "type": "industry_transition",
                        "source_industry": industry,
                    },
                )
            )
        return docs

    # ── Paths to role (top 125 targets, top 4 paths each) ────────────

    def _load_paths(self) -> list[Document]:
        paths_to_role: dict[str, list[dict[str, Any]]] = self.data.get(
            "paths_to_role", {}
        )

        # Only include targets with at least 2 paths
        qualified: dict[str, list[dict[str, Any]]] = {}
        for target, paths in paths_to_role.items():
            if len(paths) >= 2:
                qualified[target] = paths

        # Sort by total frequency descending, take top 125
        sorted_targets = sorted(
            qualified,
            key=lambda t: sum(p["frequency"] for p in qualified[t]),
            reverse=True,
        )[:125]

        docs: list[Document] = []
        for target in sorted_targets:
            paths = sorted(
                qualified[target],
                key=lambda p: p["frequency"],
                reverse=True,
            )[:4]
            path_lines = "\n".join(
                f"  {i}. {' -> '.join(p['path'])} "
                f"({_fmt_count(p['frequency'])} people)"
                for i, p in enumerate(paths, 1)
            )
            text = f"Career paths to {target}:\n{path_lines}"
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "type": "paths_to_role",
                        "target_role": target,
                    },
                )
            )
        return docs
