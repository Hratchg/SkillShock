"""
SkillShock — Career Intelligence Dashboard
Backend: FastAPI serving JSON data endpoints + AI Career Planner
Frontend: ui.html (pure HTML/CSS/JS + Plotly CDN)
Run: python dashboard.py
"""

import json, os, re, threading, time, webbrowser, tempfile
from pathlib import Path
from datetime import datetime, timedelta

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    import uvicorn
except ImportError:
    os.system("pip install fastapi uvicorn --break-system-packages -q")
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    import uvicorn

from dotenv import load_dotenv
load_dotenv()

# ── Load data ────────────────────────────────────────────────────
with open("output.json") as f:
    raw = json.load(f)

metadata       = raw["metadata"]
promo          = raw["promotion_velocity"]
role_trans     = raw["role_transitions"]
major_first    = raw["major_to_first_role"]
industry_trans = raw["industry_transitions"]
paths_to_role  = raw["paths_to_role"]

_role_counts = {r: len(t) for r, t in role_trans.items()}
top_roles = sorted(_role_counts, key=_role_counts.get, reverse=True)[:50]

_real_majors = {
    m: roles for m, roles in major_first.items()
    if len(m) >= 4
    and not re.match(r"^[\d.\-\s/,]+$", m)
    and not m.startswith('"')
    and len(roles) >= 3
    and not re.match(r"^\d", m)
}
top_majors = sorted(_real_majors, key=lambda m: (-len(_real_majors[m]), m))

_ind_counts      = {i: len(d) for i, d in industry_trans.items()}
top_industries   = sorted(_ind_counts, key=_ind_counts.get, reverse=True)[:30]
_path_counts     = {r: sum(p["frequency"] for p in ps) for r, ps in paths_to_role.items()}
top_target_roles = sorted(_path_counts, key=_path_counts.get, reverse=True)[:50]

# ── RAG setup (RapidFire LangChainRagSpec) ────────────────────────
USE_RAG = os.getenv("USE_RAG", "true").lower() in ("true", "1", "yes")
rag_spec = None
if USE_RAG:
    try:
        from rag_config import build_rag_spec, retrieve_context
        rag_spec = build_rag_spec(raw, k=8)
        print("RapidFire RAG active — FAISS index built.")
    except Exception as e:
        print(f"RAG init failed ({e}), using exact-match fallback.")

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(title="SkillShock")
UI_FILE = Path(__file__).parent / "ui.html"


@app.get("/", response_class=HTMLResponse)
def index():
    return UI_FILE.read_text(encoding="utf-8")


@app.get("/api/meta")
def api_meta():
    return JSONResponse({
        "metadata":         metadata,
        "top_roles":        top_roles,
        "top_majors":       top_majors,
        "top_industries":   top_industries,
        "top_target_roles": top_target_roles,
        "stats": {
            "total_persons": metadata["total_persons"],
            "total_jobs":    metadata["total_jobs"],
            "unique_roles":  len(role_trans),
            "majors":        len(major_first),
            "industries":    len(industry_trans),
            "target_roles":  len(paths_to_role),
        }
    })


@app.get("/api/promo")
def api_promo():
    return JSONResponse({
        k: {"median_months": v["median_months"],
            "sample_size":   v["sample_size"],
            "low_confidence": v["low_confidence"]}
        for k, v in promo.items()
    })


@app.get("/api/role/{role}")
def api_role(role: str):
    t = role_trans.get(role, {})
    return JSONResponse({"role": role, "transitions": sorted(t.items(), key=lambda x: x[1], reverse=True)[:10]})


@app.get("/api/major/{major}")
def api_major(major: str):
    r = major_first.get(major, {})
    return JSONResponse({"major": major, "roles": sorted(r.items(), key=lambda x: x[1], reverse=True)[:10]})


