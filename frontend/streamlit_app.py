import streamlit as st
from io import BytesIO
from supabase_auth import authenticate_user, register_user
from text_extraction import extract_text_from_file
import json
from jd_to_text import jobPosting_pre_processing
import datetime
import zipfile
import os
import requests
import time
import math
import random
from google.cloud import storage

API_BASE_URL = os.getenv("RESUMATRIX_API_URL", "http://localhost:8000") + "/api"
GCP_BUCKET = os.getenv("GCP_BUCKET_NAME")

gcs_client = storage.Client(project=os.environ.get("GCP_PROJECT_ID"))
bucket = gcs_client.bucket(GCP_BUCKET)

st.set_page_config(page_title="ResuMatrix", page_icon="📋", layout="wide")

# ── Design system ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0a0c14;
    color: #f0f2f7;
}
[data-testid="stSidebar"] {
    background-color: #0f1117;
    border-right: 1px solid #1e2235;
}
[data-testid="stSidebar"] * { color: #c8cdd8 !important; }

/* ── Typography ── */
h1, h2, h3, h4 { color: #f0f2f7 !important; font-weight: 700; letter-spacing: -0.02em; }
.page-title {
    font-size: 2.2rem; font-weight: 800; color: #f0f2f7;
    letter-spacing: -0.04em; margin-bottom: 0.1rem;
}
.page-subtitle { font-size: 1rem; color: #6b7280; margin-bottom: 2rem; }
.section-heading {
    font-size: 0.72rem; font-weight: 700; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.1em;
    border-bottom: 1px solid #1e2235; padding-bottom: 10px;
    margin: 32px 0 20px;
}

/* ── Cards ── */
.rm-card {
    background: #111420;
    border: 1px solid #1e2235;
    border-radius: 12px;
    padding: 0;
    margin-bottom: 14px;
    transition: border-color 0.2s, box-shadow 0.2s;
    overflow: hidden;
    position: relative;
}
.rm-card:hover {
    border-color: #2d3456;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.rm-card.ranked {
    border-left: 3px solid #00d26a;
}
.rm-card.ranked::before {
    content: '';
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 200px;
    background: linear-gradient(90deg, #00d26a06 0%, transparent 100%);
    pointer-events: none;
}
.rm-card.unfit-card {
    border-left: 3px solid #ff444455;
    opacity: 0.82;
}
.rm-card-inner {
    padding: 24px 28px;
}
.rm-card-header {
    display: flex; align-items: center;
    justify-content: space-between; gap: 20px;
    margin-bottom: 18px;
}
.rm-card-meta { flex: 1; min-width: 0; }
.rm-card-title { font-size: 1.15rem; font-weight: 800; color: #f0f2f7; letter-spacing: -0.02em; margin-bottom: 4px; }
.rm-card-sub { font-size: 0.78rem; color: #6b7280; }

/* ── Rank badge ── */
.rank-badge {
    display: inline-block;
    background: #00d26a14; color: #00d26a;
    border: 1px solid #00d26a30;
    border-radius: 5px; padding: 2px 10px;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.05em; margin-bottom: 8px;
}
.unfit-badge {
    display: inline-block;
    background: #ff444414; color: #ff6b6b;
    border: 1px solid #ff444430;
    border-radius: 5px; padding: 2px 10px;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.05em; margin-bottom: 8px;
}

/* ── Arc gauge ── */
.gauge-wrap {
    flex-shrink: 0;
    display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.gauge-label {
    font-size: 0.62rem; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.08em;
}

/* ── Progress bars ── */
.score-section {
    border-top: 1px solid #1e2235;
    padding: 16px 28px 20px;
}
.score-row { display: flex; align-items: center; gap: 10px; margin: 6px 0; }
.score-row-label { font-size: 0.75rem; color: #6b7280; width: 82px; flex-shrink: 0; }
.score-bar-bg {
    flex: 1; height: 4px; background: #1e2235; border-radius: 2px; overflow: hidden;
}
.score-bar-fill { height: 4px; border-radius: 2px; }
.score-row-pct { font-size: 0.75rem; font-weight: 600; width: 34px; text-align: right; flex-shrink: 0; }

/* ── Reasoning layer ── */
.card-summary {
    font-size: 0.82rem; color: #6b7280; font-style: italic;
    line-height: 1.55; margin-top: 14px;
    padding-top: 12px; border-top: 1px solid #1e2235;
}
.missing-row {
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
    margin-top: 10px;
}
.missing-label {
    font-size: 0.68rem; font-weight: 700; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.08em; flex-shrink: 0;
}
.missing-pill {
    display: inline-block;
    background: #ef444414; color: #f87171;
    border: 1px solid #ef444430;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.72rem; font-weight: 600;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #111420 !important;
    border: 1px solid #1e2235 !important;
    color: #f0f2f7 !important;
    border-radius: 8px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #00d26a44 !important;
    box-shadow: 0 0 0 3px #00d26a0a !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border: 1px dashed #1e2235 !important;
    border-radius: 10px !important;
    background: #111420 !important;
}
[data-testid="stFileUploader"] section {
    border: none !important;
    background: transparent !important;
}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
    background-color: #111420 !important;
    color: #00d26a !important;
    border: 1px solid #00d26a44 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
[data-testid="stFileUploader"] button:hover,
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]:hover {
    background-color: #00d26a14 !important;
    border-color: #00d26a !important;
}

/* ── Buttons ── */
.stButton > button {
    background-color: #00d26a !important;
    color: #0a0c14 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 11px 22px !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em !important;
    transition: opacity 0.15s, transform 0.1s !important;
}
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0) !important; }
.stButton > button[kind="secondary"] {
    background-color: #111420 !important;
    color: #f0f2f7 !important;
    border: 1px solid #1e2235 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background-color: #111420 !important;
    color: #00d26a !important;
    border: 1px solid #00d26a30 !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
}
[data-testid="stDownloadButton"] button:hover { background-color: #00d26a14 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 8px !important; }

/* ── Divider ── */
hr { border-color: #1e2235 !important; }

/* ── Sidebar ── */
.sidebar-user { padding: 14px 0; border-bottom: 1px solid #1e2235; margin-bottom: 16px; }
.sidebar-user-name { font-size: 0.95rem; font-weight: 700; color: #f0f2f7 !important; }
.sidebar-user-email { font-size: 0.78rem; color: #6b7280 !important; margin-top: 2px; }
.sidebar-date { font-size: 0.72rem; color: #4a5068 !important; margin-top: 4px; }

/* ── Login hero panel ── */
.hero-panel {
    background: #0a0c14;
    border-right: 1px solid #1e2235;
    padding: 0;
    min-height: 100vh;
    display: flex; flex-direction: column; justify-content: center;
    position: relative; overflow: hidden;
}
.hero-inner { padding: 60px 52px; position: relative; z-index: 2; }
.hero-logo {
    font-size: 1.4rem; font-weight: 800; color: #f0f2f7;
    letter-spacing: -0.03em; margin-bottom: 64px;
    display: flex; align-items: center; gap: 10px;
}
.hero-logo-mark {
    width: 28px; height: 28px;
    background: #00d26a;
    border-radius: 7px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.85rem; font-weight: 900; color: #0a0c14;
    flex-shrink: 0;
}
.hero-eyebrow {
    font-size: 0.7rem; font-weight: 700; color: #00d26a;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 18px;
    display: flex; align-items: center; gap: 8px;
}
.hero-eyebrow::before {
    content: '';
    display: inline-block; width: 20px; height: 1px; background: #00d26a;
}
.hero-headline {
    font-size: 3.2rem; font-weight: 900; color: #f0f2f7;
    letter-spacing: -0.05em; line-height: 1.05; margin-bottom: 22px;
}
.hero-headline-accent {
    background: linear-gradient(90deg, #00d26a 0%, #00b85a 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-body {
    font-size: 0.98rem; color: #6b7280; line-height: 1.7;
    max-width: 360px; margin-bottom: 44px;
}
/* Stat grid */
.hero-stat-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1px; background: #1e2235;
    border: 1px solid #1e2235; border-radius: 10px; overflow: hidden;
    margin-bottom: 40px;
}
.hero-stat-cell {
    background: #111420;
    padding: 18px 20px;
}
.hero-stat-value {
    font-size: 1.7rem; font-weight: 900; color: #f0f2f7; line-height: 1;
    letter-spacing: -0.04em;
}
.hero-stat-label {
    font-size: 0.68rem; color: #6b7280; margin-top: 5px;
    text-transform: uppercase; letter-spacing: 0.08em;
}
/* Feature pills */
.hero-pills { display: flex; flex-wrap: wrap; gap: 8px; }
.hero-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #111420; border: 1px solid #1e2235;
    border-radius: 100px; padding: 6px 13px;
    font-size: 0.75rem; color: #9ca3af;
}
.hero-pill-dot { width: 5px; height: 5px; background: #00d26a; border-radius: 50%; flex-shrink: 0; }
/* Decorative background grid */
.hero-grid-bg {
    position: absolute; inset: 0; z-index: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 40px 40px;
    mask-image: radial-gradient(ellipse 80% 80% at 50% 0%, black 0%, transparent 70%);
}
/* Glow blobs */
.hero-glow-1 {
    position: absolute; width: 500px; height: 500px;
    background: radial-gradient(circle, #00d26a08 0%, transparent 70%);
    top: -100px; right: -150px; pointer-events: none; z-index: 1;
}
.hero-glow-2 {
    position: absolute; width: 300px; height: 300px;
    background: radial-gradient(circle, #4f6bff06 0%, transparent 70%);
    bottom: 60px; left: -60px; pointer-events: none; z-index: 1;
}

/* ── Auth form panel ── */
.auth-panel {
    padding: 60px 48px;
    display: flex; flex-direction: column; justify-content: center;
    min-height: 100vh;
    background: #0a0c14;
}
.auth-form-title {
    font-size: 1.6rem; font-weight: 800; color: #f0f2f7;
    letter-spacing: -0.03em; margin-bottom: 6px;
}
.auth-form-sub { font-size: 0.88rem; color: #6b7280; margin-bottom: 28px; }

/* ── Dashboard header ── */
.dash-header {
    padding: 28px 0 24px;
    border-bottom: 1px solid #1e2235;
    margin-bottom: 32px;
}
.dash-eyebrow {
    font-size: 0.68rem; font-weight: 700; color: #00d26a;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 8px;
    display: flex; align-items: center; gap: 8px;
}
.dash-eyebrow::before { content: ''; display: inline-block; width: 16px; height: 1px; background: #00d26a; }
.dash-title {
    font-size: 2rem; font-weight: 800; color: #f0f2f7;
    letter-spacing: -0.04em; line-height: 1.1;
}
.dash-subtitle { font-size: 0.9rem; color: #6b7280; margin-top: 6px; }

/* ── JD input area ── */
.jd-input-label {
    font-size: 0.68rem; font-weight: 700; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px;
}

/* ── Upload pill ── */
.upload-pill-row {
    display: flex; align-items: center; gap: 10px;
    background: #0f1117; border: 1px dashed #1e2235;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
}
.upload-pill-icon { font-size: 1rem; }
.upload-pill-text { font-size: 0.82rem; color: #6b7280; }

/* ── Step badge / hint ── */
.step-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 22px; height: 22px;
    background: #00d26a14; color: #00d26a;
    border: 1px solid #00d26a30; border-radius: 5px;
    font-size: 0.68rem; font-weight: 800;
    margin-right: 10px; flex-shrink: 0;
}
.step-row { display: flex; align-items: center; margin-bottom: 4px; }
.step-label { font-size: 0.85rem; font-weight: 600; color: #e5e7eb; }

/* ── Checkboxes ── */
[data-testid="stCheckbox"] span[data-baseweb="checkbox"] > div {
    border-color: #1e2235 !important;
    background-color: #111420 !important;
}
[data-testid="stCheckbox"] input:checked + div,
[data-testid="stCheckbox"] span[data-baseweb="checkbox"] input:checked ~ div {
    background-color: #00d26a !important;
    border-color: #00d26a !important;
}
[data-testid="stCheckbox"] svg { color: #0a0c14 !important; fill: #0a0c14 !important; }
[data-testid="stCheckbox"] p { color: #c8cdd8 !important; font-size: 0.85rem !important; }

/* ── Feedback row card ── */
.feedback-card {
    background: #111420; border: 1px solid #1e2235;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
}
.feedback-card-name { font-size: 0.95rem; font-weight: 700; color: #f0f2f7; }
.feedback-card-sub { font-size: 0.75rem; color: #6b7280; margin-top: 3px; }

/* ── Remove top padding ── */
[data-testid="stMainBlockContainer"] { padding-top: 1rem !important; }
.block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Strip hash fragment (#access_token=...) from URL bar via JS ───────────────
st.components.v1.html(
    "<script>if(window.location.hash && window.location.hash.includes('access_token'))"
    "{ window.history.replaceState(null, '', window.location.pathname); }</script>",
    height=0,
)

# ── Session state init ──────────────────────────────────────────────────────────
_defaults = {
    "username": "",
    "useremail": "",
    "userid": "",
    "signedout": False,
    "signout": False,
    "next_page": "dashboard_page",
    "resumes_text": {},
    "processed_job_json": "",
    "processed_job_text": "",
    "job_description": "",
    "show_results": False,
    "resumes_binary": {},
    "extracted_resumes": "",
    "job_id": None,
    "job_title": "",
    "modifications": [],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Clean URL after Supabase email confirmation ────────────────────────────────
_params = st.query_params.to_dict()
if any(k in _params for k in ("access_token", "refresh_token", "type", "token_hash")):
    st.query_params.clear()
    st.rerun()


# ── Helpers ────────────────────────────────────────────────────────────────────
def clear_session_and_logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def score_color(pct: float) -> str:
    if pct >= 75:
        return "#00d26a"
    if pct >= 50:
        return "#f59e0b"
    return "#ef4444"


def arc_gauge_svg(pct: int, color: str, size: int = 80) -> str:
    """SVG circular arc gauge — 270° arc, clockwise from bottom-left."""
    r = 28
    cx = size // 2
    cy = size // 2
    stroke_w = 5
    circumference = 2 * math.pi * r
    # 270° arc = 75% of full circumference
    arc_full = circumference * 0.75
    arc_fill = arc_full * (pct / 100)
    gap = circumference - arc_fill
    # Rotate so arc starts at 135° (bottom-left) and goes clockwise
    rotation = 135
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 {size} {size}' "
        f"style='transform:rotate({rotation}deg);'>"
        # Track
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' "
        f"stroke='#1e2235' stroke-width='{stroke_w}' "
        f"stroke-dasharray='{arc_full:.2f} {circumference - arc_full:.2f}' "
        f"stroke-linecap='round' />"
        # Fill
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' "
        f"stroke='{color}' stroke-width='{stroke_w}' "
        f"stroke-dasharray='{arc_fill:.2f} {gap:.2f}' "
        f"stroke-linecap='round' "
        f"style='filter:drop-shadow(0 0 6px {color}55);' />"
        # Center text (counter-rotate so text is upright)
        f"<text x='{cx}' y='{cy + 1}' text-anchor='middle' dominant-baseline='middle' "
        f"style='transform:rotate(-{rotation}deg);transform-origin:{cx}px {cy}px;"
        f"font-size:13px;font-weight:800;fill:{color};letter-spacing:-0.04em;'>"
        f"{pct}%</text>"
        f"</svg>"
    )


def progress_bar_html(label: str, score: float) -> str:
    """score is already 0-100 (integer from simple_ranker section scores)."""
    pct = round(score)
    color = score_color(pct)
    return (
        f"<div class='score-row'>"
        f"<span class='score-row-label'>{label}</span>"
        f"<div class='score-bar-bg'>"
        f"<div class='score-bar-fill' style='width:{pct}%;background:{color};'></div>"
        f"</div>"
        f"<span class='score-row-pct' style='color:{color};'>{pct}%</span>"
        f"</div>"
    )


def resume_card_html(rank_label: str, candidate_name: str, filename: str,
                     fit_probability: float, section_scores: dict | None,
                     badge_class: str = "rank-badge",
                     summary: str | None = None,
                     missing_keywords: list | None = None) -> str:
    overall_pct = round(fit_probability * 100)
    color = score_color(overall_pct)
    extra_class = "ranked" if badge_class == "rank-badge" else "unfit-card"
    gauge_svg = arc_gauge_svg(overall_pct, color, size=82)

    bars = ""
    if section_scores:
        label_map = {
            "skills": "Skills",
            "experience": "Experience",
            "education": "Education",
            "projects": "Projects",
        }
        for key, display in label_map.items():
            if key in section_scores:
                bars += progress_bar_html(display, section_scores[key])

    # Summary (italic quote)
    summary_html = ""
    if summary:
        summary_html = f"<div class='card-summary'>\u201c{summary}\u201d</div>"

    # Missing keywords pills
    missing_html = ""
    if missing_keywords:
        pills = "".join(f"<span class='missing-pill'>{kw}</span>" for kw in missing_keywords)
        missing_html = (
            f"<div class='missing-row'>"
            f"<span class='missing-label'>Missing</span>"
            f"{pills}"
            f"</div>"
        )

    section_html = ""
    if bars or summary_html or missing_html:
        section_html = (
            f"<div class='score-section'>"
            f"{bars}"
            f"{summary_html}"
            f"{missing_html}"
            f"</div>"
        )

    return (
        f"<div class='rm-card {extra_class}'>"
        f"<div class='rm-card-inner'>"
        f"<div class='rm-card-header'>"
        f"<div class='rm-card-meta'>"
        f"<div><span class='{badge_class}'>{rank_label}</span></div>"
        f"<div class='rm-card-title'>{candidate_name}</div>"
        f"<div class='rm-card-sub'>{filename}</div>"
        f"</div>"
        f"<div class='gauge-wrap'>"
        f"{gauge_svg}"
        f"<div class='gauge-label'>Overall</div>"
        f"</div>"
        f"</div>"
        f"</div>"
        f"{section_html}"
        f"</div>"
    )


def get_resume_file_by_id(resume_id: str, job_id: str):
    blobs = bucket.list_blobs(prefix=f"resumes/{job_id}/")
    for blob in blobs:
        file_name = blob.name.split("/")[-1]
        if file_name.startswith(f"{resume_id}_"):
            actual_name = file_name.split(f"{resume_id}_", 1)[1]
            return blob.download_as_bytes(), actual_name
    return None, None


def render_sidebar(show_nav: bool = False):
    with st.sidebar:
        st.markdown(
            f"<div class='sidebar-user'>"
            f"<div class='sidebar-user-name'>{st.session_state.username}</div>"
            f"<div class='sidebar-user-email'>{st.session_state.useremail}</div>"
            f"<div class='sidebar-date'>{datetime.date.today().strftime('%B %d, %Y')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", key="signout_btn"):
            clear_session_and_logout()
        if show_nav:
            st.markdown("---")
            if st.button("Go to Results", key="nav_results"):
                st.session_state.next_page = "results_page"
                st.session_state.show_results = True
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state["signedout"]:
    col_hero, col_form = st.columns([1, 1], gap="small")

    with col_hero:
        # NOTE: zero-indentation — markdown treats 4+ leading spaces as code block
        hero_html = (
"<div class='hero-panel'>"
"<div class='hero-grid-bg'></div>"
"<div class='hero-glow-1'></div>"
"<div class='hero-glow-2'></div>"
"<div class='hero-inner'>"
"<div class='hero-logo'><span class='hero-logo-mark'>R</span>ResuMatrix</div>"
"<div class='hero-eyebrow'>AI Resume Screening</div>"
"<div class='hero-headline'>Hire faster.<br>Screen <span class='hero-headline-accent'>smarter.</span></div>"
"<div class='hero-body'>ResuMatrix uses GPT-4o-mini to rank every resume against your job description "
"in seconds — section by section, with full transparency.</div>"
"<div class='hero-stat-grid'>"
"<div class='hero-stat-cell'><div class='hero-stat-value'>4&times;</div><div class='hero-stat-label'>Faster</div></div>"
"<div class='hero-stat-cell'><div class='hero-stat-value'>95%</div><div class='hero-stat-label'>Less bias</div></div>"
"<div class='hero-stat-cell'><div class='hero-stat-value'>&infin;</div><div class='hero-stat-label'>Scale</div></div>"
"</div>"
"<div class='hero-pills'>"
"<span class='hero-pill'><span class='hero-pill-dot'></span>GPT-4o-mini scoring</span>"
"<span class='hero-pill'><span class='hero-pill-dot'></span>Section-level analysis</span>"
"<span class='hero-pill'><span class='hero-pill-dot'></span>Instant ranking</span>"
"<span class='hero-pill'><span class='hero-pill-dot'></span>Feedback loop</span>"
"</div>"
"</div>"
"</div>"
        )
        st.markdown(hero_html, unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='min-height:18vh'></div>", unsafe_allow_html=True)

        choice = st.radio(
            "auth_mode",
            ["Log in", "Create account"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if choice == "Log in":
            st.markdown('<div class="auth-form-title">Welcome back</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-form-sub">Sign in to your ResuMatrix workspace</div>',
                        unsafe_allow_html=True)

            email = st.text_input("Email address", key="login_email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", key="login_password",
                                     placeholder="••••••••")

            if st.button("Log in →", use_container_width=True):
                try:
                    user_info = authenticate_user(email, password)
                    if user_info:
                        st.session_state.username = user_info["username"]
                        st.session_state.useremail = user_info["email"]
                        st.session_state.userid = user_info["id"]
                        st.session_state.signedout = True
                        st.session_state.signout = True
                        st.session_state.next_page = "dashboard_page"
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                except Exception as e:
                    st.warning(f"Login failed: {e}")

        else:
            st.markdown('<div class="auth-form-title">Create your account</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-form-sub">Get started with ResuMatrix for free</div>',
                        unsafe_allow_html=True)

            username = st.text_input("Username", key="signup_username", placeholder="yourname")
            email = st.text_input("Email address", key="signup_email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", key="signup_password",
                                     placeholder="Min. 8 characters")

            if st.button("Create account →", use_container_width=True):
                try:
                    if register_user(email, password, username):
                        st.success("Account created! Switch to Log in above.")
                except Exception as e:
                    st.warning(f"Signup failed: {e}")

        st.markdown(
            "<div style='margin-top:32px;padding-top:20px;border-top:1px solid #1e2235;"
            "font-size:0.75rem;color:#4a5068;text-align:center;'>"
            "By continuing you agree to the ResuMatrix Terms of Service."
            "</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.next_page == "dashboard_page":
    render_sidebar(show_nav=True)

    st.markdown(
        "<div class='dash-header'>"
        "<div class='dash-eyebrow'>Step 1 of 3</div>"
        "<div class='dash-title'>Define the role</div>"
        "<div class='dash-subtitle'>"
        "Paste or upload a job description — our AI will structure it and extract "
        "the requirements used to rank candidates."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_main, col_hint = st.columns([3, 1], gap="large")

    with col_main:
        st.markdown('<div class="jd-input-label">Job Description</div>', unsafe_allow_html=True)
        job_description = st.text_area(
            "jd_input",
            value=st.session_state.get("job_description", ""),
            height=260,
            placeholder="Paste the full job posting here — title, responsibilities, qualifications, skills…",
            label_visibility="collapsed",
        )

        st.markdown(
            "<div class='upload-pill-row'>"
            "<span class='upload-pill-icon'>📎</span>"
            "<span class='upload-pill-text'>Or upload a file (TXT, PDF, DOCX)</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "upload_jd", type=["txt", "pdf", "docx"], label_visibility="collapsed"
        )
        extracted_text = extract_text_from_file(uploaded_file) if uploaded_file else ""
        if extracted_text:
            with st.expander("Preview extracted text"):
                st.text(extracted_text[:1200] + ("…" if len(extracted_text) > 1200 else ""))

        if st.button("Analyse Job Description →", use_container_width=True):
            st.session_state.modifications = []
            final_description = job_description.strip() or extracted_text.strip()
            if final_description:
                st.session_state.job_description = final_description
                with st.spinner("Parsing with LLaMA 3.3…"):
                    try:
                        processed_job_json, processed_job_text = jobPosting_pre_processing(final_description)
                        st.session_state.processed_job_json = processed_job_json
                        st.session_state.processed_job_text = processed_job_text
                        try:
                            jd_data = json.loads(processed_job_json)
                            st.session_state.job_title = jd_data.get("job_title", "")
                        except (json.JSONDecodeError, AttributeError):
                            st.session_state.job_title = ""
                        st.session_state.modified_job_posting = False
                    except json.JSONDecodeError as e:
                        st.error(f"Parse error: {e}")
            else:
                st.error("Please enter or upload a job description.")

    with col_hint:
        # NOTE: zero-indentation — markdown treats 4+ leading spaces as code block
        hint_html = (
"<div style='padding-top:8px;'>"
"<div class='jd-input-label' style='margin-bottom:18px;'>What we extract</div>"
"<div class='step-row'><span class='step-badge'>1</span><span class='step-label'>Job title &amp; company</span></div>"
"<div style='font-size:0.75rem;color:#6b7280;margin:3px 0 14px 32px;'>Used to label the screening run</div>"
"<div class='step-row'><span class='step-badge'>2</span><span class='step-label'>Required skills</span></div>"
"<div style='font-size:0.75rem;color:#6b7280;margin:3px 0 14px 32px;'>Scored against each resume&apos;s skills section</div>"
"<div class='step-row'><span class='step-badge'>3</span><span class='step-label'>Experience level</span></div>"
"<div style='font-size:0.75rem;color:#6b7280;margin:3px 0 14px 32px;'>Years required, seniority, domain</div>"
"<div class='step-row'><span class='step-badge'>4</span><span class='step-label'>Education requirements</span></div>"
"<div style='font-size:0.75rem;color:#6b7280;margin:3px 0 14px 32px;'>Degree, field of study</div>"
"<div class='step-row'><span class='step-badge'>5</span><span class='step-label'>Responsibilities</span></div>"
"<div style='font-size:0.75rem;color:#6b7280;margin:3px 0 14px 32px;'>Project &amp; deliverable context</div>"
"</div>"
        )
        st.markdown(hint_html, unsafe_allow_html=True)

    # ── Review & edit section ─────────────────────────────────────────────────
    if st.session_state.get("processed_job_text"):
        st.markdown("---")

        job_title_display = st.session_state.get("job_title") or "Job"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;"
            f"background:#00d26a0a;border:1px solid #00d26a25;"
            f"border-radius:8px;padding:14px 18px;margin-bottom:20px;'>"
            f"<span style='font-size:1rem;'>✓</span>"
            f"<div>"
            f"<div style='font-size:0.85rem;font-weight:700;color:#00d26a;'>Parsed: {job_title_display}</div>"
            f"<div style='font-size:0.75rem;color:#6b7280;margin-top:2px;'>"
            f"Review and refine below, then proceed to upload resumes.</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        col_review, col_actions = st.columns([3, 1], gap="large")

        with col_review:
            st.markdown('<div class="jd-input-label">Structured job posting</div>', unsafe_allow_html=True)
            st.session_state.processed_text = st.text_area(
                "processed_jd",
                value=st.session_state.processed_job_text,
                height=300,
                label_visibility="collapsed",
            )

        with col_actions:
            st.markdown('<div class="jd-input-label" style="margin-bottom:12px;">Refine</div>',
                        unsafe_allow_html=True)
            new_change = st.text_area(
                "Describe changes:",
                value="",
                height=120,
                placeholder="e.g. Add Python to required skills, remove salary info…",
            )
            if st.button("Regenerate", use_container_width=True):
                if new_change.strip():
                    st.session_state.modifications.append(new_change)
                with st.spinner("Regenerating…"):
                    try:
                        combined = "\n".join(st.session_state.modifications)
                        upd_json, upd_text = jobPosting_pre_processing(
                            st.session_state.processed_text, combined
                        )
                        st.session_state.processed_job_json = upd_json
                        st.session_state.processed_job_text = upd_text
                        st.session_state.job_description = upd_text
                        try:
                            jd_data = json.loads(upd_json)
                            st.session_state.job_title = jd_data.get("job_title", "")
                        except (json.JSONDecodeError, AttributeError):
                            pass
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Error: {e}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Upload Resumes →", use_container_width=True):
            if st.session_state.get("job_description") and st.session_state.get("userid"):
                payload = {
                    "job_text": st.session_state.processed_job_text,
                    "user_id": st.session_state.userid,
                    "job_title": st.session_state.get("job_title") or None,
                }
                resp = requests.post(f"{API_BASE_URL}/jobs/", json=payload)
                if resp.ok:
                    st.session_state.job_id = resp.json()["job"]["id"]
                    st.session_state.next_page = "resume_page"
                    st.rerun()
                else:
                    st.error(f"Failed to save job: {resp.text}")
            else:
                st.error("Missing job description or user session.")


# ══════════════════════════════════════════════════════════════════════════════
# RESUME UPLOAD PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.next_page == "resume_page":
    render_sidebar()

    st.markdown('<div class="page-title">Upload Resumes</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Upload a ZIP file containing PDF resumes.</div>',
                unsafe_allow_html=True)

    uploaded_resume = st.file_uploader("Upload ZIP:", type=["zip"])

    if uploaded_resume:
        zip_bytes = BytesIO(uploaded_resume.getvalue())
        extracted_files = []
        skipped = []

        with zipfile.ZipFile(zip_bytes, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                fname = file_info.filename
                if (file_info.is_dir() or fname.startswith("__MACOSX")
                        or fname.endswith(".DS_Store")
                        or not fname.lower().endswith(".pdf")):
                    skipped.append(fname)
                    continue
                with zip_ref.open(file_info) as f:
                    extracted_files.append((fname, BytesIO(f.read())))

        if skipped:
            st.warning(f"Skipped {len(skipped)} non-PDF / system file(s).")
        if not extracted_files:
            st.error("No PDF files found in the uploaded ZIP.")
        else:
            st.session_state.extracted_resumes = extracted_files
            st.success(f"{len(extracted_files)} PDF resume(s) ready.")

        if st.button("Submit Resumes"):
            if not st.session_state.get("job_id"):
                st.error("Missing job ID. Go back and submit a job description first.")
            elif not st.session_state.get("extracted_resumes"):
                st.error("No resumes extracted yet.")
            else:
                with st.spinner("Uploading and starting ranking..."):
                    files = [
                        ("files", (fname, fobj, "application/octet-stream"))
                        for fname, fobj in st.session_state.extracted_resumes
                    ]
                    try:
                        resp = requests.post(
                            f"{API_BASE_URL}/jobs/{st.session_state.job_id}/resumes",
                            files=files,
                        )
                        if resp.ok:
                            st.session_state.resume_public_urls = resp.json().get("public_urls", [])
                            st.session_state.next_page = "results_page"
                            st.session_state.show_results = True
                            st.rerun()
                        else:
                            st.error(f"Upload failed ({resp.status_code}): {resp.text}")
                    except Exception as e:
                        st.error(f"Upload error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.next_page == "results_page" and st.session_state.show_results:
    render_sidebar()

    st.markdown('<div class="page-title">Screening Results</div>', unsafe_allow_html=True)

    user_id = st.session_state.userid

    # ── Job selector ──────────────────────────────────────────────────────────
    try:
        resp = requests.get(f"{API_BASE_URL}/jobs/?user_id={user_id}")
        if resp.status_code == 200:
            jobs_data = resp.json().get("jobs", [])
            job_options = {}
            for j in jobs_data:
                title = j.get("job_title") or "Untitled Job"
                short_id = str(j["id"])[:8]
                label = f"{title}  —  {short_id}"
                job_options[label] = j["id"]

            current_id = st.session_state.get("job_id")
            current_label = next(
                (lbl for lbl, jid in job_options.items() if jid == current_id),
                list(job_options.keys())[0] if job_options else None,
            )
            selected_label = st.selectbox(
                "Select job:",
                list(job_options.keys()),
                index=list(job_options.keys()).index(current_label) if current_label in job_options else 0,
            )
            selected_id = job_options[selected_label]
            if selected_id != st.session_state.get("job_id"):
                st.session_state.job_id = selected_id
                st.rerun()
    except Exception as e:
        st.error(f"Failed to fetch jobs: {e}")

    job_id = st.session_state.job_id
    job_api = f"{API_BASE_URL}/jobs/{job_id}"
    resumes_api = f"{API_BASE_URL}/jobs/{job_id}/resumes"

    # ── Polling ───────────────────────────────────────────────────────────────
    status_placeholder = st.empty()
    MAX_POLLS = 20  # 20 × 15s = 5 minutes max
    ranking_complete = False

    for poll_attempt in range(MAX_POLLS):
        try:
            job_res = requests.get(job_api)
            resumes_res = requests.get(resumes_api)

            if not job_res.ok or not resumes_res.ok:
                status_placeholder.warning("Polling error — retrying...")
                time.sleep(15)
                continue

            job_data = job_res.json()["job"]
            resumes_data = resumes_res.json()["resumes"]

            if job_data["user_id"] != user_id:
                st.error("Not authorized to view this job.")
                st.stop()

            resume_statuses = [r["status"] for r in resumes_data]
            if all(s not in [-2, 0] for s in resume_statuses) and job_data["status"] == 1:
                ranking_complete = True
                break

        except Exception as e:
            status_placeholder.warning(f"Polling error: {e}")

        status_placeholder.info(
            f"⏳ Ranking in progress... (check {poll_attempt + 1}/{MAX_POLLS})"
        )
        time.sleep(15)

    if not ranking_complete:
        status_placeholder.error(
            "Ranking timed out after 5 minutes. The ranker may still be running — "
            "refresh this page to check."
        )
        st.stop()

    status_placeholder.empty()

    # ── Results rendering ─────────────────────────────────────────────────────
    ranked_resumes = sorted(
        [r for r in resumes_data if r["status"] > 0],
        key=lambda x: x["status"],
    )
    unfit_resumes = [r for r in resumes_data if r["status"] == -1]

    # ── Ranked resumes ────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-heading">Top Candidates &nbsp;·&nbsp; {len(ranked_resumes)} matched</div>',
        unsafe_allow_html=True,
    )

    for resume in ranked_resumes:
        candidate_name = resume.get("candidate_name") or ""
        filename = resume.get("filename") or ""
        if not candidate_name:
            stem = filename.rsplit(".", 1)[0] if filename else resume["id"]
            candidate_name = stem.replace("_", " ").replace("-", " ").title()

        section_scores = None
        raw_scores = resume.get("section_scores")
        if raw_scores:
            try:
                section_scores = json.loads(raw_scores) if isinstance(raw_scores, str) else raw_scores
            except (json.JSONDecodeError, TypeError):
                section_scores = None

        missing_keywords = None
        raw_missing = resume.get("missing_keywords")
        if raw_missing:
            try:
                missing_keywords = json.loads(raw_missing) if isinstance(raw_missing, str) else raw_missing
            except (json.JSONDecodeError, TypeError):
                missing_keywords = None

        rank_num = resume["status"]
        fit_prob = resume.get("fit_probability") or 0.0

        st.markdown(
            resume_card_html(
                rank_label=f"#{rank_num}",
                candidate_name=candidate_name,
                filename=filename,
                fit_probability=fit_prob,
                section_scores=section_scores,
                badge_class="rank-badge",
                summary=resume.get("summary"),
                missing_keywords=missing_keywords,
            ),
            unsafe_allow_html=True,
        )

        resume_bytes, resume_name = get_resume_file_by_id(resume["id"], job_id)
        if resume_bytes:
            st.download_button(
                label="Download PDF",
                data=resume_bytes,
                file_name=resume_name or filename,
                mime="application/pdf",
                key=f"dl_{resume['id']}",
            )
        st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)

    # ── Unfit resumes ─────────────────────────────────────────────────────────
    if unfit_resumes:
        st.markdown(
            f'<div class="section-heading">Not a Match &nbsp;·&nbsp; {len(unfit_resumes)} screened out</div>',
            unsafe_allow_html=True,
        )

        for resume in unfit_resumes:
            candidate_name = resume.get("candidate_name") or ""
            filename = resume.get("filename") or ""
            if not candidate_name:
                stem = filename.rsplit(".", 1)[0] if filename else resume["id"]
                candidate_name = stem.replace("_", " ").replace("-", " ").title()

            section_scores = None
            raw_scores = resume.get("section_scores")
            if raw_scores:
                try:
                    section_scores = json.loads(raw_scores) if isinstance(raw_scores, str) else raw_scores
                except (json.JSONDecodeError, TypeError):
                    section_scores = None

            missing_keywords = None
            raw_missing = resume.get("missing_keywords")
            if raw_missing:
                try:
                    missing_keywords = json.loads(raw_missing) if isinstance(raw_missing, str) else raw_missing
                except (json.JSONDecodeError, TypeError):
                    missing_keywords = None

            fit_prob = resume.get("fit_probability") or 0.0

            st.markdown(
                resume_card_html(
                    rank_label="No Match",
                    candidate_name=candidate_name,
                    filename=filename,
                    fit_probability=fit_prob,
                    section_scores=section_scores,
                    badge_class="unfit-badge",
                    summary=resume.get("summary"),
                    missing_keywords=missing_keywords,
                ),
                unsafe_allow_html=True,
            )

            resume_bytes, resume_name = get_resume_file_by_id(resume["id"], job_id)
            if resume_bytes:
                st.download_button(
                    label="Download PDF",
                    data=resume_bytes,
                    file_name=resume_name or filename,
                    mime="application/pdf",
                    key=f"dl_unfit_{resume['id']}",
                )
            st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("---")
    col_next, col_back = st.columns([1, 1])
    with col_next:
        if st.button("Continue to Feedback →"):
            st.session_state.next_page = "feedback_page"
            st.rerun()
    with col_back:
        if st.button("← New Screening"):
            st.session_state.next_page = "dashboard_page"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.next_page == "feedback_page":
    render_sidebar()

    st.markdown('<div class="page-title">Feedback</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Help us improve — were these results accurate?</div>',
                unsafe_allow_html=True)

    job_id = st.session_state.job_id
    resumes_api = f"{API_BASE_URL}/jobs/{job_id}/resumes"

    try:
        resumes_res = requests.get(resumes_api)
        resumes_data = resumes_res.json()["resumes"]
    except Exception:
        st.error("Could not fetch resumes for feedback.")
        st.stop()

    ranked_resumes = [r for r in resumes_data if r["status"] > 0]
    unfit_resumes = [r for r in resumes_data if r["status"] == -1]

    if "sampled_ranked" not in st.session_state:
        st.session_state.sampled_ranked = random.sample(ranked_resumes, min(3, len(ranked_resumes)))
    if "sampled_unfit" not in st.session_state:
        st.session_state.sampled_unfit = random.sample(unfit_resumes, min(3, len(unfit_resumes)))

    ranked_feedback = {}
    unfit_feedback = {}

    st.markdown('<div class="section-heading">Ranked Resumes — Were these good fits?</div>',
                unsafe_allow_html=True)
    for resume in st.session_state.sampled_ranked:
        candidate_name = resume.get("candidate_name") or resume.get("filename") or resume["id"]
        filename = resume.get("filename") or ""
        fit_pct = round((resume.get("fit_probability") or 0) * 100)
        st.markdown(
            f"<div class='feedback-card'>"
            f"<div class='feedback-card-name'>{candidate_name}</div>"
            f"<div class='feedback-card-sub'>{filename} &nbsp;·&nbsp; {fit_pct}% match</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            ranked_feedback[f"{resume['id']}_fit"] = st.checkbox(
                "Good Fit", key=f"fit_ranked_{resume['id']}"
            )
        with col2:
            ranked_feedback[f"{resume['id']}_no_fit"] = st.checkbox(
                "No Fit", key=f"no_fit_ranked_{resume['id']}"
            )
        st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-heading">Screened-Out Resumes — Were these correctly rejected?</div>',
                unsafe_allow_html=True)
    for resume in st.session_state.sampled_unfit:
        candidate_name = resume.get("candidate_name") or resume.get("filename") or resume["id"]
        filename = resume.get("filename") or ""
        fit_pct = round((resume.get("fit_probability") or 0) * 100)
        st.markdown(
            f"<div class='feedback-card'>"
            f"<div class='feedback-card-name'>{candidate_name}</div>"
            f"<div class='feedback-card-sub'>{filename} &nbsp;·&nbsp; {fit_pct}% match</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            unfit_feedback[f"{resume['id']}_fit"] = st.checkbox(
                "Good Fit", key=f"fit_unfit_{resume['id']}"
            )
        with col2:
            unfit_feedback[f"{resume['id']}_no_fit"] = st.checkbox(
                "No Fit", key=f"no_fit_unfit_{resume['id']}"
            )
        st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    col_submit, col_skip = st.columns([1, 1])

    with col_submit:
        if st.button("Submit Feedback"):
            feedback_payload = []

            def collect_feedback(feedback_dict):
                for k, v in feedback_dict.items():
                    parts = k.split("_", 1)
                    if len(parts) == 2 and v:
                        resume_id, label = parts
                        feedback_payload.append({
                            "id": resume_id,
                            "feedback_label": 1 if label == "fit" else -1,
                        })

            collect_feedback(ranked_feedback)
            collect_feedback(unfit_feedback)

            if feedback_payload:
                try:
                    res = requests.put(resumes_api, json={"resumes": feedback_payload})
                    if res.status_code == 200:
                        st.success("Feedback submitted — thank you!")
                        time.sleep(1)
                        clear_session_and_logout()
                    else:
                        st.error(f"API error {res.status_code}: {res.text}")
                except Exception as e:
                    st.error(f"Failed to submit feedback: {e}")
            else:
                st.warning("No feedback selected.")

    with col_skip:
        if st.button("Skip"):
            clear_session_and_logout()
