"""
SkillShock Career Intelligence Dashboard
Gradio + Plotly interactive visualizations over output.json
Launch: python dashboard.py
"""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta

import gradio as gr
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Load data once at startup
# ---------------------------------------------------------------------------
with open("output.json") as f:
    data = json.load(f)

metadata      = data["metadata"]
promo         = data["promotion_velocity"]
role_trans    = data["role_transitions"]
major_first   = data["major_to_first_role"]
industry_trans = data["industry_transitions"]
paths_to_role = data["paths_to_role"]

# ---------------------------------------------------------------------------
# Pre-compute dropdown options
# ---------------------------------------------------------------------------
_role_counts   = {r: len(targets) for r, targets in role_trans.items()}
top_roles      = sorted(_role_counts, key=_role_counts.get, reverse=True)[:50]

_real_majors   = {
    m: roles for m, roles in major_first.items()
    if len(m) >= 4
    and not re.match(r"^[\d.\-\s/,]+$", m)
    and not m.startswith('"')
    and len(roles) >= 3
    and not re.match(r"^\d", m)
}
top_majors     = sorted(_real_majors, key=lambda m: (-len(_real_majors[m]), m))
_major_lookup  = {m.strip().lower(): (m, roles) for m, roles in major_first.items()}

_ind_counts    = {ind: len(dests) for ind, dests in industry_trans.items()}
top_industries = sorted(_ind_counts, key=_ind_counts.get, reverse=True)[:30]

_path_counts   = {r: sum(p["frequency"] for p in paths) for r, paths in paths_to_role.items()}
top_target_roles = sorted(_path_counts, key=_path_counts.get, reverse=True)[:50]

# ---------------------------------------------------------------------------
# Shared styling
# ---------------------------------------------------------------------------
PLOT_BG    = "#1e1e2e"
PAPER_BG   = "#1e1e2e"
FONT_COLOR = "#cdd6f4"
GRID_COLOR = "#45475a"


def _style(fig):
    fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        font_color=FONT_COLOR, margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False)
    return fig


def _choices_prefix_first(choices: list, query: str) -> list:
    if not query or not query.strip():
        return choices
    q = query.strip().lower()
    prefix = [x for x in choices if x.lower().startswith(q)]
    rest   = [x for x in choices if x not in prefix and q in x.lower()]
    return prefix + rest


def _major_choices_for_search(query: str) -> list:
    return _choices_prefix_first(top_majors, query)


# ---------------------------------------------------------------------------
# Original chart builders (used by existing tabs AND planner)
# ---------------------------------------------------------------------------

def build_promo_chart():
    labels, months, colors, samples = [], [], [], []
    for trans, info in promo.items():
        labels.append(trans)
        months.append(info["median_months"])
        colors.append("Low Confidence" if info["low_confidence"] else "High Confidence")
        samples.append(info["sample_size"])
    fig = px.bar(
        x=months, y=labels, orientation="h", color=colors,
        color_discrete_map={"High Confidence": "#89b4fa", "Low Confidence": "#f38ba8"},
        labels={"x": "Median Months", "y": "", "color": "Confidence"},
        title="Median Months per Level Transition",
        text=[f"{m:.0f}mo (n={s:,})" for m, s in zip(months, samples)],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis=dict(autorange="reversed"), height=500)
    return _style(fig)