@app.get("/api/industry/{industry}")
def api_industry(industry: str):
    d = industry_trans.get(industry, {})
    return JSONResponse({"industry": industry, "destinations": sorted(d.items(), key=lambda x: x[1], reverse=True)[:10]})


@app.get("/api/paths/{role}")
def api_paths(role: str):
    p = paths_to_role.get(role, [])
    return JSONResponse({"role": role, "paths": sorted(p, key=lambda x: x["frequency"], reverse=True)[:5]})


@app.get("/api/sankey/major")
def api_sankey_major(major: str = ""):
    """Sankey data for Major → First Role. If major is given, single-major view; else top-12 overview."""
    top_n_majors = 12
    top_n_roles_per = 5
    top_roles_single = 15

    if major and major.strip():
        roles_dict = _real_majors.get(major) or major_first.get(major) or {}
        if not roles_dict:
            return JSONResponse({"nodes": [], "links": []})
        sorted_roles = sorted(roles_dict.items(), key=lambda x: x[1], reverse=True)[:top_roles_single]
        nodes = [major] + [r for r, _ in sorted_roles]
        links = [{"source": 0, "target": i + 1, "value": round(p * 1000)} for i, (_, p) in enumerate(sorted_roles)]
        return JSONResponse({"nodes": nodes, "links": links, "title": f"Career Flow: {major} → First Role"})

    # All-majors overview
    nodes = []
    major_to_idx = {}
    role_to_idx = {}
    top_m = list(_real_majors.keys())[:top_n_majors]
    for m in top_m:
        major_to_idx[m] = len(nodes)
        nodes.append(m)
    links = []
    for m in top_m:
        roles = _real_majors[m]
        sorted_r = sorted(roles.items(), key=lambda x: x[1], reverse=True)[:top_n_roles_per]
        for title, prob in sorted_r:
            if title not in role_to_idx:
                role_to_idx[title] = len(nodes)
                nodes.append(title)
            links.append({"source": major_to_idx[m], "target": role_to_idx[title], "value": round(prob * 1000)})
    return JSONResponse({"nodes": nodes, "links": links, "title": "Career Flow: Major → First Role"})


@app.get("/api/sankey/industry")
def api_sankey_industry():
    """Sankey data for Industry → Next Industry transfers."""
    top_n = 10
    ind_counts = {ind: len(dests) for ind, dests in industry_trans.items()}
    top_ind = sorted(ind_counts, key=ind_counts.get, reverse=True)[:top_n]
    nodes = list(top_ind)
    dest_set = set()
    for ind in top_ind:
        for d in list(industry_trans[ind].keys())[:5]:
            dest_set.add(d)
    for d in sorted(dest_set, key=lambda x: -sum(industry_trans.get(s, {}).get(x, 0) for s in top_ind))[:top_n * 2]:
        if d not in nodes:
            nodes.append(d)
    node_to_idx = {n: i for i, n in enumerate(nodes)}
    links = []
    for ind in top_ind:
        dests = industry_trans.get(ind, {})
        sorted_d = sorted(dests.items(), key=lambda x: x[1], reverse=True)[:5]
        for d, prob in sorted_d:
            j = node_to_idx.get(d)
            if j is not None:
                links.append({"source": node_to_idx[ind], "target": j, "value": round(prob * 500)})
    return JSONResponse({"nodes": nodes, "links": links})


# ── AI Planner helpers ────────────────────────────────────────────

def _fuzzy_find(key: str, lookup: dict):
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


def _gather_context(major, current_role, target_role, current_industry) -> str:
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
            f"Where people go AFTER reaching '{target_trans_key}':\n" +
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


