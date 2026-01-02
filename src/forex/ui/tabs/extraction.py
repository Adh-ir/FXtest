"""
Rate Extraction Tab

Handles the rate extraction UI:
- Configuration inputs (base/source currencies, date range)
- API call orchestration
- Results display and download options
"""

import streamlit as st

from forex.auth import clear_api_key
from forex.config import UI_CONFIG
from forex.facade import get_available_currencies, get_rates
from forex.utils import convert_df_to_csv, convert_df_to_excel

# Module-level constants
TOP_CURRENCIES = list(UI_CONFIG.TOP_CURRENCIES)


def render_tab(api_key: str, cookie_manager) -> None:
    """
    Render the Rate Extraction tab.

    Args:
        api_key: Authenticated Twelve Data API key
        cookie_manager: Cookie manager for auth operations (logout)
    """
    col_left, col_right = st.columns([1, 1.5], gap="large")

    # --- LEFT PANE (Inputs) ---
    with col_left:
        st.markdown("### 🛠️ Configuration")

        # User Inputs - Currency Pair Row
        curr_col1, curr_col2 = st.columns(2)

        with curr_col1:
            st.markdown("**Base Currencies**")
            base_options = TOP_CURRENCIES[:]
            if "ZAR" not in base_options:
                base_options.insert(0, "ZAR")

            base_currency_selection = st.selectbox(
                "Base",
                options=base_options,
                index=base_options.index("ZAR") if "ZAR" in base_options else 0,
                label_visibility="collapsed",
                key="extract_base",
                help="The currency you want rates quoted against (e.g., 1 USD = X ZAR)",
            )

        with curr_col2:
            st.markdown("**Source Currencies**")

            # Dynamic Fetch Logic
            available_options = []
            primary_base = base_currency_selection.strip().upper() if base_currency_selection else "USD"

            if api_key and primary_base:
                try:
                    all_curr = get_available_currencies(api_key, primary_base)
                    if all_curr:
                        # Sticky Top Sort: Majors first, then alphabetical rest
                        majors = [c for c in TOP_CURRENCIES if c in all_curr]
                        others = sorted(set(all_curr) - set(majors))
                        available_options = majors + others
                except Exception:
                    pass  # Fallback to empty if fetch fails

            # UI Layout
            input_container = st.container()

            # Checkbox for Select All
            select_all = st.checkbox("Select All Available Currencies", key="sel_all_toggle")

            selected_sources = []
            ack_high_volume = st.session_state.get("ack_high_vol", False)

            # MODAL WARNING LOGIC
            if select_all:
                if not ack_high_volume:
                    _render_high_volume_warning(available_options)
                else:
                    # Confirmed state
                    st.info(f"✅ All {len(available_options)} currencies selected.")
                    selected_sources = ["[ALL]"]
            else:
                # Reset acknowledgment if unchecked
                if ack_high_volume:
                    st.session_state["ack_high_vol"] = False

                # Standard Multi-Select
                if available_options:
                    selected_sources = input_container.multiselect(
                        "Select currencies",
                        options=available_options,
                        default=["USD"] if "USD" in available_options else [],
                        label_visibility="collapsed",
                        placeholder="Select currencies...",
                        key="source_multiselect",
                        help="Select the currencies to retrieve exchange rates for",
                    )
                else:
                    source_text = input_container.text_input(
                        "Source",
                        value="USD",
                        placeholder="e.g. USD, EUR",
                        label_visibility="collapsed",
                        key="extract_source_fallback",
                    )
                    selected_sources = [s.strip() for s in source_text.split(",") if s.strip()]

        st.markdown("<h4>Date Range</h4>", unsafe_allow_html=True)
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            start_date = st.date_input(
                "Start Date",
                key="extract_start",
                help="Start of historical rate range (YYYY-MM-DD)",
            )
        with d_col2:
            end_date = st.date_input(
                "End Date",
                key="extract_end",
                help="End of historical rate range (exclusive, data goes up to but not including this date)",
            )

        invert_rates_extraction = st.checkbox("Invert rates (1/Rate)", key="invert_extraction")

        st.markdown("---")

        # Validation for Run
        run_disabled = not base_currency_selection or (not select_all and not selected_sources)

        if run_disabled:
            st.caption("⚠️ Select currencies to enable extraction")

        if st.button(
            "Run Extraction",
            type="primary",
            disabled=run_disabled,
            key="extract_run",
        ):
            _run_extraction(
                api_key=api_key,
                base_currency=base_currency_selection,
                selected_sources=selected_sources,
                available_options=available_options,
                select_all=select_all,
                start_date=start_date,
                end_date=end_date,
                invert=invert_rates_extraction,
            )

        if st.button("Logout / Clear Key", type="secondary", key="logout_btn"):
            clear_api_key(cookie_manager)
            st.rerun()

    # --- RIGHT PANE (Results) ---
    with col_right:
        st.markdown(
            '<h3 style="margin-top: var(--results-header-offset, -80px);">📊 Extraction Results</h3>',
            unsafe_allow_html=True,
        )

        if "last_result" in st.session_state:
            _render_results(st.session_state["last_result"])
        else:
            st.markdown(
                """
                <div class="results-placeholder">
                    <p>Configure settings on the left and click 'Run Extraction'.</p>
                </div>
            """,
                unsafe_allow_html=True,
            )