def build_role_transition_chart(source_role):
    targets = role_trans.get(source_role, {})
    if not targets:
        fig = go.Figure()
        fig.add_annotation(text="No data for this role", showarrow=False, font_size=18)
        return _style(fig)
    sorted_targets = sorted(targets.items(), key=lambda x: x[1], reverse=True)[:10]
    roles = [t[0] for t in sorted_targets][::-1]
    probs = [t[1] for t in sorted_targets][::-1]
    fig = px.bar(
        x=probs, y=roles, orientation="h",
        labels={"x": "Probability", "y": ""},
        title=f"Top 10 Next Roles from: {source_role}",
        text=[f"{p:.1%}" for p in probs],
        color_discrete_sequence=["#a6e3a1"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=450, xaxis_tickformat=".0%")
    return _style(fig)


def build_major_chart(major):
    roles = major_first.get(major, {})
    if not roles:
        fig = go.Figure()
        fig.add_annotation(text="No data for this major", showarrow=False, font_size=18)
        return _style(fig)
    sorted_roles = sorted(roles.items(), key=lambda x: x[1], reverse=True)[:10]
    titles = [r[0] for r in sorted_roles][::-1]
    probs  = [r[1] for r in sorted_roles][::-1]
    fig = px.bar(
        x=probs, y=titles, orientation="h",
        labels={"x": "Probability", "y": ""},
        title=f"Top 10 First Roles for: {major}",
        text=[f"{p:.1%}" for p in probs],
        color_discrete_sequence=["#f9e2af"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=450, xaxis_tickformat=".0%")
    return _style(fig)


def build_industry_chart(source_industry):
    dests = industry_trans.get(source_industry, {})
    if not dests:
        fig = go.Figure()
        fig.add_annotation(text="No data for this industry", showarrow=False, font_size=18)
        return _style(fig)
    sorted_dests = sorted(dests.items(), key=lambda x: x[1], reverse=True)[:10]
    industries = [d[0] for d in sorted_dests][::-1]
    probs      = [d[1] for d in sorted_dests][::-1]
    fig = px.bar(
        x=probs, y=industries, orientation="h",
        labels={"x": "Probability", "y": ""},
        title=f"Top 10 Industries People Switch To from: {source_industry}",
        text=[f"{p:.1%}" for p in probs],
        color_discrete_sequence=["#cba6f7"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=450, xaxis_tickformat=".0%")
    return _style(fig)


def build_paths_table(target_role):
    paths = paths_to_role.get(target_role, [])
    if not paths:
        return "<p style='color:#cdd6f4;'>No career path data for this role.</p>"
    sorted_paths = sorted(paths, key=lambda p: p["frequency"], reverse=True)[:5]
    rows = ""
    for i, entry in enumerate(sorted_paths, 1):
        path_str = " &rarr; ".join(entry["path"])
        freq = entry["frequency"]
        rows += (
            f"<tr><td style='padding:8px;color:#cdd6f4;'>{i}</td>"
            f"<td style='padding:8px;color:#cdd6f4;'>{path_str}</td>"
            f"<td style='padding:8px;color:#cdd6f4;text-align:right;'>{freq:,}</td></tr>"
        )
    return f"""
    <table style="width:100%;border-collapse:collapse;background:#1e1e2e;">
      <thead>
        <tr style="border-bottom:2px solid #45475a;">
          <th style="padding:8px;color:#89b4fa;text-align:left;">#</th>
          <th style="padding:8px;color:#89b4fa;text-align:left;">Career Path</th>
          <th style="padding:8px;color:#89b4fa;text-align:right;">Frequency</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


# ---------------------------------------------------------------------------
# AI Planner — fuzzy matching
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# AI Planner — data context builder (injects real stats into prompt)
# ---------------------------------------------------------------------------

def _gather_context(major: str, current_role: str, target_role: str, current_industry: str) -> str:
    ctx = []

    major_key = _fuzzy_find(major, major_first) if major else None
    if major_key:
        roles = sorted(major_first[major_key].items(), key=lambda x: x[1], reverse=True)[:7]
        ctx.append(
            f"Common first roles for {major_key} graduates (real data):\n" +
            "\n".join(f"  - {r}: {p:.0%} of graduates" for r, p in roles)
        )

    role_key = _fuzzy_find(current_role, role_trans) if current_role else None
    if role_key:
        nexts = sorted(role_trans[role_key].items(), key=lambda x: x[1], reverse=True)[:6]
        ctx.append(
            f"Where people go after '{role_key}' (real transition probabilities):\n" +
            "\n".join(f"  - {r}: {p:.0%}" for r, p in nexts)
        )

    target_key = _fuzzy_find(target_role, paths_to_role) if target_role else None
    if target_key:
        top_paths = sorted(paths_to_role[target_key], key=lambda p: p["frequency"], reverse=True)[:4]
        ctx.append(
            f"Most common real career paths to '{target_key}':\n" +
            "\n".join(f"  {i+1}. {' -> '.join(p['path'])} ({p['frequency']:,} people)"
                      for i, p in enumerate(top_paths))
        )

    target_trans_key = _fuzzy_find(target_role, role_trans) if target_role else None
    if target_trans_key:
        nexts = sorted(role_trans[target_trans_key].items(), key=lambda x: x[1], reverse=True)[:4]
        ctx.append(
            f"Where people go AFTER reaching '{target_trans_key}' (what comes next):\n" +
            "\n".join(f"  - {r}: {p:.0%}" for r, p in nexts)
        )

    ind_key = _fuzzy_find(current_industry, industry_trans) if current_industry else None
    if ind_key:
        dests = sorted(industry_trans[ind_key].items(), key=lambda x: x[1], reverse=True)[:5]
        ctx.append(
            f"Industries people switch to from '{ind_key}':\n" +
            "\n".join(f"  - {d}: {p:.0%}" for d, p in dests)
        )

    promo_lines = [
        f"  - {trans}: {info['median_months']:.0f} months median (n={info['sample_size']:,})"
        for trans, info in promo.items() if not info["low_confidence"]
    ]
    if promo_lines:
        ctx.append("Real promotion velocity benchmarks:\n" + "\n".join(promo_lines))

    return "\n\n".join(ctx) if ctx else "No direct data matches found — general expert advice will be provided."


# ---------------------------------------------------------------------------
# AI Planner — personalised chart builders
# ---------------------------------------------------------------------------

def _empty_fig(msg: str):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font_size=13, font_color=FONT_COLOR)
    return _style(fig)


def build_planner_role_chart(current_role: str):
    key = _fuzzy_find(current_role, role_trans) if current_role else None
    if not key:
        return _empty_fig(f"No role transition data for '{current_role}'" if current_role else "No current role entered")
    return build_role_transition_chart(key)


def build_planner_major_chart(major: str):
    key = _fuzzy_find(major, major_first) if major else None
    if not key:
        return _empty_fig(f"No data for major '{major}'" if major else "No major entered")
    return build_major_chart(key)


def build_planner_industry_chart(current_industry: str):
    key = _fuzzy_find(current_industry, industry_trans) if current_industry else None
    if not key:
        return _empty_fig(f"No industry data for '{current_industry}'" if current_industry else "No industry entered")
    return build_industry_chart(key)


def build_planner_paths_html(target_role: str):
    key = _fuzzy_find(target_role, paths_to_role) if target_role else None
    if not key:
        return (f"<p style='color:#6c7086'>No career path data found for '{target_role}'.</p>"
                if target_role else "<p style='color:#6c7086'>No target role entered.</p>")
    return build_paths_table(key)


def build_planner_promo_chart(current_role: str, target_role: str):
    """Promotion velocity chart with the student's relevant bars highlighted."""
    level_kw = {
        "C-Suite": ["ceo","cto","cfo","coo","chief"],
        "VP":      ["vp","vice president","evp","svp"],
        "Director":["director"],
        "Manager": ["manager"],
        "Staff":   ["staff","principal","lead"],
        "Senior":  ["senior","sr."],
        "IC":      ["engineer","analyst","associate","coordinator","intern","scientist"],
    }

    def infer_level(role_str):
        if not role_str:
            return None
        r = role_str.lower()
        for lvl, kws in level_kw.items():
            if any(kw in r for kw in kws):
                return lvl
        return None

    cur_lvl = infer_level(current_role)
    tgt_lvl = infer_level(target_role)

    labels, months_list, colors, samples = [], [], [], []
    for trans, info in promo.items():
        labels.append(trans)
        months_list.append(info["median_months"])
        samples.append(info["sample_size"])
        parts = [p.strip() for p in trans.split("->")]
        relevant = (
            (cur_lvl and any(cur_lvl.lower() in p.lower() for p in parts)) or
            (tgt_lvl and any(tgt_lvl.lower() in p.lower() for p in parts))
        )
        if relevant:
            colors.append("Your Path")
        elif not info["low_confidence"]:
            colors.append("High Confidence")
        else:
            colors.append("Low Confidence")

    fig = px.bar(
        x=months_list, y=labels, orientation="h", color=colors,
        color_discrete_map={
            "Your Path":       "#fab387",
            "High Confidence": "#89b4fa",
            "Low Confidence":  "#585b70",
        },
        labels={"x": "Median Months", "y": "", "color": ""},
        title="Promotion Velocity — Your Relevant Transitions Highlighted",
        text=[f"{m:.0f}mo (n={s:,})" for m, s in zip(months_list, samples)],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis=dict(autorange="reversed"), height=420)
    return _style(fig)


def build_planner_timeline_chart(plan_json: str, months_total: int):
    """Gantt-style visual roadmap from plan JSON."""
    if not plan_json:
        return _empty_fig("Generate your plan to see the visual timeline")
    try:
        plan = json.loads(plan_json)
    except Exception:
        return _empty_fig("Plan not yet generated")

    milestones = plan.get("milestones", [])
    if not milestones:
        return _empty_fig("No milestones found in plan")

    cat_colors = {
        "Skills":       "#89b4fa",
        "Networking":   "#a6e3a1",
        "Applications": "#f9e2af",
        "Experience":   "#fab387",
        "Education":    "#cba6f7",
        "Career Move":  "#f38ba8",
    }
    cat_icons = {
        "Skills": "💻", "Networking": "🤝", "Applications": "📄",
        "Experience": "🏢", "Education": "📚", "Career Move": "🚀",
    }

    fig = go.Figure()
    seen = set()

    for i, m in enumerate(milestones):
        cat   = m.get("category", "Skills")
        color = cat_colors.get(cat, "#89b4fa")
        icon  = cat_icons.get(cat, "📌")
        month = m.get("month", i + 1)
        label = f"{icon} M{month}: {m.get('title', '')}"

        fig.add_trace(go.Bar(
            x=[0.8], y=[label], base=[month - 0.4],
            orientation="h",
            marker_color=color,
            name=cat,
            legendgroup=cat,
            showlegend=(cat not in seen),
            hovertemplate=(
                f"<b>Month {month}: {m.get('title','')}</b><br>"
                f"Category: {cat}<br>"
                f"Action: {m.get('action','')}<br>"
                f"Success: {m.get('success_metric','')}<extra></extra>"
            ),
            text=m.get("title", ""),
            textposition="inside",
            insidetextanchor="middle",
        ))
        seen.add(cat)

    fig.update_layout(
        title="Your Month-by-Month Career Roadmap",
        xaxis=dict(title="Month", range=[0, months_total + 1], dtick=1, gridcolor=GRID_COLOR),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        barmode="overlay",
        height=max(350, len(milestones) * 44),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=80, b=40),
    )
    return _style(fig)


# ---------------------------------------------------------------------------
# AI Planner — PDF export (reportlab)
# ---------------------------------------------------------------------------

def generate_pdf(plan_json: str, profile_summary: str) -> str | None:
    if not plan_json:
        return None
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table,
            TableStyle, HRFlowable, PageBreak,
        )
        from reportlab.lib.enums import TA_LEFT

        plan = json.loads(plan_json)
        tmp  = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="skillshock_plan_")
        tmp.close()

        doc = SimpleDocTemplate(
            tmp.name, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch,  bottomMargin=0.75*inch,
        )

        DARK  = colors.HexColor("#1e1e2e")
        ACNT  = colors.HexColor("#89b4fa")
        GREEN = colors.HexColor("#a6e3a1")
        YLW   = colors.HexColor("#f9e2af")
        PEACH = colors.HexColor("#fab387")
        MAUVE = colors.HexColor("#cba6f7")
        RED   = colors.HexColor("#f38ba8")
        LIGHT = colors.HexColor("#cdd6f4")
        MID   = colors.HexColor("#6c7086")
        ROW1  = colors.HexColor("#181825")
        ROW2  = colors.HexColor("#1e1e2e")

        cat_colors_pdf = {
            "Skills": ACNT, "Networking": GREEN, "Applications": YLW,
            "Experience": PEACH, "Education": MAUVE, "Career Move": RED,
        }

        styles  = getSampleStyleSheet()
        s_title = ParagraphStyle("T", parent=styles["Title"], textColor=ACNT, fontSize=22, spaceAfter=4)
        s_sub   = ParagraphStyle("Sub", parent=styles["Normal"], textColor=MID, fontSize=10, spaceAfter=12)
        s_h2    = ParagraphStyle("H2", parent=styles["Heading2"], textColor=ACNT, fontSize=13, spaceBefore=14, spaceAfter=4)
        s_body  = ParagraphStyle("Body", parent=styles["Normal"], textColor=LIGHT, fontSize=9, leading=13, spaceAfter=4)
        s_blt   = ParagraphStyle("Blt", parent=styles["Normal"], textColor=LIGHT, fontSize=9, leading=13, leftIndent=12, spaceAfter=3)
        s_sm    = ParagraphStyle("Sm", parent=styles["Normal"], textColor=MID, fontSize=8, leading=11)

        story = []
        story.append(Paragraph("SkillShock Career Roadmap", s_title))
        story.append(Paragraph(profile_summary, s_sub))
        story.append(HRFlowable(width="100%", thickness=1, color=ACNT, spaceAfter=10))

        def section(title, content):
            if content:
                story.append(Paragraph(title, s_h2))
                story.append(Paragraph(content, s_body))

        section("Overview",         plan.get("summary", ""))
        section("Where You Stand",  plan.get("where_i_stand", ""))

        gaps = plan.get("gap_analysis", [])
        if gaps:
            story.append(Paragraph("Key Gaps to Close", s_h2))
            for g in gaps:
                story.append(Paragraph(f"• {g}", s_blt))

        milestones = plan.get("milestones", [])
        if milestones:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Month-by-Month Roadmap", s_h2))
            tdata = [["Mo.", "Milestone", "Category", "Action", "Success Metric"]]
            for m in milestones:
                cat = m.get("category", "")
                tdata.append([
                    Paragraph(f"<b>{m.get('month','')}</b>", s_sm),
                    Paragraph(m.get("title", ""), s_sm),
                    Paragraph(cat, s_sm),
                    Paragraph(m.get("action", ""), s_sm),
                    Paragraph(m.get("success_metric", ""), s_sm),
                ])
            col_w = [0.45*inch, 1.2*inch, 0.9*inch, 2.4*inch, 1.95*inch]
            t = Table(tdata, colWidths=col_w, repeatRows=1)
            cmds = [
                ("BACKGROUND",    (0,0),(-1,0),  ACNT),
                ("TEXTCOLOR",     (0,0),(-1,0),  DARK),
                ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0,0),(-1,0),  8),
                ("ROWBACKGROUNDS",(0,1),(-1,-1), [ROW1, ROW2]),
                ("TEXTCOLOR",     (0,1),(-1,-1), LIGHT),
                ("FONTSIZE",      (0,1),(-1,-1), 8),
                ("VALIGN",        (0,0),(-1,-1), "TOP"),
                ("GRID",          (0,0),(-1,-1), 0.25, MID),
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING", (0,0),(-1,-1), 4),
                ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ]
            for ri, m in enumerate(milestones, 1):
                c = cat_colors_pdf.get(m.get("category",""), ACNT)
                cmds += [
                    ("BACKGROUND", (2,ri),(2,ri), c),
                    ("TEXTCOLOR",  (2,ri),(2,ri), DARK),
                ]
            t.setStyle(TableStyle(cmds))
            story.append(t)

        story.append(PageBreak())

        qw = plan.get("quick_wins", [])
        if qw:
            story.append(Paragraph("Quick Wins — Next 90 Days", s_h2))
            for i, w in enumerate(qw, 1):
                story.append(Paragraph(f"{i}. {w}", s_blt))

        risks = plan.get("risks", [])
        if risks:
            story.append(Paragraph("Risks & Watch-Outs", s_h2))
            for r in risks:
                story.append(Paragraph(f"• {r}", s_blt))

        section("Salary Trajectory",                  plan.get("salary_trajectory", ""))
        section("What the Real Data Says About You",  plan.get("data_insights", ""))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "Generated by SkillShock AI  ·  Gemini 2.5 Flash  ·  Based on 75,000+ real career trajectories",
            s_sm,
        ))
        doc.build(story)
        return tmp.name

    except Exception as e:
        print(f"PDF error: {e}")
        return None


