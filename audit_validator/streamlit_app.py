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

# Simple, clean CSS
st.markdown(
    """
<style>
    /* Simple, clean design */
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
    
    .simple-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
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
    initial_sidebar_state="expanded",
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
# Simple sidebar
with st.sidebar:
    st.title("WP Yaml Validator")
    st.caption("Configuration Validation Tool")

    # User selection
    users = get_users_cached() if db else get_users_cached()
    user_emails = list(users.keys()) if users else ["admin@example.com", "owner@example.com", "auditor@example.com", "viewer@example.com"]

    if st.session_state.user_email:
        st.success(f"Signed in as {st.session_state.user_email}")
        if st.button("Sign Out"):
            st.session_state.user_email = None
            st.session_state.role = None
            st.rerun()
    else:
        selected_user = st.selectbox("Select User", options=user_emails, index=0)
        if st.button("Sign In"):
            st.session_state.user_email = selected_user
            st.session_state.role = users.get(selected_user, {}).get("role", "Viewer")
            st.rerun()

    st.divider()

    # Logo upload (optional)
    logo_file = st.file_uploader("Upload Logo (optional)", type=["png", "jpg", "jpeg"])
    logo_path = None
    if logo_file:
        logo_path = os.path.join(os.path.dirname(__file__), "uploaded_logo.png")
        with open(logo_path, "wb") as fh:
            fh.write(logo_file.getvalue())

    st.divider()
    st.caption("Word Publishing - Yaml Validator")

# Main tabs
tab_summary, tab_details, tab_ai, tab_downloads = st.tabs(
    [
        "📊 Executive",
        "🔍 Details",
        "🤖 AI Chat",
        "⬇️ Exports",
    ]
)

# ---------- Run Validation action ----------
with tab_summary:
    st.header("Configuration Validation")

    # File upload section
    col1, col2 = st.columns([1, 1])
    with col1:
        cfg_upload = st.file_uploader("Upload Config", type=["xlsx", "xls", "yaml", "yml"], key="cfg_main")
    with col2:
        snap_upload = st.file_uploader("Upload Snapshot", type=["json"], key="snap_main")

    # Device ID and Run button
    col3, col4 = st.columns([1, 1])
    with col3:
        device_id_in = st.text_input("Device ID (optional)", value="", placeholder="device-123")
    with col4:
        run_now = st.button("Run Validation", type="primary")
        if st.session_state.validation_result and st.button("Re-run"):
            st.session_state.validation_result = None
            st.rerun()

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
        st.success("Validation complete. View Executive & Details tabs.")

# ---------- Executive Tab render ----------
with tab_summary:
    result = st.session_state.get("validation_result")
    if not result:
        st.info("Run validation to see results.")
    else:
        match_pct = int(result.get("match_percentage", 0))
        details = result.get("details", []) or []

        # Simple metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Match %", f"{match_pct}%")
        with col2:
            st.metric("Total Checks", len(details))
        with col3:
            critical_count = sum(1 for d in details if d.get("severity") and str(d.get("severity")).lower() == "critical")
            st.metric("Critical", critical_count)
        with col4:
            statuses = get_statuses_cached() if db else {}
            open_count = sum(1 for d in details if statuses.get(d.get("key")) != "resolved")
            st.metric("Open Issues", open_count)

        st.markdown("---")
        # Simple findings table
        st.subheader("Key Findings")

        if details:
            # Create simple table
            findings_data = []
            for d in details[:10]:  # Show top 10
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

        st.markdown("---")
        # Enhanced heatmap section
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown('<h3 style="color: #2c3e50; margin: 0 0 15px 0;">🔥 Severity Heatmap</h3>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        cats = {}
        for d in details:
            key = d.get("key", "")
            cat = key.split(".")[0] if "." in key else key
            sev = d.get("severity", "unknown")
            cats.setdefault(cat, []).append(sev)

        heat = []
        for cat, sevs in cats.items():
            row = {
                "category": cat,
                "critical": sum(1 for s in sevs if str(s).lower() == "critical"),
                "high": sum(1 for s in sevs if str(s).lower() == "high"),
                "medium": sum(1 for s in sevs if str(s).lower() == "medium" or str(s).lower() == "partial"),
                "low": sum(1 for s in sevs if str(s).lower() == "low" or str(s).lower() == "match"),
            }
            heat.append(row)

        if heat:
            df_heat = pd.DataFrame(heat).set_index("category")
            if PLOTLY_AVAILABLE:
                # Enhanced heatmap with better colors
                fig = px.imshow(
                    df_heat.fillna(0).T,
                    labels=dict(x="Category", y="Severity", color="Count"),
                    x=df_heat.index,
                    y=df_heat.columns[::-1],
                    color_continuous_scale="RdYlGn_r",
                )
                fig.update_layout(height=300, margin=dict(t=20, b=10, l=10, r=10), title="Issue Distribution by Category and Severity")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown('<div class="data-table">', unsafe_allow_html=True)
                st.dataframe(df_heat, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
            st.markdown('<p style="text-align: center; color: #7f8c8d;">No categorical data available for heatmap</p>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ---------- DETAILS TAB ----------
with tab_details:
    result = st.session_state.get("validation_result")
    if not result:
        st.info("Run validation to see detailed results.")
    else:
        details = result.get("details", []) or []

        st.subheader("Detailed Findings")

        # Simple filters
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("Search", placeholder="Search findings...")
        with col2:
            severity_values = list({str(d.get("severity", "")).title() for d in details})
            severity_filter = st.selectbox("Severity", ["All"] + sorted(severity_values))

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
            st.write(f"Showing {len(filtered_details)} of {len(details)} findings")

            # Simple table
            display_data = []
            for d in filtered_details:
                explanation = d.get("explanation", "") or ""
                display_data.append(
                    {
                        "Key": d.get("key", ""),
                        "Status": d.get("status", ""),
                        "Severity": d.get("severity", ""),
                        "Explanation": explanation[:100] + "..." if len(explanation) > 100 else explanation,
                    }
                )

            df_display = pd.DataFrame(display_data)
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No findings match the current filters.")

# ---------- AI INSIGHTS TAB ----------
with tab_ai:
    result = st.session_state.get("validation_result")
    if not result:
        st.info("Run validation to chat with AI about your results.")
    else:
        st.subheader("AI Chat Assistant")

        # Initialize chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Display chat history
        st.write("**Chat History:**")
        for i, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message"><strong>AI:</strong> {message["content"]}</div>', unsafe_allow_html=True)

        # Generate initial summary if not done
        if not st.session_state.chat_history:
            with st.spinner("Analyzing your results..."):
                try:
                    details = result.get("details", []) or []
                    match_pct = result.get("match_percentage", 0)

                    context = f"""
                    Validation Results Analysis:
                    - Overall Match Percentage: {match_pct}%
                    - Total Findings: {len(details)}
                    - Critical Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')}
                    - High Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'high')}
                    - Medium Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'medium')}
                    - Low Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'low')}
                    
                    Key findings details:
                    {chr(10).join([f"- {d.get('key')}: {d.get('explanation', '')}" for d in details[:5]])}
                    """

                    prompt = f"""
                    You are an IT security and compliance expert. Provide a comprehensive analysis of these configuration validation results.
                    
                    {context}
                    
                    Please provide:
                    1. **Executive Summary** (2-3 sentences on overall status)
                    2. **Risk Assessment** (Low/Medium/High based on findings)
                    3. **Top 3 Priority Issues** that need attention
                    4. **Compliance Impact** (if any regulatory concerns)
                    5. **Recommended Next Steps** (3-5 actionable items)
                    
                    Be detailed, professional, and provide specific insights that would be valuable for both technical and executive audiences.
                    """

                    response = ask_groq_cached(
                        prompt,
                        DEFAULT_MODELS[0],
                        DEFAULT_GROQ_KEYS,
                        system_prompt="You are an expert IT security analyst. Provide detailed, actionable insights.",
                        max_tokens=500,
                        temperature=0.3,
                        timeout=18,
                    )

                    ai_response = response
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})

                except Exception as e:
                    st.error(f"AI analysis failed: {e}")
                    st.session_state.chat_history.append({"role": "assistant", "content": "I'm here to help analyze your validation results. What would you like to know about your findings?"})

        # Chat input
        st.write("**Ask a Question:**")
        user_question = st.text_input("", placeholder="e.g., What are the most critical issues? How can I improve compliance?")

        if user_question and st.button("Send Question"):
            st.session_state.chat_history.append({"role": "user", "content": user_question})

            with st.spinner("Analyzing..."):
                try:
                    details = result.get("details", []) or []
                    match_pct = result.get("match_percentage", 0)

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
                    
                    Provide a detailed, helpful answer based on the validation results. Be specific, actionable, and professional. 
                    If the question is about specific issues, provide detailed explanations and recommendations.
                    If it's about compliance, explain the regulatory implications.
                    If it's about remediation, provide step-by-step guidance.
                    """

                    response = ask_groq_cached(
                        prompt,
                        DEFAULT_MODELS[0],
                        DEFAULT_GROQ_KEYS,
                        system_prompt="You are an expert IT security analyst. Provide detailed, actionable insights.",
                        max_tokens=400,
                        temperature=0.3,
                        timeout=18,
                    )

                    ai_response = response
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    st.rerun()

                except Exception as e:
                    st.error(f"Sorry, I couldn't process that question: {e}")

        # Clear chat button
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