def _render_high_volume_warning(available_options: list) -> None:
    """Render the high volume warning modal."""
    st.markdown('<div class="modal-backdrop"></div>', unsafe_allow_html=True)
    container = st.container()
    with container:
        with st.form("high_vol_warning"):
            st.markdown(
                """
                <h2 style="color:#d32f2f !important;">⚠️ High Volume Warning</h2>
                <p>You are about to select <b>ALL available currencies</b>.</p>
                <p>This operation will consume a significant amount of your daily API quota and may take several minutes to complete.</p>
                <br>
            """,
                unsafe_allow_html=True,
            )

            c_col1, c_col2 = st.columns(2)

            def clear_selection():
                st.session_state["sel_all_toggle"] = False
                st.session_state["ack_high_vol"] = False

            with c_col1:
                proceed = st.form_submit_button("✅ I Understand, Proceed", type="primary")
            with c_col2:
                cancel = st.form_submit_button("❌ Cancel", on_click=clear_selection)

            if proceed:
                st.session_state["ack_high_vol"] = True
                st.rerun()

            if cancel:
                st.rerun()

    st.stop()


def _run_extraction(
    api_key: str,
    base_currency: str,
    selected_sources: list,
    available_options: list,
    select_all: bool,
    start_date,
    end_date,
    invert: bool,
) -> None:
    """Execute the rate extraction."""
    with st.spinner("Fetching rates from Twelve Data..."):
        try:
            bases = [base_currency]
            sources = available_options if select_all else selected_sources

            s_date_str = start_date.strftime("%Y-%m-%d")
            e_date_str = end_date.strftime("%Y-%m-%d")

            df = get_rates(
                api_key,
                bases,
                s_date_str,
                e_date_str,
                sources,
                invert=invert,
            )

            if not df.empty:
                st.session_state["last_result"] = df
                st.success(f"Success! Retrieved {len(df)} records.")
            else:
                st.warning("No data found for the specified criteria.")

        except Exception as e:
            _handle_extraction_error(e)


def _handle_extraction_error(e: Exception) -> None:
    """Handle extraction errors with user-friendly messages."""
    error_msg = str(e).lower()
    if "rate limit" in error_msg or "429" in error_msg:
        st.error("⏱️ API rate limit exceeded. Please wait a minute and try again.")
    elif "unauthorized" in error_msg or "401" in error_msg or "api key" in error_msg:
        st.error("🔑 API key is invalid or expired. Please check your credentials.")
    elif "timeout" in error_msg:
        st.error("⌛ Request timed out. Please try again with a smaller date range.")
    else:
        st.error(f"An error occurred: {e}")


def _render_results(res_df) -> None:
    """Render the results dataframe and download buttons."""
    # View Toggle
    view_mode = st.toggle(
        "Summary View",
        key="toggle_extraction",
        help="Toggle for summary statistics (Mean, Std Dev, CV, High, Low)",
    )

    if view_mode:  # Summary
        summary_df = (
            res_df.groupby(["Currency Base", "Currency Source"])["Exchange Rate"]
            .agg(["mean", "std", "min", "max"])
            .reset_index()
        )

        summary_df.columns = ["Base", "Source", "Mean", "Std Dev", "Low", "High"]
        summary_df["CV"] = (summary_df["Std Dev"] / summary_df["Mean"] * 100).round(2).astype(str) + "%"
        summary_df = summary_df[["Base", "Source", "Mean", "Std Dev", "CV", "High", "Low"]]

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            height=200,
        )
    else:  # Detailed
        st.dataframe(
            res_df,
            use_container_width=True,
            hide_index=True,
            height=560,
        )

    # Download Buttons
    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    dl_cols = st.columns([1, 1.1, 2], gap="small")

    csv = convert_df_to_csv(res_df)
    excel = convert_df_to_excel(res_df)

    with dl_cols[0]:
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="forex_rates.csv",
            mime="text/csv",
            key="dl_csv_extract",
        )
    with dl_cols[1]:
        st.download_button(
            label="Download Excel",
            data=excel,
            file_name="forex_rates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_excel_extract",
        )