# ---------------------------------------------------------------------------
# AI Planner — ICS calendar export
# ---------------------------------------------------------------------------

def generate_ics(plan_json: str, months_total: int) -> str | None:
    if not plan_json:
        return None
    try:
        plan = json.loads(plan_json)
        milestones = plan.get("milestones", [])
        if not milestones:
            return None

        now = datetime.utcnow()
        start_date = datetime(now.year + (1 if now.month == 12 else 0),
                              1 if now.month == 12 else now.month + 1, 1)

        def fmt(dt):
            return dt.strftime("%Y%m%dT%H%M%SZ")

        def esc(text):
            return str(text).replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")

        lines = [
            "BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID:-//SkillShock//Career Planner//EN",
            "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
            "X-WR-CALNAME:SkillShock Career Plan", "X-WR-TIMEZONE:UTC",
        ]
        for i, m in enumerate(milestones):
            offset = m.get("month", i+1) - 1
            yr  = start_date.year  + (start_date.month - 1 + offset) // 12
            mo  = (start_date.month - 1 + offset) % 12 + 1
            ev  = datetime(yr, mo, 1, 9, 0, 0)
            end = ev + timedelta(hours=1)
            uid = f"skillshock-{i+1}-{now.strftime('%Y%m%d%H%M%S')}@skillshock"
            desc = (f"Category: {m.get('category','')}\n"
                    f"Action: {m.get('action','')}\n"
                    f"Success Metric: {m.get('success_metric','')}")
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{fmt(now)}",
                f"DTSTART:{fmt(ev)}",
                f"DTEND:{fmt(end)}",
                f"SUMMARY:🎯 Month {m.get('month','')}: {esc(m.get('title',''))}",
                f"DESCRIPTION:{esc(desc)}",
                f"CATEGORIES:{esc(m.get('category',''))}",
                "END:VEVENT",
            ]
        lines.append("END:VCALENDAR")

        tmp = tempfile.NamedTemporaryFile(suffix=".ics", delete=False, prefix="skillshock_calendar_")
        tmp.write("\r\n".join(lines).encode("utf-8"))
        tmp.close()
        return tmp.name

    except Exception as e:
        print(f"ICS error: {e}")
        return None