# ---------- DOWNLOADS / EXPORTS TAB ----------
with tab_downloads:
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.markdown('<h2 style="color: #2c3e50; margin: 0 0 15px 0;">⬇️ Exports & Reports</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: #7f8c8d; margin: 0;">Generate and download comprehensive reports in various formats</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("validation_result")
    if not result:
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; padding: 40px;">', unsafe_allow_html=True)
        st.markdown('<h3 style="color: #7f8c8d; margin: 0;">📊 Export & Reports</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color: #95a5a6; margin: 10px 0;">Run validation to enable report generation and exports</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Export options in cards
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin: 0 0 15px 0; color: #2c3e50;">📄 Data Exports</h4>', unsafe_allow_html=True)

            # JSON export
            json_bytes = json.dumps(result, indent=2).encode("utf-8")
            st.download_button("📋 Download Validation (JSON)", data=json_bytes, file_name="validation_report.json", mime="application/json", use_container_width=True)

            # CSV export
            details_df = pd.DataFrame(result.get("details", []))
            if not details_df.empty:
                csv_bytes = details_df.to_csv(index=False).encode("utf-8")
                st.download_button("📊 Download Findings (CSV)", data=csv_bytes, file_name="findings.csv", mime="text/csv", use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin: 0 0 15px 0; color: #2c3e50;">📋 Executive Reports</h4>', unsafe_allow_html=True)

            include_ai = st.checkbox("Include AI insights", value=True, help="Include AI-generated insights in the executive report")
            ai_txt = st.session_state.get("groq_last_response", "")
            pdf_bytes, mime, fname = build_exec_pdf_bytes(result, ai_reply_text=ai_txt, include_ai=include_ai, logo_path=logo_path)

            st.download_button("📄 Download Executive Report", data=pdf_bytes, file_name=fname, mime=mime, use_container_width=True)

            st.markdown('<p style="color: #7f8c8d; margin: 10px 0; font-size: 12px;">Format: PDF (or TXT if PDF generation unavailable)</p>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ---------- Footer ----------
st.divider()
st.caption("Word Publishing - Yaml Validator")
