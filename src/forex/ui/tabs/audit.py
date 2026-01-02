"""
Audit & Reconciliation Tab

Handles the audit UI:
- File upload and configuration
- Audit execution with progress feedback
- Results display with metrics and download options
"""

from io import BytesIO

import streamlit as st

from forex.auditor import clear_rate_cache, run_audit
from forex.utils import convert_df_to_csv, convert_df_to_excel, create_template_excel


def render_tab(api_key: str, cookie_manager) -> None:
    """
    Render the Audit & Reconciliation tab.

    Args:
        api_key: Authenticated Twelve Data API key
        cookie_manager: Cookie manager for auth operations (unused in this tab but kept for interface consistency)
    """
    col_left, col_right = st.columns([1, 1.5], gap="large")

    # --- LEFT PANE (Audit Inputs) ---
    with col_left:
        st.markdown("### 🔍 Audit Configuration")

        # File Upload
        uploaded_file = st.file_uploader(
            "Upload your rates file (Excel/CSV)",
            type=["xlsx", "xls", "csv"],
            key="audit_file",
            help="File must contain columns: Date, Base Currency, Source Currency, User Rate",
        )

        # Example Template
        template_bytes = create_template_excel()

        # Inject CSS for smaller template download button
        st.markdown(
            """
        <style>
        /* Target the template download button specifically */
        div[data-testid="stVerticalBlock"] > div[data-testid="element-container"]:has(+ div[data-testid="element-container"] [data-testid="stMarkdown"]) [data-testid="stDownloadButton"] button,
        [data-testid="stDownloadButton"][data-testid-key="dl_template"] button {
            font-size: 0.7rem !important;
            padding: 4px 12px !important;
            min-height: unset !important;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        st.download_button(
            label="⬇️ Download Example Template",
            data=template_bytes,
            file_name="fx_audit_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_template",
            help="Download a blank Excel file with the required column headers.",
            use_container_width=True,
        )

        st.markdown("#### Configuration")

        col_d, col_t = st.columns(2)
        with col_d:
            date_format = st.text_input(
                "Date Format in File",
                value="YYYY-MM-DD",
                help="e.g. DD/MM/YYYY",
                key="audit_date_fmt",
            )
        with col_t:
            threshold = st.slider("Variance Threshold (%)", 0.0, 10.0, 5.0, 0.1, key="audit_threshold")

        # Invert rates hardcoded to False per user request
        invert_rates_audit = False

        testing_mode = st.checkbox(
            "🧪 Testing Mode (Mock API)",
            value=True,
            help="When enabled, uses mock rates instead of real API calls. Recommended for initial testing.",
            key="audit_test_mode",
        )

        st.markdown("---")

        # Generate Audit Button
        audit_disabled = uploaded_file is None

        if audit_disabled:
            st.caption("⚠️ Upload a file to enable audit")

        if st.button(
            "Generate Audit",
            type="primary",
            disabled=audit_disabled,
            key="audit_run",
        ):
            _start_audit(
                uploaded_file=uploaded_file,
                date_format=date_format,
                threshold=threshold,
                testing_mode=testing_mode,
                invert_rates=invert_rates_audit,
            )

    # --- RIGHT PANE (Audit Results) ---
    with col_right:
        st.markdown(
            '<h3 style="margin-top: var(--results-header-offset, -70px);">📋 Audit Results</h3>',
            unsafe_allow_html=True,
        )

        # Check if we're processing (triggered by button click)
        if st.session_state.get("audit_processing", False):
            _execute_audit(api_key)

        elif "audit_result" in st.session_state:
            _render_audit_results()

        else:
            st.info("Upload a file and click **Generate Audit** to see results here.")


def _start_audit(
    uploaded_file,
    date_format: str,
    threshold: float,
    testing_mode: bool,
    invert_rates: bool,
) -> None:
    """Initialize audit processing state."""
    # Clear previous results and mark as processing
    if "audit_result" in st.session_state:
        del st.session_state["audit_result"]
    st.session_state["audit_processing"] = True

    # Store file CONTENT (bytes) and name, not the UploadedFile object
    st.session_state["audit_file_data"] = uploaded_file.getvalue()
    st.session_state["audit_file_name"] = uploaded_file.name

    st.session_state["audit_params"] = {
        "date_fmt": date_format,
        "threshold": threshold,
        "testing_mode": testing_mode,
        "invert_rates": invert_rates,
    }
    st.rerun()


def _execute_audit(api_key: str) -> None:
    """Execute the audit processing."""
    clear_rate_cache()

    with st.spinner("Running audit..."):
        try:
            params = st.session_state["audit_params"]
            file_bytes = st.session_state["audit_file_data"]
            file_name = st.session_state.get("audit_file_name", "file.xlsx")

            # Wrap bytes in BytesIO for pandas to read
            file_data = BytesIO(file_bytes)
            file_data.name = file_name

            # Progress Placeholder
            progress_text = st.empty()

            def update_progress(msg: str) -> None:
                progress_text.text(f"⏳ {msg}")

            # Run audit synchronously
            df, summary = run_audit(
                file=file_data,
                date_fmt=params["date_fmt"],
                threshold=params["threshold"],
                api_key=api_key,
                testing_mode=params["testing_mode"],
                invert_rates=params["invert_rates"],
                progress_callback=update_progress,
            )

            if not df.empty:
                st.session_state["audit_result"] = (df, summary)
                st.session_state["audit_processing"] = False
                st.rerun()
            else:
                st.session_state["audit_processing"] = False
                st.error("Audit returned no results. Check your file format.")

        except Exception as e:
            st.session_state["audit_processing"] = False
            st.error(f"Audit failed: {e}")


def _render_audit_results() -> None:
    """Render audit results with metrics and download buttons."""
    df, summary = st.session_state["audit_result"]

    # Summary Metrics (always shown)
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("📊 Total Rows", summary.get("total_rows", 0))
    with metric_cols[1]:
        st.metric("✅ Passed", summary.get("passed", 0))
    with metric_cols[2]:
        st.metric("⚠️ Exceptions", summary.get("exceptions", 0))
    with metric_cols[3]:
        st.metric("❌ Errors", summary.get("api_errors", 0))

    if summary.get("testing_mode"):
        st.info("🧪 Results generated with **mock data** (Testing Mode enabled)")

    # Results Table
    if not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=400,
        )

        # Download Buttons
        st.markdown(
            '<div class="audit-download-section"></div>',
            unsafe_allow_html=True,
        )

        dl_cols = st.columns([1, 1.1, 2], gap="small")

        csv = convert_df_to_csv(df)
        excel = convert_df_to_excel(df)

        with dl_cols[0]:
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="audit_report.csv",
                mime="text/csv",
                key="dl_csv_audit",
            )
        with dl_cols[1]:
            st.download_button(
                label="Download Excel",
                data=excel,
                file_name="audit_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_excel_audit",
            )
