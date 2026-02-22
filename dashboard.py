"""
SkillShock — Career Intelligence Dashboard
Backend: FastAPI serving JSON data endpoints
Frontend: ui.html (pure HTML/CSS/JS + Plotly CDN)
Run: python dashboard.py
"""

import json, os, re, threading, time, webbrowser
from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError:
    os.system("pip install fastapi uvicorn --break-system-packages -q")
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn

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


def _open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:7860")


if __name__ == "__main__":
    print("\n  SkillShock  ->  http://127.0.0.1:7860\n")
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")