# ---------------------------------------------------------------------------
# AI Planner — Gemini generator + markdown renderer
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are SkillShock's AI Career Advisor — a world-class career strategist backed by real trajectory data from 75,000+ professionals.

Produce deeply personalized, actionable career plans. Use the real statistical data explicitly and numerically. Be a trusted mentor: honest about challenges, specific about actions, grounded in evidence. Never give generic advice.

Output ONLY a valid JSON object — no markdown fences, no preamble, no trailing text. Schema:
{
  "summary": "2-3 sentence personalized overview",
  "where_i_stand": "3-4 sentences comparing profile to real data patterns",
  "gap_analysis": ["gap1", "gap2", "gap3"],
  "milestones": [
    {
      "month": 1,
      "title": "Short title",
      "category": "one of: Skills, Networking, Applications, Experience, Education, Career Move",
      "action": "Specific actionable description",
      "success_metric": "How they know they have achieved this"
    }
  ],
  "risks": ["risk1", "risk2", "risk3"],
  "quick_wins": ["win1", "win2", "win3"],
  "salary_trajectory": "2-3 sentences on realistic comp progression",
  "data_insights": "2-3 sentences on the most surprising or useful patterns from the real data"
}

Milestones must span the FULL timeline evenly (8-12 milestones for a 12-month plan, scaled for longer). Every milestone must be concrete and specific to THIS student."""


def _build_prompt(profile: dict, data_context: str) -> str:
    return f"""Create a deeply personalized career plan for this student.

