"""
Forex Rate Extractor - Main Application

Orchestrator for the Streamlit application:
- Page configuration and styling
- Authentication handling
- Navigation between tabs

Tab implementations are in:
- forex.ui.tabs.extraction (Rate Extraction)
- forex.ui.tabs.audit (Audit & Reconciliation)
"""

import os
import time

import streamlit as st

# --- PATH CONFIGURATION ---
current_dir = os.path.dirname(os.path.abspath(__file__))

# --- IMPORTS ---
try:
    from forex.auth import get_api_key, get_cookie_manager, set_api_key
    from forex.ui.tabs import audit, extraction

    _LOGIC_AVAILABLE = True
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.warning("Backend modules not found. Application may not work.")
    _LOGIC_AVAILABLE = False


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FX-Test",
    page_icon=os.path.join(current_dir, "assets", "favicon_optimized.png"),
    layout="wide",
)


# --- CSS LOADING ---
def load_css(file_name: str) -> None:
    """Load CSS file and inject into page."""
    file_path = os.path.join(current_dir, file_name)
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found at: {file_path}")


load_css("ui/styles.css")


# --- ACCESSIBILITY ---
st.markdown(
    """
<style>
    /* Skip Link for Keyboard Users */
    .skip-link {
        position: absolute;
        top: -9999px;
        left: -9999px;
        background: #066F45;
        color: white;
        padding: 10px 20px;
        z-index: 999999;
        text-decoration: none;
        font-weight: bold;
        border-radius: 4px;
    }
    .skip-link:focus {
        top: 20px;
        left: 20px;
        outline: 3px solid #5ddf79;
    }
</style>
<a href="#main-content" class="skip-link">Skip to main content</a>
""",
    unsafe_allow_html=True,
)


# --- TITLE ---
st.markdown(
    '<h1 class="gradient-title"><span class="title-fx">FX</span> <span class="title-test">Test</span></h1>',
    unsafe_allow_html=True,
)

# --- HELP BUTTON ---
st.markdown(
    """
<a href="/Help" target="_blank" class="info-btn">
    <span class="info-icon">i</span>
</a>
""",
    unsafe_allow_html=True,
)


# --- AUTHENTICATION ---
try:
    cookie_manager = get_cookie_manager()
    api_key = get_api_key(cookie_manager)
except NameError:
    cookie_manager = None
    api_key = "test_key"  # Fallback if auth missing

if not api_key:
    # --- AUTHENTICATION MODAL ---
    st.markdown('<div class="modal-backdrop"></div>', unsafe_allow_html=True)

    with st.form("auth_form"):
        st.markdown(
            """
            <div role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <h2 id="modal-title">🔐 API Key Required</h2>
            <p style="margin-bottom: 5px;">Please enter your <a href="https://twelvedata.com" target="_blank" style="color: #21BA1C; text-decoration: none; font-weight: bold;">Twelve Data</a> API Key to continue.</p>
            <p style="font-size: 0.8rem; margin-bottom: 15px;"><a href="https://twelvedata.com/account/api-keys" target="_blank" style="color: inherit; text-decoration: underline; opacity: 0.8;">Get your key here</a></p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        input_key = st.text_input(
            "API Key",
            type="password",
            label_visibility="collapsed",
            placeholder="Enter your key here...",
            help="Enter your 32-character API key",
        )

        st.markdown(
            '<p class="auth-disclaimer">Your key will be securely stored in your browser for 7 days.</p>',
            unsafe_allow_html=True,
        )

        cols = st.columns([1.5, 1])
        with cols[1]:
            submitted = st.form_submit_button("Initialize ➜")

        if submitted and input_key:
            set_api_key(cookie_manager, input_key)
            st.success("Key Saved! Reloading...")
            time.sleep(1)
            st.rerun()

else:
    # --- MAIN APPLICATION ---

    # Initialize navigation state
    if "nav_radio" not in st.session_state:
        st.session_state["nav_radio"] = "📊 Rate Extraction"

    # Navigation styling
    st.markdown(
        """
    <style>
    /* Aggressive Spacing Reduction */
    div.row-widget.stRadio {
        margin-top: -65px !important;
    }

    /* Pull download buttons closer to table */
    .audit-download-section {
        margin-top: -15px !important;
    }

    div.row-widget.stRadio > div {
        flex-direction: row;
        gap: 20px;
        border-bottom: 2px solid #f0f2f6;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    div.row-widget.stRadio > div > label {
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 5px;
        padding: 5px 15px;
        cursor: pointer;
        transition: all 0.3s;
    }
    div.row-widget.stRadio > div > label:hover {
        background-color: #f0f2f6;
    }
    div.row-widget.stRadio > div > label[data-testid="stMarkdownContainer"] > p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Navigation
    selected_tab = st.radio(
        "Navigation",
        ["📊 Rate Extraction", "🔍 Audit & Reconciliation"],
        horizontal=True,
        label_visibility="collapsed",
        key="nav_radio",
    )

    # Main Content Anchor
    st.markdown('<div id="main-content"></div>', unsafe_allow_html=True)

    # --- TAB ROUTING ---
    if selected_tab == "📊 Rate Extraction":
        extraction.render_tab(api_key, cookie_manager)
    elif selected_tab == "🔍 Audit & Reconciliation":
        audit.render_tab(api_key, cookie_manager)
