"""
SkillShock Career Intelligence Dashboard
Gradio + Plotly interactive visualizations over output.json
Launch: python dashboard.py
"""

import json
import re
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Load data once at startup
# ---------------------------------------------------------------------------
with open("output.json") as f:
    data = json.load(f)

metadata = data["metadata"]
promo = data["promotion_velocity"]
role_trans = data["role_transitions"]
major_first = data["major_to_first_role"]
industry_trans = data["industry_transitions"]
paths_to_role = data["paths_to_role"]

# ---------------------------------------------------------------------------
# Pre-compute dropdown options (top-N most common entries)
# ---------------------------------------------------------------------------

# Top 50 source roles: pick roles with the most unique next-role targets
_role_counts = {r: len(targets) for r, targets in role_trans.items()}
top_roles = sorted(_role_counts, key=_role_counts.get, reverse=True)[:50]

# Top 50 majors: filter to real-looking names (>= 4 chars, not numeric, >= 3 roles)
_real_majors = {
    m: roles for m, roles in major_first.items()
    if len(m) >= 4
    and not re.match(r"^[\d.\-\s/,]+$", m)
    and not m.startswith('"')
    and len(roles) >= 3
    and not re.match(r"^\d", m)
}
top_majors = sorted(_real_majors, key=lambda m: (-len(_real_majors[m]), m))[:50]

# Top 30 industries by number of destination industries
_ind_counts = {ind: len(dests) for ind, dests in industry_trans.items()}
top_industries = sorted(_ind_counts, key=_ind_counts.get, reverse=True)[:30]

# Top 50 target roles for career paths: pick roles with the most recorded paths
_path_counts = {r: sum(p["frequency"] for p in paths) for r, paths in paths_to_role.items()}
top_target_roles = sorted(_path_counts, key=_path_counts.get, reverse=True)[:50]

# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

PLOT_BG = "#1e1e2e"
PAPER_BG = "#1e1e2e"
FONT_COLOR = "#cdd6f4"
GRID_COLOR = "#45475a"


def _style(fig):
    """Apply consistent dark styling to a plotly figure."""
    fig.update_layout(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font_color=FONT_COLOR,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False)
    return fig


def build_promo_chart():
    """Bar chart of median months per level transition, colored by confidence."""
    labels, months, colors, samples = [], [], [], []
    for trans, info in promo.items():
        labels.append(trans)
        months.append(info["median_months"])
        colors.append("Low Confidence" if info["low_confidence"] else "High Confidence")
        samples.append(info["sample_size"])

    fig = px.bar(
        x=months, y=labels, orientation="h",
        color=colors,
        color_discrete_map={"High Confidence": "#89b4fa", "Low Confidence": "#f38ba8"},
        labels={"x": "Median Months", "y": "", "color": "Confidence"},
        title="Median Months per Level Transition",
        text=[f"{m:.0f}mo (n={s:,})" for m, s in zip(months, samples)],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis=dict(autorange="reversed"), height=500)
    return _style(fig)