STUDENT PROFILE:
- Major / Field of Study: {profile['major'] or 'Not specified'}
- Current Role: {profile['current_role'] or 'Student / Entry level'}
- Current Industry: {profile['current_industry'] or 'Not specified'}
- Target Role: {profile['target_role'] or 'Not specified'}
- Years of Experience: {profile['years_exp']}
- Months Until Graduation / Next Transition: {profile['months_to_graduation']}
- Current Skills and Tools: {profile['skills'] or 'Not specified'}
- GPA / Academic Standing: {profile['gpa'] or 'Not specified'}
- Geographic Preference: {profile['location_pref'] or 'Not specified'}
- Work Style Preference: {profile['work_style']}
- Career Timeline Urgency: {profile['urgency']}
- Internships / Projects / Experience: {profile['internships'] or 'None specified'}
- Salary Expectations: {profile['salary_expectations'] or 'Not specified'}
- Constraints or Special Circumstances: {profile['constraints'] or 'None'}
- Additional Context: {profile['extra'] or 'None'}

REAL CAREER DATA FROM 75,000+ PROFESSIONALS:
{data_context}

Generate the JSON career plan now."""


def _render_plan_md(plan: dict, profile: dict) -> str:
    target = profile.get("target_role") or "your target role"
    months = profile.get("months_to_graduation") or 12
    cat_icons = {
        "Skills":"💻","Networking":"🤝","Applications":"📄",
        "Experience":"🏢","Education":"📚","Career Move":"🚀",
    }
    lines = [
        f"# 🎯 Your Personalized Career Roadmap",
        f"**Goal:** {target} &nbsp;|&nbsp; **Timeline:** {months} months\n",
        f"> {plan.get('summary','')}\n",
        "## 📊 Where You Stand",
        plan.get("where_i_stand","") + "\n",
        "## 🔍 Key Gaps to Close",
    ]
    for g in plan.get("gap_analysis",[]): lines.append(f"- {g}")
    lines += ["", "## 🗓️ Month-by-Month Milestones"]
    for m in plan.get("milestones",[]):
        icon = cat_icons.get(m.get("category",""),"📌")
        lines += [
            f"### {icon} Month {m['month']} — {m['title']} `[{m.get('category','')}]`",
            f"**Action:** {m['action']}",
            f"**Done when:** {m['success_metric']}\n",
        ]
    lines += ["## ⚡ Quick Wins (Next 90 Days)"]
    for i, w in enumerate(plan.get("quick_wins",[]),1): lines.append(f"{i}. {w}")
    lines += ["", "## ⚠️ Risks & Watch-Outs"]
    for r in plan.get("risks",[]): lines.append(f"- {r}")
    lines += [
        "",
        "## 💰 Salary Trajectory",
        plan.get("salary_trajectory","") + "\n",
        "## 📈 What the Real Data Says",
        plan.get("data_insights","") + "\n",
        "---",
        "*Generated by SkillShock AI · Gemini 2.5 Flash · 75,000+ real career trajectories*",
    ]
    return "\n".join(lines)


def _empty_outputs():
    ef = _empty_fig("Generate your plan to see data")
    ep = "<p style='color:#6c7086'>Generate your plan to see career path data.</p>"
    return ef, ef, ef, ep, ef, ef


def generate_career_plan(
    major, current_role, current_industry, target_role,
    years_exp, months_to_graduation, skills, gpa,
    location_pref, work_style, urgency, internships,
    salary_expectations, constraints, extra,
):
    """Stream career plan. Yields (md, raw_json, role_fig, major_fig, ind_fig, paths_html, promo_fig, timeline_fig)."""
    ef1, ef2, ef3, ep, ef4, ef5 = _empty_outputs()

    api_key = os.getenv("GOOGLE_API_KEY","")
    if not api_key:
        yield (
            "⚠️ **GOOGLE_API_KEY not set.** Get a free key at "
            "[aistudio.google.com](https://aistudio.google.com/apikey) "
            "and add `GOOGLE_API_KEY=your_key` to your `.env` file.",
            "", ef1, ef2, ef3, ep, ef4, ef5,
        )
        return

    profile = dict(
        major=major, current_role=current_role, current_industry=current_industry,
        target_role=target_role, years_exp=years_exp,
        months_to_graduation=months_to_graduation, skills=skills, gpa=gpa,
        location_pref=location_pref, work_style=work_style, urgency=urgency,
        internships=internships, salary_expectations=salary_expectations,
        constraints=constraints, extra=extra,
    )

    data_ctx = _gather_context(major, current_role, target_role, current_industry)
    prompt   = _build_prompt(profile, data_ctx)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)

    yield ("⏳ *Analyzing your profile against 75,000+ real career trajectories...*",
           "", ef1, ef2, ef3, ep, ef4, ef5)

    raw = ""
    for chunk in model.generate_content(prompt, stream=True):
        if chunk.text:
            raw += chunk.text
            yield ("⏳ *Building your personalized plan — almost there...*",
                   raw, ef1, ef2, ef3, ep, ef4, ef5)

    try:
        clean = re.sub(r"```json|```", "", raw.strip()).strip()
        plan  = json.loads(clean)
        md    = _render_plan_md(plan, profile)
        pjson = json.dumps(plan)

        role_fig     = build_planner_role_chart(current_role)
        major_fig    = build_planner_major_chart(major)
        ind_fig      = build_planner_industry_chart(current_industry)
        paths_html   = build_planner_paths_html(target_role)
        promo_fig    = build_planner_promo_chart(current_role, target_role)
        timeline_fig = build_planner_timeline_chart(pjson, int(months_to_graduation))

        yield (md, pjson, role_fig, major_fig, ind_fig, paths_html, promo_fig, timeline_fig)

    except Exception as e:
        yield (
            f"⚠️ Could not parse plan response.\n\nError: {e}\n\nRaw output:\n```\n{raw[:2000]}\n```",
            "", ef1, ef2, ef3, ep, ef4, ef5,
        )


def export_pdf(plan_json, major, current_role, target_role, months):
    if not plan_json:
        return None
    summary = (f"Major: {major or 'N/A'} | Current: {current_role or 'N/A'} "
               f"| Target: {target_role or 'N/A'} | Timeline: {months} months")
    return generate_pdf(plan_json, summary)


def export_ics(plan_json, months):
    if not plan_json:
        return None
    return generate_ics(plan_json, int(months))


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
with gr.Blocks(title="SkillShock Dashboard") as demo:

    gr.Markdown("# SkillShock — Career Intelligence Dashboard")
    gr.Markdown("*Powered by Live Data Technologies People Data*")

    with gr.Tabs():

        # ---- Tab 1: Overview ----
        with gr.Tab("Overview"):
            gr.Markdown("## Dataset Overview")
            with gr.Row():
                gr.Textbox(label="Total Persons",  value=f"{metadata['total_persons']:,}", interactive=False)
                gr.Textbox(label="Total Jobs",     value=f"{metadata['total_jobs']:,}",    interactive=False)
                gr.Textbox(label="Generated At",   value=metadata["generated_at"][:19].replace("T"," "), interactive=False)
            with gr.Row():
                gr.Textbox(label="Data Files",     value=", ".join(metadata["data_files"]), interactive=False)
            gr.Markdown("### Data Dimensions")
            with gr.Row():
                gr.Textbox(label="Unique Roles (transitions)", value=f"{len(role_trans):,}",    interactive=False)
                gr.Textbox(label="Unique Majors",              value=f"{len(major_first):,}",   interactive=False)
                gr.Textbox(label="Industries",                 value=f"{len(industry_trans):,}",interactive=False)
                gr.Textbox(label="Level Transitions",          value=str(len(promo)),           interactive=False)
                gr.Textbox(label="Target Roles (paths)",       value=f"{len(paths_to_role):,}", interactive=False)

        # ---- Tab 2: Promotion Velocity ----
        with gr.Tab("Promotion Velocity"):
            gr.Markdown("## Promotion Velocity by Level Transition")
            gr.Markdown("Median months between career level transitions. Red bars indicate low-confidence estimates.")
            promo_plot = gr.Plot(value=build_promo_chart())

        # ---- Tab 3: Role Transitions ----
        with gr.Tab("Role Transitions"):
            gr.Markdown("## Role Transition Explorer")
            gr.Markdown("Select a role to see the top 10 most likely next positions.")
            role_search = gr.Textbox(label="Search roles (prefix matches first)", placeholder="e.g. Engineer", value="")
            role_dd     = gr.Dropdown(choices=top_roles, value=top_roles[0], label="Source Role")
            role_plot   = gr.Plot(value=build_role_transition_chart(top_roles[0]))

            def update_role_dropdown(query):
                choices = _choices_prefix_first(top_roles, query)
                return gr.update(choices=choices, value=choices[0] if choices else None)

            role_search.change(fn=update_role_dropdown, inputs=role_search, outputs=role_dd)
            role_dd.change(fn=build_role_transition_chart, inputs=role_dd, outputs=role_plot)

        # ---- Tab 4: Major -> First Role ----
        with gr.Tab("Major -> First Role"):
            gr.Markdown("## Major to First Role")
            gr.Markdown("Select a major/field of study to see the top 10 first job titles.")
            major_search = gr.Textbox(label="Search majors (prefix matches first)", placeholder="e.g. Physics", value="")
            major_dd     = gr.Dropdown(choices=top_majors, value=top_majors[0], label="Major / Field of Study", allow_custom_value=True)
            major_plot   = gr.Plot(value=build_major_chart(top_majors[0]))

            def update_major_dropdown(query):
                choices = _major_choices_for_search(query)
                return gr.update(choices=choices, value=choices[0] if choices else None)

            major_search.change(fn=update_major_dropdown, inputs=major_search, outputs=major_dd)
            major_dd.change(fn=build_major_chart, inputs=major_dd, outputs=major_plot)

        # ---- Tab 5: Industry Transitions ----
        with gr.Tab("Industry Transitions"):
            gr.Markdown("## Industry Transition Explorer")
            gr.Markdown("Select an industry to see the top 10 industries people move to.")
            ind_search = gr.Textbox(label="Search industries (prefix matches first)", placeholder="e.g. Technology", value="")
            ind_dd     = gr.Dropdown(choices=top_industries, value=top_industries[0], label="Source Industry")
            ind_plot   = gr.Plot(value=build_industry_chart(top_industries[0]))

            def update_ind_dropdown(query):
                choices = _choices_prefix_first(top_industries, query)
                return gr.update(choices=choices, value=choices[0] if choices else None)

            ind_search.change(fn=update_ind_dropdown, inputs=ind_search, outputs=ind_dd)
            ind_dd.change(fn=build_industry_chart, inputs=ind_dd, outputs=ind_plot)

        # ---- Tab 6: Career Paths ----
        with gr.Tab("Career Paths"):
            gr.Markdown("## Career Path Explorer")
            gr.Markdown("Select a target role to see the top 5 most common career paths leading to it.")
            path_search = gr.Textbox(label="Search target roles (prefix matches first)", placeholder="e.g. Manager", value="")
            path_dd     = gr.Dropdown(choices=top_target_roles, value=top_target_roles[0], label="Target Role")
            path_html   = gr.HTML(value=build_paths_table(top_target_roles[0]))

            def update_path_dropdown(query):
                choices = _choices_prefix_first(top_target_roles, query)
                return gr.update(choices=choices, value=choices[0] if choices else None)

            path_search.change(fn=update_path_dropdown, inputs=path_search, outputs=path_dd)
            path_dd.change(fn=build_paths_table, inputs=path_dd, outputs=path_html)

        # ---- Tab 7: AI Career Planner ----
        with gr.Tab("🤖 AI Career Planner"):
            gr.Markdown("## 🎯 AI Career Planner")
            gr.Markdown(
                "Fill in your profile — the more detail you give, the more personalized your plan. "
                "The AI advisor matches your situation against **75,000+ real career trajectories** and generates "
                "a month-by-month roadmap *plus* the real data charts that back every recommendation."
            )

            ai_raw_state    = gr.State("")
            ai_months_state = gr.State(12)

            with gr.Row():
                # ---- Left: input form ----
                with gr.Column(scale=1, min_width=300):
                    gr.Markdown("### 🎓 Academic Background")
                    ai_major = gr.Dropdown(
                        choices=top_majors, label="Field of Study / Major",
                        allow_custom_value=True, value=top_majors[0] if top_majors else None,
                        info="Start typing to search or enter your own.")
                    ai_gpa = gr.Textbox(
                        label="GPA / Academic Standing (optional)",
                        placeholder="e.g. 3.7 / 4.0, Dean's List, Pass/Fail")
                    ai_months = gr.Slider(
                        minimum=1, maximum=48, value=12, step=1,
                        label="Months Until Graduation / Next Major Transition",
                        info="Sets your plan timeline.")

                    gr.Markdown("### 💼 Work Experience")
                    ai_years = gr.Slider(minimum=0, maximum=30, value=0, step=1,
                        label="Years of Work Experience")
                    ai_current_role = gr.Dropdown(
                        choices=top_roles, label="Current or Most Recent Role",
                        allow_custom_value=True, value=None,
                        info="Leave blank if you are a student with no experience.")
                    ai_current_industry = gr.Dropdown(
                        choices=top_industries, label="Current Industry",
                        allow_custom_value=True, value=None)
                    ai_internships = gr.Textbox(
                        label="Internships, Projects, or Relevant Experience (optional)",
                        placeholder="e.g. SWE intern at fintech startup, built ML project, research assistant",
                        lines=2)

                    gr.Markdown("### 🚀 Career Goals")
                    ai_target_role = gr.Dropdown(
                        choices=top_target_roles, label="Target / Dream Role",
                        allow_custom_value=True, value=None,
                        info="Where do you want to end up?")
                    ai_salary = gr.Textbox(
                        label="Salary Expectations (optional)",
                        placeholder="e.g. $100k year 1, $150k within 3 years")
                    ai_urgency = gr.Radio(
                        choices=["Exploring options", "Actively planning", "Urgent — need a job ASAP"],
                        label="Timeline Urgency", value="Actively planning")

                    gr.Markdown("### 🛠️ Skills & Preferences")
                    ai_skills = gr.Textbox(
                        label="Current Skills & Tools",
                        placeholder="e.g. Python, SQL, Excel, Figma, React, public speaking",
                        lines=2)
                    ai_location = gr.Textbox(
                        label="Geographic Preference (optional)",
                        placeholder="e.g. New York City, remote only, open to relocation")
                    ai_work_style = gr.Radio(
                        choices=["Startup / fast-paced", "Large company / structured", "No preference"],
                        label="Work Style Preference", value="No preference")

                    gr.Markdown("### 📝 Anything Else?")
                    ai_constraints = gr.Textbox(
                        label="Constraints or Special Circumstances (optional)",
                        placeholder="e.g. visa sponsorship needed, career switching, returning from gap year",
                        lines=2)
                    ai_extra = gr.Textbox(
                        label="Additional Context (optional)",
                        placeholder="Anything else that would help personalize your plan...",
                        lines=2)

                    ai_submit = gr.Button(
                        "✨ Generate My Personalized Career Plan",
                        variant="primary", size="lg")

                # ---- Right: plan output ----
                with gr.Column(scale=2):
                    gr.Markdown("### 📋 Your Personalized Career Plan")
                    ai_output = gr.Markdown(
                        value="*Complete the form and click **Generate** to receive your "
                              "personalized, data-driven career roadmap.*")

            # ---- Visual timeline ----
            gr.Markdown("---")
            gr.Markdown("### 📅 Visual Roadmap Timeline")
            gr.Markdown("*Interactive Gantt chart — hover over each bar for full milestone details.*")
            ai_timeline_plot = gr.Plot(label="")

            # ---- Supporting data charts ----
            gr.Markdown("---")
            gr.Markdown("### 📊 The Real Data Behind Your Plan")
            gr.Markdown(
                "These charts show actual career trajectory data from 75,000+ professionals "
                "— the evidence your recommendations are built on."
            )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 🔀 Where People Go From Your Current Role")
                    ai_role_plot = gr.Plot(label="")
                with gr.Column():
                    gr.Markdown("#### 🎓 First Jobs for Your Major")
                    ai_major_plot = gr.Plot(label="")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 🏭 Industry Switch Paths")
                    ai_industry_plot = gr.Plot(label="")
                with gr.Column():
                    gr.Markdown("#### 🛤️ Most Common Paths to Your Target Role")
                    ai_paths_html = gr.HTML(
                        value="<p style='color:#6c7086'>Generate your plan to see career path data.</p>")

            gr.Markdown("#### ⏱️ Promotion Velocity — Your Relevant Transitions Highlighted")
            ai_promo_plot = gr.Plot(label="")

            # ---- Export ----
            gr.Markdown("---")
            gr.Markdown("### 📥 Export Your Plan")
            gr.Markdown("*Export buttons activate after you generate your plan.*")
            with gr.Row():
                pdf_btn = gr.Button("📄 Download PDF Report", variant="secondary")
                ics_btn = gr.Button("📅 Add to Calendar (.ics)", variant="secondary")
            with gr.Row():
                pdf_file = gr.File(label="PDF Download", visible=False)
                ics_file = gr.File(label="Calendar File Download", visible=False)

            gr.Markdown(
                "<small>*Powered by Gemini 2.5 Flash (free tier) + SkillShock real career data. "
                "Requires `GOOGLE_API_KEY` in your `.env` — "
                "get one free at [aistudio.google.com](https://aistudio.google.com/apikey).*</small>"
            )

            # ---- Wire up generate ----
            ai_submit.click(
                fn=generate_career_plan,
                inputs=[
                    ai_major, ai_current_role, ai_current_industry, ai_target_role,
                    ai_years, ai_months, ai_skills, ai_gpa,
                    ai_location, ai_work_style, ai_urgency, ai_internships,
                    ai_salary, ai_constraints, ai_extra,
                ],
                outputs=[
                    ai_output, ai_raw_state,
                    ai_role_plot, ai_major_plot, ai_industry_plot,
                    ai_paths_html, ai_promo_plot, ai_timeline_plot,
                ],
            )

            # Keep months in state for exports
            ai_months.change(fn=lambda m: m, inputs=ai_months, outputs=ai_months_state)

            # ---- Wire up exports ----
            pdf_btn.click(
                fn=export_pdf,
                inputs=[ai_raw_state, ai_major, ai_current_role, ai_target_role, ai_months_state],
                outputs=pdf_file,
            ).then(fn=lambda: gr.update(visible=True), outputs=pdf_file)

            ics_btn.click(
                fn=export_ics,
                inputs=[ai_raw_state, ai_months_state],
                outputs=ics_file,
            ).then(fn=lambda: gr.update(visible=True), outputs=ics_file)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())