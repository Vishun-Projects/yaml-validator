# app.py
"""
Audit Validator - Enterprise Dashboard with Enhanced UI
Modern, responsive Streamlit application with improved UX and visual design
"""

import streamlit as st
import json
import os
import sys
import yaml
import time
import hashlib
import base64
import math
from io import BytesIO
import importlib.util
import html as _html
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Simple CSS for basic layout
st.markdown(
    """
<style>
    /* Basic layout styles */
    .main-container {
        padding: 20px;
    }
    
    .metric-box {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 5px;
        text-align: center;
    }
    
    .status-critical { background: #ff4757; color: white; padding: 4px 8px; border-radius: 4px; }
    .status-high { background: #ffa502; color: white; padding: 4px 8px; border-radius: 4px; }
    .status-medium { background: #ffb142; color: white; padding: 4px 8px; border-radius: 4px; }
    .status-low { background: #2ed573; color: white; padding: 4px 8px; border-radius: 4px; }
    .status-match { background: #3742fa; color: white; padding: 4px 8px; border-radius: 4px; }
    
    .card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .chat-container {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .chat-message {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
    
    .user-message {
        background: #e3f2fd;
        border-color: #2196f3;
    }
    
    .export-modal {
        background: rgba(0, 0, 0, 0.5);
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1000;
    }
    
    .export-modal-content {
        background: #ffffff;
        border-radius: 8px;
        padding: 20px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        min-width: 400px;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# import DB helper (expects db.py in same folder)
try:
    from db import get_db

    db = get_db()
except Exception as e:
    db = None
    st.warning(f"⚠️ Database not available: {e}")
    st.info(
        "💡 The app will work in demo mode without database persistence. To enable full features, run 'python db_setup.py' to set up MySQL database."
    )

# Optional libs
try:
    import plotly.express as px
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors as rl_colors

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    import requests
except Exception:
    requests = None

# -------------------------
DEFAULT_GROQ_KEYS = (
    "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",
    "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",
)
DEFAULT_MODELS = ["llama-3.1-8b-instant"]
# -------------------------

# ---------- Streamlit & session defaults ----------
st.set_page_config(
    page_title="Audit Validator — Enterprise Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://github.com/your-repo/audit-validator",
        "Report a bug": "https://github.com/your-repo/audit-validator/issues",
        "About": "# Audit Validator\nEnterprise-grade configuration validation and compliance monitoring.",
    },
)

# Initialize session state with better defaults
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "validation_result" not in st.session_state:
    st.session_state.validation_result = None
if "last_result_hash" not in st.session_state:
    st.session_state.last_result_hash = ""
if "ai_insights_generated_for" not in st.session_state:
    st.session_state.ai_insights_generated_for = ""
if "groq_last_response" not in st.session_state:
    st.session_state.groq_last_response = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "role" not in st.session_state:
    st.session_state.role = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Executive"
if "refresh_data" not in st.session_state:
    st.session_state.refresh_data = False
if "show_export_modal" not in st.session_state:
    st.session_state.show_export_modal = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------- Helpers / Utilities ----------


def _colors_for_theme(theme):
    if theme == "dark":
        return {
            "bg": "#0f1720",
            "card": "#0f1a24",
            "muted": "#9aa6b2",
            "accent": "#00d27a",
            "donut_match": "#00d27a",
            "donut_mismatch": "#14323a",
            "text_primary": "#e6eef3",
            "trend_alpha": 0.05,
            "match_color": "#00d27a",
        }
    return {
        "bg": "#ffffff",
        "card": "#f0f4f8",
        "muted": "#64748b",
        "accent": "#00b36b",
        "donut_match": "#00b36b",
        "donut_mismatch": "#e6fffa",
        "text_primary": "#1e293b",
        "trend_alpha": 0.12,
        "match_color": "#00b36b",
    }


THEME_COLORS = _colors_for_theme(st.session_state.theme)


def hash_obj(obj) -> str:
    s = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# --- Cached DB reads (invalidate after writes) ---
@st.cache_data
def get_users_cached():
    # Return users from DB if available, otherwise return a demo fallback
    if db:
        try:
            return db.get_users()
        except Exception:
            # fall through to demo users if DB errors
            pass

    return {
        "admin@example.com": {"name": "Admin User", "role": "Administrator"},
        "owner@example.com": {"name": "Owner User", "role": "Owner"},
        "auditor@example.com": {"name": "Auditor User", "role": "Auditor"},
        "viewer@example.com": {"name": "Viewer User", "role": "Viewer"},
    }


@st.cache_data
def get_assignments_cached():
    if db:
        try:
            return db.get_assignments()
        except Exception:
            return {}
    return {}


@st.cache_data
def get_statuses_cached():
    if db:
        try:
            return db.get_statuses()
        except Exception:
            return {}
    return {}


@st.cache_data
def get_slas_cached():
    if db:
        try:
            return db.get_slas()
        except Exception:
            return {}
    return {}


@st.cache_data
def get_ai_logs_cached(limit=200):
    if db:
        try:
            return db.get_ai_logs(limit=limit)
        except Exception:
            return []
    return []


def invalidate_db_caches():
    # clear cached wrappers so UI reflects DB writes
    try:
        get_users_cached.clear()
        get_assignments_cached.clear()
        get_statuses_cached.clear()
        get_slas_cached.clear()
        get_ai_logs_cached.clear()
    except Exception:
        pass


def safe_db_operation(operation, fallback_message="Operation completed (demo mode)"):
    """Safely execute database operations with fallback for demo mode"""
    if db:
        try:
            operation()
            return True
        except Exception as e:
            st.warning(f"Database operation failed: {e}")
            return False
    else:
        st.info(f"💡 {fallback_message}")
        return True


@st.cache_data
def read_uploaded_config_cached(file_bytes: bytes, filename: str):
    import io

    ext = os.path.splitext(filename)[1].lower()
    if ext in [".xlsx", ".xls", ".xlsm"]:
        # openpyxl engine recommended
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str, engine="openpyxl")
        for _, row in df.iterrows():
            if row.notnull().any():
                d = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                return yaml.safe_dump(d, sort_keys=False)
        return ""
    else:
        return file_bytes.decode("utf-8", errors="ignore")


@st.cache_data
def ask_groq_cached(
    prompt_ctx: str,
    model: str,
    keys: tuple,
    system_prompt="You are an expert QA analyst. Produce concise, actionable outputs.",
    max_tokens=700,
    temperature=0.25,
    timeout=18,
):
    if requests is None:
        return "❌ 'requests' not installed. pip install requests"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    last_err = None
    for key in keys:
        try:
            headers["Authorization"] = f"Bearer {key}"
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt_ctx}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text}"
                continue
            data = resp.json()
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message", {}).get("content") or choices[0].get("text")
                if msg:
                    return msg.strip()
        except Exception as e:
            last_err = str(e)
            continue
    return f"❌ AI error: {last_err or 'no response'}"


def progressive_markdown_display(full_md: str, placeholder, chunk_chars=40, delay=0.02):
    if not full_md:
        placeholder.markdown("_No content._")
        return
    if len(full_md) < chunk_chars * 3:
        placeholder.markdown(full_md)
        return
    pos = 0
    while pos < len(full_md):
        pos = min(pos + chunk_chars, len(full_md))
        placeholder.markdown(full_md[:pos])
        time.sleep(delay)
    placeholder.markdown(full_md)


def df_to_colored_html_table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<div class='small-muted'>No rows to display.</div>"
    parts = ["<div class='table-wrap'><table class='custom-table'><thead><tr>"]
    for c in df.columns:
        if c == "Color":
            continue
        parts.append(f"<th>{_html.escape(str(c))}</th>")
    parts.append("</tr></thead><tbody>")
    for _, r in df.iterrows():
        bg = r.get("Color") if pd.notna(r.get("Color")) else ""
        parts.append(f"<tr style='background-color:{bg}'>")
        for c in df.columns:
            if c == "Color":
                continue
            val = r.get(c, "")
            if isinstance(val, (list, dict)):
                val = _html.escape(json.dumps(val, ensure_ascii=False))
            else:
                val = _html.escape(str(val))
            parts.append(f"<td>{val}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def build_exec_pdf_bytes(result_obj, ai_reply_text=None, include_ai=True, org_name="Audit Validator", logo_path=None):
    # If reportlab is unavailable, return a TXT fallback
    title = f"{org_name} — Executive Audit Summary"
    date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    mismatches = [d for d in (result_obj.get("details") or []) if d.get("status") != "match"][:10]
    summary_md = rec_md = ""
    if ai_reply_text and "SUMMARY:" in ai_reply_text:
        parts = ai_reply_text.split("RECOMMENDATIONS:")
        summary_md = parts[0].replace("SUMMARY:", "").strip()
        if len(parts) > 1:
            rec_explan = parts[1].split("ENHANCED_EXPLANATIONS:")
            rec_md = rec_explan[0].strip()
    elif ai_reply_text:
        summary_md = ai_reply_text

    if REPORTLAB_AVAILABLE:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []
        if logo_path and os.path.exists(logo_path):
            try:
                story.append(Image(logo_path, width=100, height=40))
                story.append(Spacer(1, 8))
            except Exception:
                pass
        story.append(Paragraph(title, styles["Title"]))
        story.append(Paragraph(f"Generated: {date_str}", styles["Normal"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Overall Match:</b> {result_obj.get('match_percentage','N/A')}%", styles["Heading3"]))
        story.append(Paragraph(f"<b>Total Checks:</b> {len(result_obj.get('details', []))}", styles["Normal"]))
        story.append(Spacer(1, 8))
        if mismatches:
            story.append(Paragraph("<b>Top Findings</b>", styles["Heading3"]))
            table_data = [["Key", "Status", "Severity", "Explanation", "Owner", "SLA"]]
            for t in mismatches:
                owner = get_assignments_cached().get(t.get("key"), "Unassigned")
                sla = get_slas_cached().get(t.get("key"), "")
                table_data.append([str(t.get("key", "")), str(t.get("status", "")), str(t.get("severity", "")), str(t.get("explanation", "")), owner, str(sla)])
            tbl = Table(table_data, colWidths=[120, 60, 60, 180, 80, 80])
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#e8e8e8")),
                        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(tbl)
            story.append(Spacer(1, 8))
        if include_ai and summary_md:
            story.append(Paragraph("<b>AI Summary</b>", styles["Heading3"]))
            for line in summary_md.split("\n"):
                story.append(Paragraph(_html.escape(line), styles["Normal"]))
            story.append(Spacer(1, 8))
        if include_ai and rec_md:
            story.append(Paragraph("<b>AI Recommendations</b>", styles["Heading3"]))
            for line in rec_md.split("\n"):
                story.append(Paragraph(_html.escape(line), styles["Normal"]))
            story.append(Spacer(1, 8))
        story.append(Paragraph("Generated by Audit Validator", styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        return buffer.read(), "application/pdf", "executive_summary.pdf"
    else:
        lines = [
            title,
            f"Generated: {date_str}",
            f"Overall Match: {result_obj.get('match_percentage','N/A')}%",
            f"Total Checks: {len(result_obj.get('details', []))}",
            "",
            "Top Findings:",
        ]
        for t in mismatches:
            owner = get_assignments_cached().get(t.get("key"), "Unassigned")
            sla = get_slas_cached().get(t.get("key"), "")
            lines.append(f"- {t.get('key')} | {t.get('status')} | {t.get('severity')} | Owner: {owner} | SLA: {sla} | {t.get('explanation')}")
        if include_ai and summary_md:
            lines += ["", "AI Summary:", summary_md]
        if include_ai and rec_md:
            lines += ["", "AI Recommendations:", rec_md]
        return ("\n".join(lines)).encode("utf-8"), "text/plain", "executive_summary.txt"


# --- Dynamic ai_audit_gui import or fallback ---
ai_module_path = os.path.join(os.path.dirname(__file__), "..", "ai_audit_gui.py")
if os.path.exists(ai_module_path):
    spec = importlib.util.spec_from_file_location("ai_audit_gui", ai_module_path)
    ai_audit_gui = importlib.util.module_from_spec(spec)
    sys.modules["ai_audit_gui"] = ai_audit_gui
    spec.loader.exec_module(ai_audit_gui)
else:

    class _FakeAI:
        @staticmethod
        def collect_full_snapshot(interactive_ui=False, collect_apps_flag=False):
            return {"device": "demo-device", "collected": True, "collected_at": datetime.utcnow().isoformat()}

        @staticmethod
        def collect_generic_snapshot():
            return {"device": "generic-demo"}

        @staticmethod
        def validate_against_yaml(cfg, snap):
            now = datetime.utcnow()
            return {
                "match_percentage": 73,
                "details": [
                    {"key": "ssh.password_auth", "expected": "no", "actual": "yes", "status": "mismatch", "severity": "critical", "explanation": "Password auth enabled", "first_seen": (now - timedelta(days=5)).isoformat()},
                    {"key": "tls.expiry", "expected": ">30d", "actual": "10d", "status": "mismatch", "severity": "high", "explanation": "Certificate expires soon", "first_seen": (now - timedelta(days=12)).isoformat()},
                    {"key": "ntp.server", "expected": "ntp.example.com", "actual": "pool.ntp.org", "status": "partial", "severity": "medium", "explanation": "NTP different", "first_seen": (now - timedelta(days=2)).isoformat()},
                    {"key": "device.hostname", "expected": "prod-router", "actual": "prod-router", "status": "match", "severity": "low", "explanation": "OK", "first_seen": (now - timedelta(days=60)).isoformat()},
                ],
            }


    ai_audit_gui = _FakeAI()

# ---------- UI: layout and components ----------
# Two-pane layout matching the image structure

# Add CSS for the layout
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Main container */
    .main .block-container {
        max-width: 100vw !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Two-pane layout */
    .two-pane-container {
        display: flex;
        height: 100vh;
        background: #f8f9fa;
    }
    
    /* Left pane - narrower */
    .left-pane {
        width: 400px;
        background: white;
        padding: 30px;
        border-right: 1px solid #e0e0e0;
        overflow-y: auto;
    }
    
    /* Right pane - wider */
    .right-pane {
        flex: 1;
        background: white;
        padding: 30px;
        display: flex;
        flex-direction: column;
    }
    
    /* Upload sections */
    .upload-section {
        margin-bottom: 30px;
        padding: 20px;
        border: 2px dashed #ddd;
        border-radius: 8px;
        background: #fafafa;
        text-align: center;
    }
    
    .upload-section:hover {
        border-color: #ff6b35;
        background: #fff5f2;
    }
    
    /* Buttons */
    .stButton > button {
        background: #ff6b35 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
    }
    
    .stButton > button:hover {
        background: #e55a2b !important;
    }
    
    /* Chat container */
    .chat-container {
        flex: 1;
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    
    /* Chat input */
    .chat-input-container {
        display: flex;
        align-items: center;
        gap: 10px;
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 25px;
        padding: 15px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f0f0 !important;
        border-radius: 20px !important;
        color: #666 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #ff6b35 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Create the two-pane layout
st.markdown('<div class="two-pane-container">', unsafe_allow_html=True)

# LEFT PANE
st.markdown('<div class="left-pane">', unsafe_allow_html=True)

# Header
st.markdown('<h1 style="color: #ff6b35; font-size: 24px; font-weight: 700; margin-bottom: 5px;">Audit Validator</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #666; font-size: 16px; margin-bottom: 30px;">Configuration Validation Tool</p>', unsafe_allow_html=True)

# Upload Logo Section
st.markdown('<h3 style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px;">Upload Logo</h3>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 14px; color: #666; margin-bottom: 15px;">Please upload file in jpeg or png format and make sure the file size is under 25 MB.</p>', unsafe_allow_html=True)

st.markdown('<div class="upload-section">', unsafe_allow_html=True)
st.markdown('<div style="font-size: 24px; color: #666; margin-bottom: 10px;">☁️</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 16px; color: #666; margin-bottom: 5px;">Drop file or browse</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 12px; color: #999;">Format: .jpeg, .png & Max file size: 25 MB</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

logo_upload = st.file_uploader("", type=["jpeg", "jpg", "png"], key="logo_upload", label_visibility="collapsed")

    col1, col2 = st.columns([1, 1])
    with col1:
    if st.button("Browse Files", key="browse_logo"):
        pass

# Upload Config Section
st.markdown('<h3 style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px;">Upload Config</h3>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 14px; color: #666; margin-bottom: 15px;">Please upload files in pdf, docx or doc format and make sure the file size is under 25 MB.</p>', unsafe_allow_html=True)

st.markdown('<div class="upload-section">', unsafe_allow_html=True)
st.markdown('<div style="font-size: 16px; color: #666; margin-bottom: 5px;">Drop file or Browse</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 12px; color: #999;">Format: pdf, docx, doc & Max file size: 25 MB</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

cfg_upload = st.file_uploader("", type=["pdf", "docx", "doc", "xlsx", "xls", "yaml", "yml"], key="cfg_upload", label_visibility="collapsed")

    col3, col4 = st.columns([1, 1])
    with col3:
    if st.button("Cancel", key="cancel_config"):
        pass
    with col4:
    if st.button("Done", key="done_config"):
        pass

# Upload Snapshot Section
st.markdown('<h3 style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px;">Upload Snapshot</h3>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 14px; color: #666; margin-bottom: 15px;">Please upload files in pdf, docx or doc format and make sure the file size is under 25 MB.</p>', unsafe_allow_html=True)

st.markdown('<div class="upload-section">', unsafe_allow_html=True)
st.markdown('<div style="font-size: 16px; color: #666; margin-bottom: 5px;">Drop file or Browse</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 12px; color: #999;">Format: pdf, docx, doc & Max file size: 25 MB</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

snap_upload = st.file_uploader("", type=["json"], key="snap_upload", label_visibility="collapsed")

col5, col6 = st.columns([1, 1])
with col5:
    if st.button("Cancel", key="cancel_snap"):
        pass
with col6:
    if st.button("Done", key="done_snap"):
        pass

# Run Validation Button
st.markdown('<div style="margin-top: 30px;">', unsafe_allow_html=True)
run_now = st.button("Run Validation", key="run_validation", type="primary")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # End left pane

# RIGHT PANE
st.markdown('<div class="right-pane">', unsafe_allow_html=True)

# Header with robot icon and tabs
col7, col8, col9 = st.columns([1, 2, 1])
with col7:
    st.markdown('<div style="display: flex; align-items: center; gap: 10px;">', unsafe_allow_html=True)
    st.markdown('<span style="font-size: 20px; color: #20c997;">🤖</span>', unsafe_allow_html=True)
    st.markdown('<span style="font-size: 18px; font-weight: 600; color: #333;">Configure Validator</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col8:
    tab1, tab2 = st.tabs(["Executive", "Details"])

with col9:
    if st.button("📤 Export", key="export_btn"):
        st.session_state.show_export_modal = True

# Main content area
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown('<div style="font-size: 60px; color: #ddd; margin-bottom: 20px;">💬</div>', unsafe_allow_html=True)
st.markdown('<h2 style="font-size: 24px; font-weight: 600; color: #333; margin-bottom: 10px;">Smart AI Helper</h2>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 16px; color: #666; line-height: 1.5; max-width: 400px;">Always-on assistant offering instant answers, clear insights, and actionable recommendations.</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Chat input at bottom
st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
st.markdown('<span style="color: #666;">📎</span>', unsafe_allow_html=True)
user_question = st.text_input("", placeholder="Message slothGPT...", key="chat_input", label_visibility="collapsed")
if st.button("↑", key="send_chat"):
    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        # Generate AI response
        if st.session_state.validation_result:
            details = st.session_state.validation_result.get("details", []) or []
            match_pct = st.session_state.validation_result.get("match_percentage", 0)
            
            context = f"""
            Current validation results:
            - Match Percentage: {match_pct}%
            - Total Findings: {len(details)}
            - Critical Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')}
            - High Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'high')}
            - Medium Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'medium')}
            - Low Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'low')}
            
            All findings: {chr(10).join([f"- {d.get('key')}: {d.get('explanation', '')}" for d in details])}
            """
            
            prompt = f"""
            You are an IT security expert helping analyze configuration validation results.
            
            {context}
            
            User question: {user_question}
            
            Provide a concise, helpful answer based on the validation results. Be specific and actionable.
            """
            
            try:
                response = ask_groq_cached(
                    prompt,
                    DEFAULT_MODELS[0],
                    DEFAULT_GROQ_KEYS,
                    system_prompt="You are an expert IT security analyst. Provide concise, actionable insights.",
                    max_tokens=300,
                    temperature=0.3,
                    timeout=18,
                )
                st.session_state.chat_history.append({"role": "assistant", "content": response})
    except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"Sorry, I couldn't process that: {str(e)}"})
    else:
                st.session_state.chat_history.append({"role": "assistant", "content": "Please run a validation first to analyze results."})
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # End right pane

st.markdown('</div>', unsafe_allow_html=True)  # End two-pane container

# Tab content (hidden but functional)
with tab1:
    # Executive Tab Content
    result = st.session_state.get("validation_result")
    if result:
        st.markdown('<h3 style="margin-bottom: 20px; color: #333;">Executive Summary</h3>', unsafe_allow_html=True)
        
        match_pct = int(result.get("match_percentage", 0))
        details = result.get("details", []) or []

        # Simple metrics
        col10, col11, col12, col13 = st.columns(4)
        with col10:
            st.metric("Match %", f"{match_pct}%")
        with col11:
            st.metric("Total Checks", len(details))
        with col12:
            critical_count = sum(1 for d in details if d.get("severity") and str(d.get("severity")).lower() == "critical")
            st.metric("Critical", critical_count)
        with col13:
            statuses = get_statuses_cached() if db else {}
            open_count = sum(1 for d in details if statuses.get(d.get("key")) != "resolved")
            st.metric("Open Issues", open_count)

        # Key findings table
        st.markdown('<h4 style="margin: 20px 0 15px 0; color: #333;">Key Findings</h4>', unsafe_allow_html=True)
        if details:
            findings_data = []
            for d in details[:5]:
                explanation = d.get("explanation", "") or ""
                findings_data.append(
                    {
                        "Key": d.get("key", ""),
                        "Status": d.get("status", ""),
                        "Severity": d.get("severity", ""),
                        "Explanation": explanation[:50] + "..." if len(explanation) > 50 else explanation,
                    }
                )

            df_findings = pd.DataFrame(findings_data)
            st.dataframe(df_findings, use_container_width=True)
        else:
            st.info("No findings to display.")

with tab2:
    # Details Tab Content
    result = st.session_state.get("validation_result")
    if not result:
        st.info("Run validation to see detailed results.")
    else:
        details = result.get("details", []) or []
        match_pct = int(result.get("match_percentage", 0))

        st.markdown('<h3 style="margin-bottom: 20px; color: #333;">Detailed Analysis</h3>', unsafe_allow_html=True)
        
        # Summary metrics
        col14, col15, col16, col17 = st.columns(4)
        with col14:
            st.metric("Overall Match", f"{match_pct}%")
        with col15:
            critical_count = sum(1 for d in details if d.get("severity") and str(d.get("severity")).lower() == "critical")
            st.metric("Critical", critical_count)
        with col16:
            high_count = sum(1 for d in details if d.get("severity") and str(d.get("severity")).lower() == "high")
            st.metric("High", high_count)
        with col17:
            medium_count = sum(1 for d in details if d.get("severity") and str(d.get("severity")).lower() in ["medium", "partial"])
            st.metric("Medium", medium_count)

        # Charts section
        if details and PLOTLY_AVAILABLE:
            st.markdown('<h4 style="margin: 20px 0 15px 0; color: #333;">Severity Distribution</h4>', unsafe_allow_html=True)
            
            # Severity pie chart
            severity_counts = {}
            for d in details:
                sev = str(d.get("severity", "")).lower()
                if sev in ["critical", "high", "medium", "partial", "low", "match"]:
                    if sev == "partial":
                        sev = "medium"
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            if severity_counts:
                fig = go.Figure(data=[go.Pie(
                    labels=list(severity_counts.keys()),
                    values=list(severity_counts.values()),
                    hole=0.4,
                    marker_colors=['#ff4757', '#ffa502', '#ffb142', '#2ed573', '#3742fa']
                )])
                fig.update_layout(
                    height=300,
                    showlegend=True,
                    title="Distribution by Severity Level"
                )
                st.plotly_chart(fig, use_container_width=True)

        # Detailed findings table
        st.markdown('<h4 style="margin: 20px 0 15px 0; color: #333;">All Findings</h4>', unsafe_allow_html=True)

        # Filters
        col18, col19 = st.columns([2, 1])
        with col18:
            search_term = st.text_input("Search findings", placeholder="Search by key or explanation...", key="search_details")
        with col19:
            severity_values = list({str(d.get("severity", "")).title() for d in details})
            severity_filter = st.selectbox("Filter by severity", ["All"] + sorted(severity_values), key="severity_filter")

        # Filter the data
        filtered_details = details
        if search_term:
            filtered_details = [
                d
                for d in filtered_details
                if search_term.lower() in str(d.get("key", "")).lower() or search_term.lower() in str(d.get("explanation", "")).lower()
            ]
        if severity_filter != "All":
            filtered_details = [d for d in filtered_details if str(d.get("severity", "")).title() == severity_filter]

        # Display results
        if filtered_details:
            st.info(f"Showing {len(filtered_details)} of {len(details)} findings")

            display_data = []
            for d in filtered_details[:10]:
                explanation = d.get("explanation", "") or ""
                display_data.append(
                    {
                        "Key": d.get("key", ""),
                        "Status": d.get("status", ""),
                        "Severity": d.get("severity", ""),
                        "Explanation": explanation[:100] + "..." if len(explanation) > 100 else explanation,
                        "First Seen": d.get("first_seen", "N/A")[:10] if d.get("first_seen") else "N/A",
                    }
                )

            df_display = pd.DataFrame(display_data)
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No findings match the current filters.")

# Run validation logic
if run_now:
    # collect snapshot
    try:
        if snap_upload:
            snapshot = yaml.safe_load(snap_upload.getvalue())
    else:
            snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=False, collect_apps_flag=False)
    except Exception as e:
        st.error(f"Snapshot collection failed: {e}")
        st.stop()

    # config
        if cfg_upload:
        config_yaml = read_uploaded_config_cached(cfg_upload.getvalue(), cfg_upload.name)
            else:
        # fallback: look for monika/ YAML
        possible = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monika")
        if os.path.isdir(possible):
            found = False
            for fname in os.listdir(possible):
                if fname.lower().endswith((".yml", ".yaml")):
                    with open(os.path.join(possible, fname), "r", encoding="utf-8") as fh:
                        config_yaml = fh.read()
                    found = True
                    break
            if not found:
                st.error("No YAML config found in monika/. Please upload.")
                st.stop()
        else:
            st.error("No config provided. Upload a config file.")
            st.stop()

    # validate
    with st.spinner("Running validation..."):
        result = ai_audit_gui.validate_against_yaml(config_yaml, snapshot)
        st.session_state.validation_result = result
        st.session_state.last_result_hash = hash_obj(result)
        # initialize DB entries for new results (only create if missing)
        if db:
            try:
                existing_assignments = get_assignments_cached()
                existing_statuses = get_statuses_cached()
                existing_slas = get_slas_cached()
                for d in (result.get("details") or []):
                    k = d.get("key")
                    if k not in existing_assignments:
                        db.set_assignment(k, "Unassigned")
                    if k not in existing_statuses:
                        db.set_status(k, "open")
                    if k not in existing_slas:
                        first_seen = d.get("first_seen")
                        try:
                            fs = datetime.fromisoformat(first_seen) if first_seen else datetime.utcnow()
                        except Exception:
                            fs = datetime.utcnow()
                        db.set_sla(k, (fs + timedelta(days=7)).isoformat())
                invalidate_db_caches()
            except Exception:
                pass  # Silently fail if DB initialization fails
        
        st.success("Validation complete!")
                    st.rerun()

# ---------- Export Modal ----------
if st.session_state.show_export_modal:
    st.markdown('<div class="export-modal">', unsafe_allow_html=True)
    st.markdown('<div class="export-modal-content">', unsafe_allow_html=True)
    
    st.subheader("Export Options")

    result = st.session_state.get("validation_result")
    if not result:
        st.warning("No validation results to export. Please run validation first.")
        if st.button("Close", key="close_modal"):
            st.session_state.show_export_modal = False
            st.rerun()
    else:
        # Export options
        export_type = st.selectbox(
            "Select export type:",
            ["JSON Report", "CSV Findings", "Executive PDF"],
            key="export_type"
        )
        
        include_ai = st.checkbox("Include AI insights", value=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download", key="download_export"):
                if export_type == "JSON Report":
            json_bytes = json.dumps(result, indent=2).encode("utf-8")
                    st.download_button(
                        "Download JSON",
                        data=json_bytes,
                        file_name="validation_report.json",
                        mime="application/json",
                        key="json_download"
                    )
                elif export_type == "CSV Findings":
            details_df = pd.DataFrame(result.get("details", []))
            if not details_df.empty:
                csv_bytes = details_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download CSV",
                            data=csv_bytes,
                            file_name="findings.csv",
                            mime="text/csv",
                            key="csv_download"
                        )
                elif export_type == "Executive PDF":
                    ai_txt = st.session_state.get("groq_last_response", "")
                    pdf_bytes, mime, fname = build_exec_pdf_bytes(result, ai_reply_text=ai_txt, include_ai=include_ai)
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name=fname,
                        mime=mime,
                        key="pdf_download"
                    )

        with col2:
            if st.button("Cancel", key="cancel_export"):
                st.session_state.show_export_modal = False
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Footer ----------
st.divider()
st.caption("Word Publishing - Yaml Validator")
