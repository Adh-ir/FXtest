import streamlit as st
import sys
import os
import time
import textwrap

# --- PATH CONFIGURATION ---
# Add parent directory to path to find 'logic' module
# This ensures that even if we run from code/, we can import from logic/ (if it exists in parent)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Try imports - handle potential missing modules gracefully
try:
    from core.auth import get_api_key, set_api_key, get_cookie_manager, clear_api_key
except ImportError:
    # If core.auth not found, try finding it in logic or define mocks for testing UI only
    try:
        from logic.auth import get_api_key, set_api_key, get_cookie_manager, clear_api_key
    except ImportError:
         st.error("Authentication modules not found. Application may not Work.")

try:
    from logic.auditor import process_audit_file, clear_rate_cache
    from logic.utils import convert_df_to_csv, convert_df_to_excel, create_template_excel
    from logic.facade import get_rates, get_available_currencies
    from logic.config import UI_CONFIG
except ImportError as e:
    st.error(f"Detailed Import Error: {e}")
    st.warning("Logic modules not found. Backend functionality will be disabled.")

# Try to import UI components
try:
    from ui.components import render_download_buttons, render_results_placeholder
    _HAS_COMPONENTS = True
except ImportError:
    _HAS_COMPONENTS = False

# Module-level constants (PEP 8 compliance)
TOP_CURRENCIES = list(UI_CONFIG.TOP_CURRENCIES) if 'UI_CONFIG' in dir() else ['ZAR', 'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'NZD']

# Page Config
st.set_page_config(page_title="FX-Test", page_icon=os.path.join(current_dir, "favicon_optimized.png"), layout="wide")

# Load Styles
def load_css(file_name):
    # Fix: use absolute path based on current file location
    # This resolves the FileNotFoundError on Streamlit Cloud
    file_path = os.path.join(current_dir, file_name)
    try:
        with open(file_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found at: {file_path}")

load_css("ui/styles.css")

# --- AUTHENTICATION ---
# The Mixed-Font Gradient Title (Semantic H1)
st.markdown('<h1 class="gradient-title"><span class="title-fx">FX</span> <span class="title-test">Test</span></h1>', unsafe_allow_html=True)

# Info Button Injection
st.markdown("""
<a href="/Help" target="_blank" class="info-btn">
    <span class="info-icon">i</span>
</a>
""", unsafe_allow_html=True)

# Initialize Cookie Manager
try:
    cookie_manager = get_cookie_manager()
    api_key = get_api_key(cookie_manager)
except NameError:
    cookie_manager = None
    api_key = "test_key" # Fallback if auth missing

if not api_key:
    # --- PROMPT FOR KEY ---
    st.markdown('<div class="modal-backdrop"></div>', unsafe_allow_html=True)
    
    with st.form("auth_form"):
        st.markdown("""
            <h2>🔐 API Key Required</h2>
            <p style="margin-bottom: 5px;">Please enter your <a href="https://twelvedata.com" target="_blank" style="color: #21BA1C; text-decoration: none; font-weight: bold;">Twelve Data</a> API Key to continue.</p>
            <p style="font-size: 0.8rem; margin-bottom: 15px;"><a href="https://twelvedata.com/account/api-keys" target="_blank" style="color: inherit; text-decoration: underline; opacity: 0.8;">Get your key here</a></p>
        """, unsafe_allow_html=True)
        
        input_key = st.text_input("API Key", type="password", label_visibility="collapsed", placeholder="Enter your key here...")
        
        st.markdown('<p class="auth-disclaimer">Your key will be securely stored in your browser for 7 days.</p>', unsafe_allow_html=True)
        
        cols = st.columns([1.5, 1])
        with cols[1]:
            submitted = st.form_submit_button("Initialise ➜")
        
        if submitted and input_key:
            set_api_key(cookie_manager, input_key)
            st.success("Key Saved! Reloading...")
            time.sleep(1)
            st.rerun()

else:
    # --- MAIN APP SHELL ---
    
    # Tabs for Rate Extraction vs Audit
    tab1, tab2 = st.tabs(["📊 Rate Extraction", "🔍 Audit & Reconciliation"])
    
    # ==================== TAB 1: RATE EXTRACTION ====================
    with tab1:
        col_left, col_right = st.columns([1, 1.5], gap="large")
        
        # --- LEFT PANE (Inputs) ---
        with col_left:
            st.markdown("### 🛠️ Configuration")
            
            # User Inputs - Currency Pair Row
            # Uses module-level TOP_CURRENCIES (moved for PEP 8 compliance)
            
            curr_col1, curr_col2 = st.columns(2)
            
            with curr_col1:
                st.markdown("**Base Currencies**")
                # Single Select for Base validation
                base_options = TOP_CURRENCIES[:]
                if "ZAR" not in base_options:
                    base_options.insert(0, "ZAR")
                    
                base_currency_selection = st.selectbox(
                    "Base", 
                    options=base_options, 
                    index=base_options.index("ZAR") if "ZAR" in base_options else 0,
                    label_visibility="collapsed", 
                    key="extract_base",
                    help="The currency you want rates quoted against (e.g., 1 USD = X ZAR)"
                )
                
            with curr_col2:
                st.markdown("**Source Currencies**")
                
                # Dynamic Fetch Logic
                available_options = []
                # Use the selected base currency
                primary_base = base_currency_selection.strip().upper() if base_currency_selection else "USD"
                
                if 'get_available_currencies' in locals() and api_key and primary_base:
                    try:
                        all_curr = get_available_currencies(api_key, primary_base)
                        if all_curr:
                            # Sticky Top Sort: Majors first, then alphabetical rest
                            majors = [c for c in TOP_CURRENCIES if c in all_curr]
                            others = sorted(list(set(all_curr) - set(majors)))
                            available_options = majors + others
                    except Exception:
                        pass # Fallback to empty if fetch fails

                # UI Layout
                input_container = st.container()
                
                # Checkbox for Select All
                select_all = st.checkbox("Select All Available Currencies", key="sel_all_toggle")
                
                selected_sources = []
                ack_high_volume = st.session_state.get('ack_high_vol', False)
                
                # MODAL WARNING LOGIC
                if select_all:
                    if not ack_high_volume:
                        # RENDER MODAL
                        st.markdown('<div class="modal-backdrop"></div>', unsafe_allow_html=True)
                        container = st.container()
                        with container:
                            with st.form("high_vol_warning"):
                                st.markdown("""
                                    <h2 style="color:#d32f2f !important;">⚠️ High Volume Warning</h2>
                                    <p>You are about to select <b>ALL available currencies</b>.</p>
                                    <p>This operation will consume a significant amount of your daily API quota and may take several minutes to complete.</p>
                                    <br>
                                """, unsafe_allow_html=True)
                                
                                c_col1, c_col2 = st.columns(2)
                                
                                # Define callback to clear state
                                def clear_selection():
                                    st.session_state['sel_all_toggle'] = False
                                    st.session_state['ack_high_vol'] = False
                                    
                                with c_col1:
                                    proceed = st.form_submit_button("✅ I Understand, Proceed", type="primary")
                                with c_col2:
                                    # Use on_click for reliable state update
                                    cancel = st.form_submit_button("❌ Cancel", on_click=clear_selection)
                                    
                                if proceed:
                                    st.session_state['ack_high_vol'] = True
                                    st.rerun()
                                    
                                if cancel:
                                    # The callback handles the state reset, rerunning happens automatically after 
                                    st.rerun()
                                    
                        # Stop execution so modal remains focus
                        st.stop()
                    else:
                        # Confirmed state
                        st.info(f"✅ All {len(available_options)} currencies selected.")
                        selected_sources = ["[ALL]"]
                else:
                    # Reset acknowledgment if unchecked
                    if ack_high_volume:
                        st.session_state['ack_high_vol'] = False
                    
                    # Standard Multi-Select
                    if available_options:
                        selected_sources = input_container.multiselect(
                            "Select currencies",
                            options=available_options,
                            default=["USD"] if "USD" in available_options else [],
                            label_visibility="collapsed",
                            placeholder="Select currencies...",
                            key="source_multiselect",
                            help="Select the currencies to retrieve exchange rates for"
                        )
                    else:
                        source_text = input_container.text_input("Source", value="USD", placeholder="e.g. USD, EUR", label_visibility="collapsed", key="extract_source_fallback")
                        selected_sources = [s.strip() for s in source_text.split(',') if s.strip()]

            st.markdown("**Date Range**")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                start_date = st.date_input("Start Date", key="extract_start", help="Start of historical rate range (YYYY-MM-DD)")
            with d_col2:
                end_date = st.date_input("End Date", key="extract_end", help="End of historical rate range (exclusive, data goes up to but not including this date)")
            
            invert_rates_extraction = st.checkbox("Invert rates (1/Rate)", key="invert_extraction")
            
            st.markdown("---")
            
            # Validation for Run
            run_disabled = False
            
            if not base_currency_selection:
                run_disabled = True
            
            if not select_all and not selected_sources:
                run_disabled = True
            
            # If select_all is true, we must have acknowledged (modal handles the blocking otherwise)
            
            # Show disabled state explanation
            if run_disabled:
                st.caption("⚠️ Select currencies to enable extraction")
            
            if st.button("Run Extraction", type="primary", disabled=run_disabled, key="extract_run"):
                with st.spinner("Fetching rates from Twelve Data..."):
                    try:
                        bases = [base_currency_selection]
                        
                        if select_all:
                             sources = available_options 
                        else:
                             sources = selected_sources
                        
                        s_date_str = start_date.strftime("%Y-%m-%d")
                        e_date_str = end_date.strftime("%Y-%m-%d")
                        
                        if 'get_rates' in locals():
                            df = get_rates(api_key, bases, s_date_str, e_date_str, sources, invert=invert_rates_extraction)
                            
                            if not df.empty:
                                st.session_state['last_result'] = df
                                st.success(f"Success! Retrieved {len(df)} records.")
                            else:
                                st.warning("No data found for the specified criteria.")
                        else:
                             st.error("Backend logic missing")
                            
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

            if st.button("Logout / Clear Key", type="secondary", key="logout_btn"):
                clear_api_key(cookie_manager)
                st.rerun()

        # --- RIGHT PANE (Results) ---
        with col_right:
            # Shift content up using CSS variable for maintenance
            st.markdown('<h3 style="margin-top: var(--results-header-offset, -80px);">📊 Extraction Results</h3>', unsafe_allow_html=True)
            
            if 'last_result' in st.session_state:
                res_df = st.session_state['last_result']
                
                # Fixed height dataframe with internal scroll
                
                # View Toggle
                view_mode = st.toggle(
                    "Summary View", 
                    key="toggle_extraction", 
                    help="Toggle for summary statistics (Mean, Std Dev, CV, High, Low)"
                )
                
                if view_mode: # Summary
                    # Detailed Statistics
                    summary_df = res_df.groupby(['Currency Base', 'Currency Source'])['Exchange Rate'].agg(['mean', 'std', 'min', 'max']).reset_index()
                    
                    # Formatting and Renaming (agg returns: mean, std, min, max)
                    summary_df.columns = ['Base', 'Source', 'Mean', 'Std Dev', 'Low', 'High']
                    
                    # Note: CV must be added AFTER renaming
                    summary_df['CV'] = summary_df['Std Dev'] / summary_df['Mean']
                    
                    # Reorder columns for readability
                    summary_df = summary_df[['Base', 'Source', 'Mean', 'Std Dev', 'CV', 'High', 'Low']]
                    
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                else: # Detailed
                    st.dataframe(
                        res_df, 
                        use_container_width=True, 
                        hide_index=True,
                        height=400  # Standardized across tabs
                    )
                
                # Download Buttons
                if 'convert_df_to_csv' in locals():
                    # Spacer using CSS class
                    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                    
                    # Columns with small gap - normalized ratios
                    dl_cols = st.columns([1, 1.1, 2], gap="small")
                    
                    csv = convert_df_to_csv(res_df)
                    excel = convert_df_to_excel(res_df)
                    
                    with dl_cols[0]:
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name="forex_rates.csv",
                            mime="text/csv",
                            key="dl_csv_extract"
                        )
                    with dl_cols[1]:
                        st.download_button(
                            label="Download Excel",
                            data=excel,
                            file_name="forex_rates.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_excel_extract"
                        )
            else:
                st.markdown('''
                    <div class="results-placeholder">
                        <p>Configure settings on the left and click 'Run Extraction'.</p>
                    </div>
                ''', unsafe_allow_html=True)

    # ==================== TAB 2: AUDIT & RECONCILIATION ====================
    with tab2:
        col_left, col_right = st.columns([1, 1.5], gap="large")
        
        # --- LEFT PANE (Audit Inputs) ---
        with col_left:
            st.markdown("### 🔍 Audit Configuration")
            
            # File Upload
            uploaded_file = st.file_uploader(
                "Upload your rates file (Excel/CSV)",
                type=['xlsx', 'xls', 'csv'],
                key="audit_file"
            )
            
            # Example Template
            # create_template_excel imported at top level
            template_bytes = create_template_excel()
            
            # Inject CSS for smaller font/height (targeting download button after file uploader)
            st.markdown("""
            <style>
            /* Target the template download button specifically */
            div[data-testid="stVerticalBlock"] > div[data-testid="element-container"]:has(+ div[data-testid="element-container"] [data-testid="stMarkdown"]) [data-testid="stDownloadButton"] button,
            [data-testid="stDownloadButton"][data-testid-key="dl_template"] button {
                font-size: 0.7rem !important;
                padding: 4px 12px !important;
                min-height: unset !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.download_button(
                label="⬇️ Download Example Template",
                data=template_bytes,
                file_name="fx_audit_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_template",
                help="Download a blank Excel file with the required column headers.",
                use_container_width=True
            )
            
            st.markdown("#### Configuration")
            
            col_d, col_t = st.columns(2)
            with col_d:
                date_format = st.text_input("Date Format in File", value="YYYY-MM-DD", help="e.g. DD/MM/YYYY", key="audit_date_fmt")
            with col_t:
                threshold = st.slider("Variance Threshold (%)", 0.0, 10.0, 5.0, 0.1, key="audit_threshold")

            invert_rates_audit = st.checkbox("Invert rates (Use 1/API Rate)", key="invert_audit")
            
            testing_mode = st.checkbox("🧪 Testing Mode (Mock API)", value=True, help="When enabled, uses mock rates instead of real API calls. Recommended for initial testing.", key="audit_test_mode")
            
            st.markdown("---")
            
            # Generate Audit Button
            audit_disabled = uploaded_file is None
            
            # Show disabled state explanation
            if audit_disabled:
                st.caption("⚠️ Upload a file to enable audit")
            
            if st.button("Generate Audit", type="primary", disabled=audit_disabled, key="audit_run"):
                if not uploaded_file:
                    st.error("Please upload a file first.")
                elif not api_key and not testing_mode:
                    st.error("API Key required for live mode.")
                else:
                    # Clear previous results and mark as processing
                    if 'audit_result' in st.session_state:
                        del st.session_state['audit_result']
                    st.session_state['audit_processing'] = True
                    st.session_state['audit_file_data'] = uploaded_file
                    st.session_state['audit_params'] = {
                        'date_fmt': date_format,
                        'threshold': threshold,
                        'testing_mode': testing_mode,
                        'invert_rates': invert_rates_audit
                    }
                    st.rerun()

        # --- RIGHT PANE (Audit Results / Progress) ---
        with col_right:
            st.markdown('<h3 style="margin-top: var(--results-header-offset, -70px);">📋 Audit Results</h3>', unsafe_allow_html=True)
            
            # Check if we're processing
            if st.session_state.get('audit_processing', False):
                if 'clear_rate_cache' in locals():
                    clear_rate_cache()
                
                # Create progress containers IN THE RIGHT PANE
                progress_bar = st.progress(0, text="Initializing...")
                status_text = st.empty()
                
                try:
                    params = st.session_state['audit_params']
                    file_data = st.session_state['audit_file_data']
                    
                    if 'process_audit_file' in locals():
                        # Call the generator
                        gen = process_audit_file(
                            file=file_data,
                            date_fmt=params['date_fmt'],
                            threshold=params['threshold'],
                            api_key=api_key,
                            testing_mode=params['testing_mode'],
                            invert_rates=params['invert_rates']
                        )
                        
                        # Consume generator for progress updates
                        final_result = None
                        for update in gen:
                            current = update.get('current', 0)
                            total = update.get('total', 1)
                            message = update.get('message', '')
                            status = update.get('status', '')
                            
                            # Update progress bar
                            if total > 0:
                                progress_val = min(current / total, 1.0)
                                progress_bar.progress(progress_val, text=f"{current}/{total}")
                            
                            # Update status
                            if status == 'waiting':
                                status_text.warning(f"⏳ {message}")
                            elif status == 'error':
                                status_text.error(f"❌ {message}")
                            elif status == 'complete':
                                status_text.success(f"✅ {message}")
                            else:
                                status_text.info(f"📊 {message}")
                        
                        # Get final result via StopIteration
                        try:
                            gen.send(None)
                        except StopIteration as e:
                            final_result = e.value
                        
                        # Store result and clear processing flag
                        if final_result:
                            st.session_state['audit_result'] = final_result
                            st.session_state['audit_processing'] = False
                            progress_bar.progress(1.0, text="Complete!")
                            import time
                            time.sleep(0.5)  # Brief pause to show completion
                            st.rerun()
                        else:
                            st.session_state['audit_processing'] = False
                            st.error("Audit completed but no results returned.")
                    else:
                        st.session_state['audit_processing'] = False
                        st.error("Audit logic not found")
                        
                except Exception as e:
                    st.session_state['audit_processing'] = False
                    st.error(f"Audit failed: {e}")
            
            elif 'audit_result' in st.session_state:
                df, summary = st.session_state['audit_result']
                
                # Summary Metrics
                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.metric("📊 Total Rows", summary.get('total_rows', 0))
                with metric_cols[1]:
                    st.metric("✅ Passed", summary.get('passed', 0))
                with metric_cols[2]:
                    st.metric("⚠️ Exceptions", summary.get('exceptions', 0))
                with metric_cols[3]:
                    st.metric("❌ Errors", summary.get('api_errors', 0))
                
                if summary.get('testing_mode'):
                    st.info("🧪 Results generated with **mock data** (Testing Mode enabled)")
                
                # Results Table
                if not df.empty:
                    
                    # View Toggle
                    
                    view_mode_audit = st.toggle(
                        "Summary View", 
                        key="toggle_audit",
                        help="Switch to summary view for statistics"
                    )
                    
                    if view_mode_audit: # Summary
                        # Simple counts summary
                        summary_counts = df['Status'].value_counts().reset_index()
                        summary_counts.columns = ['Status', 'Count']
                        st.dataframe(summary_counts, use_container_width=True)
                        
                    else: # Detailed
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            height=400  # Standardized with Tab 1
                        )
                    
                    # Download Buttons
                    if 'convert_df_to_csv' in locals():
                        st.markdown("**📥 Download Audit Report**")
                        dl_cols = st.columns([1, 1.1, 2], gap="small")  # Consistent with Tab 1
                        
                        csv = convert_df_to_csv(df)
                        excel = convert_df_to_excel(df)
                        
                        with dl_cols[0]:
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name="audit_report.csv",
                                mime="text/csv",
                                key="dl_csv_audit"
                            )
                        with dl_cols[1]:
                            st.download_button(
                                label="Download Excel",
                                data=excel,
                                file_name="audit_report.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="dl_excel_audit"
                            )
                else:
                    st.warning("No processable data in the uploaded file.")
            else:
                # Using a single line string or manual concatenation to ensure no indentation issues
                html_table = """
<div class="results-placeholder">
    <p style="margin-bottom: 15px;">Upload a file and click 'Generate Audit' to validate rates.</p>
    <div style="width: 100%; max-width: 600px;">
        <p style="font-size: 0.8rem; font-weight: 700; margin-bottom: 5px; opacity: 0.9;">Required Columns:</p>
        <table class="schema-table">
            <thead>
                <tr>
                    <th>Transaction Date</th>
                    <th>Base Currency</th>
                    <th>Source Currency</th>
                    <th>User Rate</th>
                </tr>
            </thead>
        </table>
    </div>
</div>
"""
                st.markdown(html_table, unsafe_allow_html=True)