def _infer_level(role_str: str):
    if not role_str:
        return None
    level_kw = {
        "C-Suite": ["ceo","cto","cfo","coo","chief"],
        "VP":      ["vp","vice president","evp","svp"],
        "Director":["director"],
        "Manager": ["manager"],
        "Staff":   ["staff","principal","lead"],
        "Senior":  ["senior","sr."],
        "IC":      ["engineer","analyst","associate","coordinator","intern","scientist"],
    }
    r = role_str.lower()
    for lvl, kws in level_kw.items():
        if any(kw in r for kw in kws):
            return lvl
    return None


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
- Major / Field of Study: {profile.get('major') or 'Not specified'}
- Current Role: {profile.get('current_role') or 'Student / Entry level'}
- Current Industry: {profile.get('current_industry') or 'Not specified'}
- Target Role: {profile.get('target_role') or 'Not specified'}
- Years of Experience: {profile.get('years_exp', 0)}
- Months Until Graduation / Next Transition: {profile.get('months_to_graduation', 12)}
- Current Skills and Tools: {profile.get('skills') or 'Not specified'}
- GPA / Academic Standing: {profile.get('gpa') or 'Not specified'}
- Geographic Preference: {profile.get('location_pref') or 'Not specified'}
- Work Style Preference: {profile.get('work_style', 'No preference')}
- Career Timeline Urgency: {profile.get('urgency', 'Actively planning')}
- Internships / Projects / Experience: {profile.get('internships') or 'None specified'}
- Salary Expectations: {profile.get('salary_expectations') or 'Not specified'}
- Constraints or Special Circumstances: {profile.get('constraints') or 'None'}
- Additional Context: {profile.get('extra') or 'None'}

REAL CAREER DATA FROM 75,000+ PROFESSIONALS:
{data_context}