def build_role_transition_chart(source_role):
    """Top 10 next roles for a given source role."""
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
    """Top 10 first job titles for a given major."""
    roles = major_first.get(major, {})
    if not roles:
        fig = go.Figure()
        fig.add_annotation(text="No data for this major", showarrow=False, font_size=18)
        return _style(fig)

    sorted_roles = sorted(roles.items(), key=lambda x: x[1], reverse=True)[:10]
    titles = [r[0] for r in sorted_roles][::-1]
    probs = [r[1] for r in sorted_roles][::-1]

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
    """Top 10 destination industries from a given source industry."""
    dests = industry_trans.get(source_industry, {})
    if not dests:
        fig = go.Figure()
        fig.add_annotation(text="No data for this industry", showarrow=False, font_size=18)
        return _style(fig)

    sorted_dests = sorted(dests.items(), key=lambda x: x[1], reverse=True)[:10]
    industries = [d[0] for d in sorted_dests][::-1]
    probs = [d[1] for d in sorted_dests][::-1]

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
    """Top 5 career paths to reach a target role, returned as HTML table."""
    paths = paths_to_role.get(target_role, [])
    if not paths:
        return "<p style='color:#cdd6f4;'>No career path data for this role.</p>"

    # Sort by frequency descending, take top 5
    sorted_paths = sorted(paths, key=lambda p: p["frequency"], reverse=True)[:5]

    rows = ""
    for i, entry in enumerate(sorted_paths, 1):
        path_str = " &rarr; ".join(entry["path"])
        freq = entry["frequency"]
        rows += f"<tr><td style='padding:8px;color:#cdd6f4;'>{i}</td>"
        rows += f"<td style='padding:8px;color:#cdd6f4;'>{path_str}</td>"
        rows += f"<td style='padding:8px;color:#cdd6f4;text-align:right;'>{freq:,}</td></tr>"

    html = f"""
    <table style="width:100%;border-collapse:collapse;background:#1e1e2e;">
      <thead>
        <tr style="border-bottom:2px solid #45475a;">
          <th style="padding:8px;color:#89b4fa;text-align:left;">#</th>
          <th style="padding:8px;color:#89b4fa;text-align:left;">Career Path</th>
          <th style="padding:8px;color:#89b4fa;text-align:right;">Frequency</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return html


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
with gr.Blocks(theme=gr.themes.Soft(), title="SkillShock Dashboard") as demo:

    gr.Markdown("# SkillShock — Career Intelligence Dashboard")
    gr.Markdown("*Powered by Live Data Technologies People Data*")

    with gr.Tabs():

        # ---- Tab 1: Overview ----
        with gr.Tab("Overview"):
            gr.Markdown("## Dataset Overview")
            with gr.Row():
                gr.Textbox(
                    label="Total Persons",
                    value=f"{metadata['total_persons']:,}",
                    interactive=False,
                )
                gr.Textbox(
                    label="Total Jobs",
                    value=f"{metadata['total_jobs']:,}",
                    interactive=False,
                )
                gr.Textbox(
                    label="Generated At",
                    value=metadata["generated_at"][:19].replace("T", " "),
                    interactive=False,
                )
            with gr.Row():
                gr.Textbox(
                    label="Data Files",
                    value=", ".join(metadata["data_files"]),
                    interactive=False,
                )
            gr.Markdown("### Data Dimensions")
            with gr.Row():
                gr.Textbox(label="Unique Roles (transitions)", value=f"{len(role_trans):,}", interactive=False)
                gr.Textbox(label="Unique Majors", value=f"{len(major_first):,}", interactive=False)
                gr.Textbox(label="Industries", value=f"{len(industry_trans):,}", interactive=False)
                gr.Textbox(label="Level Transitions", value=str(len(promo)), interactive=False)
                gr.Textbox(label="Target Roles (paths)", value=f"{len(paths_to_role):,}", interactive=False)

        # ---- Tab 2: Promotion Velocity ----
        with gr.Tab("Promotion Velocity"):
            gr.Markdown("## Promotion Velocity by Level Transition")
            gr.Markdown("Median months between career level transitions. Red bars indicate low-confidence estimates.")
            promo_plot = gr.Plot(value=build_promo_chart())

        # ---- Tab 3: Role Transitions ----
        with gr.Tab("Role Transitions"):
            gr.Markdown("## Role Transition Explorer")
            gr.Markdown("Select a role to see the top 10 most likely next positions.")
            role_dd = gr.Dropdown(
                choices=top_roles,
                value=top_roles[0],
                label="Source Role",
            )
            role_plot = gr.Plot(value=build_role_transition_chart(top_roles[0]))
            role_dd.change(fn=build_role_transition_chart, inputs=role_dd, outputs=role_plot)

        # ---- Tab 4: Major -> First Role ----
        with gr.Tab("Major -> First Role"):
            gr.Markdown("## Major to First Role")
            gr.Markdown("Select a major/field of study to see the top 10 first job titles.")
            major_dd = gr.Dropdown(
                choices=top_majors,
                value=top_majors[0],
                label="Major / Field of Study",
            )
            major_plot = gr.Plot(value=build_major_chart(top_majors[0]))
            major_dd.change(fn=build_major_chart, inputs=major_dd, outputs=major_plot)

        # ---- Tab 5: Industry Transitions ----
        with gr.Tab("Industry Transitions"):
            gr.Markdown("## Industry Transition Explorer")
            gr.Markdown("Select an industry to see the top 10 industries people move to.")
            ind_dd = gr.Dropdown(
                choices=top_industries,
                value=top_industries[0],
                label="Source Industry",
            )
            ind_plot = gr.Plot(value=build_industry_chart(top_industries[0]))
            ind_dd.change(fn=build_industry_chart, inputs=ind_dd, outputs=ind_plot)

        # ---- Tab 6: Career Paths ----
        with gr.Tab("Career Paths"):
            gr.Markdown("## Career Path Explorer")
            gr.Markdown("Select a target role to see the top 5 most common career paths leading to it.")
            path_dd = gr.Dropdown(
                choices=top_target_roles,
                value=top_target_roles[0],
                label="Target Role",
            )
            path_html = gr.HTML(value=build_paths_table(top_target_roles[0]))
            path_dd.change(fn=build_paths_table, inputs=path_dd, outputs=path_html)


if __name__ == "__main__":
    demo.launch()