Generate the JSON career plan now."""


@app.post("/api/planner/generate")
async def api_planner_generate(body: dict):
    """Generate a career plan via Gemini. Returns JSON with plan + supporting data."""
    try:
        import google.generativeai as genai
    except ImportError:
        os.system("pip install google-generativeai --break-system-packages -q")
        import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return JSONResponse({"error": "GOOGLE_API_KEY not set. Add it to your .env file."}, status_code=400)

    if rag_spec:
        data_ctx = retrieve_context(rag_spec, body)
    else:
        data_ctx = _gather_context(
            body.get("major"), body.get("current_role"),
            body.get("target_role"), body.get("current_industry")
        )
    prompt = _build_prompt(body, data_ctx)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(prompt)
    raw = response.text

    clean = re.sub(r"```json|```", "", raw.strip()).strip()
    plan  = json.loads(clean)

    # Build supporting data payloads
    def role_data(role):
        key = _fuzzy_find(role, role_trans)
        if not key: return []
        return sorted(role_trans[key].items(), key=lambda x: x[1], reverse=True)[:10]

    def major_data(major):
        key = _fuzzy_find(major, major_first)
        if not key: return []
        return sorted(major_first[key].items(), key=lambda x: x[1], reverse=True)[:10]

    def industry_data(industry):
        key = _fuzzy_find(industry, industry_trans)
        if not key: return []
        return sorted(industry_trans[key].items(), key=lambda x: x[1], reverse=True)[:10]

    def paths_data(role):
        key = _fuzzy_find(role, paths_to_role)
        if not key: return []
        return sorted(paths_to_role[key], key=lambda x: x["frequency"], reverse=True)[:5]

    def promo_data(current_role, target_role):
        cur_lvl = _infer_level(current_role)
        tgt_lvl = _infer_level(target_role)
        out = []
        for trans, info in promo.items():
            parts = [p.strip() for p in trans.split("->")]
            relevant = (
                (cur_lvl and any(cur_lvl.lower() in p.lower() for p in parts)) or
                (tgt_lvl and any(tgt_lvl.lower() in p.lower() for p in parts))
            )
            out.append({
                "label": trans,
                "months": info["median_months"],
                "sample": info["sample_size"],
                "low_confidence": info["low_confidence"],
                "relevant": relevant,
            })
        return out

    return JSONResponse({
        "plan": plan,
        "supporting": {
            "role_transitions":     role_data(body.get("current_role")),
            "major_first_roles":    major_data(body.get("major")),
            "industry_destinations":industry_data(body.get("current_industry")),
            "paths_to_target":      paths_data(body.get("target_role")),
            "promo_velocity":       promo_data(body.get("current_role"), body.get("target_role")),
        }
    })


@app.post("/api/planner/pdf")
async def api_planner_pdf(body: dict):
    plan_json       = body.get("plan_json", "")
    profile_summary = body.get("profile_summary", "SkillShock Career Plan")
    if not plan_json:
        return JSONResponse({"error": "No plan provided"}, status_code=400)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table,
            TableStyle, HRFlowable, PageBreak,
        )

        plan = json.loads(plan_json)
        tmp  = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="skillshock_plan_")
        tmp.close()

        DARK  = colors.HexColor("#0b0b0b");  ACNT  = colors.HexColor("#c9a96e")
        GREEN = colors.HexColor("#6ea87a");  PEACH = colors.HexColor("#c4855a")
        MAUVE = colors.HexColor("#8b7cba");  RED   = colors.HexColor("#b85c5c")
        LIGHT = colors.HexColor("#f4f4f4");  MID   = colors.HexColor("#8a8a8a")
        ROW1  = colors.HexColor("#111111");  ROW2  = colors.HexColor("#161616")

        cat_colors_pdf = {
            "Skills": ACNT,  "Networking": GREEN, "Applications": ACNT,
            "Experience": PEACH, "Education": MAUVE, "Career Move": RED,
        }
        styles  = getSampleStyleSheet()
        s_title = ParagraphStyle("T",   parent=styles["Title"],   textColor=ACNT,  fontSize=22, spaceAfter=4)
        s_sub   = ParagraphStyle("Sub", parent=styles["Normal"],  textColor=MID,   fontSize=10, spaceAfter=12)
        s_h2    = ParagraphStyle("H2",  parent=styles["Heading2"],textColor=ACNT,  fontSize=13, spaceBefore=14, spaceAfter=4)
        s_body  = ParagraphStyle("Body",parent=styles["Normal"],  textColor=LIGHT, fontSize=9,  leading=13, spaceAfter=4)
        s_blt   = ParagraphStyle("Blt", parent=styles["Normal"],  textColor=LIGHT, fontSize=9,  leading=13, leftIndent=12, spaceAfter=3)
        s_sm    = ParagraphStyle("Sm",  parent=styles["Normal"],  textColor=MID,   fontSize=8,  leading=11)

        doc = SimpleDocTemplate(tmp.name, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch,  bottomMargin=0.75*inch)

        story = [
            Paragraph("SkillShock Career Roadmap", s_title),
            Paragraph(profile_summary, s_sub),
            HRFlowable(width="100%", thickness=1, color=ACNT, spaceAfter=10),
        ]

        def section(title, content):
            if content:
                story.append(Paragraph(title, s_h2))
                story.append(Paragraph(content, s_body))

        section("Overview",        plan.get("summary", ""))
        section("Where You Stand", plan.get("where_i_stand", ""))

        for g in plan.get("gap_analysis", []):
            story.append(Paragraph(f"• {g}", s_blt))

        milestones = plan.get("milestones", [])
        if milestones:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Month-by-Month Roadmap", s_h2))
            tdata = [["Mo.", "Milestone", "Category", "Action", "Success Metric"]]
            for m in milestones:
                tdata.append([
                    Paragraph(f"<b>{m.get('month','')}</b>", s_sm),
                    Paragraph(m.get("title",""), s_sm),
                    Paragraph(m.get("category",""), s_sm),
                    Paragraph(m.get("action",""), s_sm),
                    Paragraph(m.get("success_metric",""), s_sm),
                ])
            col_w = [0.45*inch, 1.2*inch, 0.9*inch, 2.4*inch, 1.95*inch]
            t = Table(tdata, colWidths=col_w, repeatRows=1)
            cmds = [
                ("BACKGROUND",(0,0),(-1,0),ACNT),("TEXTCOLOR",(0,0),(-1,0),DARK),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[ROW1,ROW2]),
                ("TEXTCOLOR",(0,1),(-1,-1),LIGHT),("FONTSIZE",(0,1),(-1,-1),8),
                ("VALIGN",(0,0),(-1,-1),"TOP"),("GRID",(0,0),(-1,-1),0.25,MID),
                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),4),
            ]
            for ri, m in enumerate(milestones, 1):
                c = cat_colors_pdf.get(m.get("category",""), ACNT)
                cmds += [("BACKGROUND",(2,ri),(2,ri),c),("TEXTCOLOR",(2,ri),(2,ri),DARK)]
            t.setStyle(TableStyle(cmds))
            story.append(t)

        story.append(PageBreak())
        for i, w in enumerate(plan.get("quick_wins",[]),1):
            story.append(Paragraph(f"{i}. {w}", s_blt))
        for r in plan.get("risks",[]):
            story.append(Paragraph(f"• {r}", s_blt))

        section("Salary Trajectory",                plan.get("salary_trajectory",""))
        section("What the Real Data Says About You", plan.get("data_insights",""))
        story += [Spacer(1,20), HRFlowable(width="100%",thickness=0.5,color=MID), Spacer(1,4),
                  Paragraph("Generated by SkillShock AI · Gemini 2.5 Flash · 75,000+ real career trajectories", s_sm)]
        doc.build(story)
        return FileResponse(tmp.name, filename="skillshock_plan.pdf", media_type="application/pdf")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/planner/ics")
async def api_planner_ics(body: dict):
    plan_json    = body.get("plan_json","")
    months_total = int(body.get("months_total", 12))
    if not plan_json:
        return JSONResponse({"error": "No plan"}, status_code=400)
    try:
        plan       = json.loads(plan_json)
        milestones = plan.get("milestones",[])
        if not milestones:
            return JSONResponse({"error":"No milestones"}, status_code=400)

        now        = datetime.utcnow()
        start_date = datetime(now.year + (1 if now.month==12 else 0),
                              1 if now.month==12 else now.month+1, 1)

        def fmt(dt): return dt.strftime("%Y%m%dT%H%M%SZ")
        def esc(t): return str(t).replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")

        lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//SkillShock//EN",
                 "CALSCALE:GREGORIAN","METHOD:PUBLISH",
                 "X-WR-CALNAME:SkillShock Career Plan","X-WR-TIMEZONE:UTC"]
        for i,m in enumerate(milestones):
            offset = m.get("month",i+1)-1
            yr = start_date.year+(start_date.month-1+offset)//12
            mo = (start_date.month-1+offset)%12+1
            ev = datetime(yr,mo,1,9,0,0); end=ev+timedelta(hours=1)
            lines += ["BEGIN:VEVENT",
                      f"UID:skillshock-{i+1}-{now.strftime('%Y%m%d%H%M%S')}@skillshock",
                      f"DTSTAMP:{fmt(now)}",f"DTSTART:{fmt(ev)}",f"DTEND:{fmt(end)}",
                      f"SUMMARY:Month {m.get('month','')}: {esc(m.get('title',''))}",
                      f"DESCRIPTION:{esc('Category: '+m.get('category','')+chr(10)+'Action: '+m.get('action',''))}",
                      "END:VEVENT"]
        lines.append("END:VCALENDAR")
        tmp=tempfile.NamedTemporaryFile(suffix=".ics",delete=False,prefix="skillshock_cal_")
        tmp.write("\r\n".join(lines).encode("utf-8")); tmp.close()
        return FileResponse(tmp.name, filename="skillshock_plan.ics", media_type="text/calendar")
    except Exception as e:
        return JSONResponse({"error":str(e)}, status_code=500)


def _open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:7860")


if __name__ == "__main__":
    print("\n  SkillShock  ->  http://127.0.0.1:7860\n")
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")
