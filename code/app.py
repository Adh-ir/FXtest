import streamlit as st
import sys
import os

# Add parent directory to path to find 'logic' module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import get_api_key, set_api_key, get_cookie_manager, clear_api_key
from logic.auditor import process_audit_file, clear_rate_cache
from logic.utils import convert_df_to_csv, convert_df_to_excel
import time

# Page Config
st.set_page_config(page_title="FX-Test", page_icon="favicon_clean.png", layout="wide")

# Load Styles
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("ui/styles.css")

# --- AUTHENTICATION ---
# The Mixed-Font Gradient Title
st.markdown('<h3 class="gradient-title"><span class="title-fx">FX</span><span class="title-hyphen">-</span><span class="title-test">Test</span></h3>', unsafe_allow_html=True)

# Info Button Injection
st.markdown("""
<a href="https://twelvedata.com/docs" target="_blank" class="info-btn">
    <span class="info-icon">i</span>
</a>
""", unsafe_allow_html=True)

# Initialize Cookie Manager (Must be at top level)
cookie_manager = get_cookie_manager()

# Get API key (session state takes priority, then cookies)
api_key = get_api_key(cookie_manager)

if not api_key:
    # --- PROMPT FOR KEY ---
    st.markdown('<div class="modal-backdrop"></div>', unsafe_allow_html=True)
    
    # The Form becomes the Modal via CSS targeting [data-testid="stForm"]
    with st.form("auth_form"):
        st.markdown("""
            <h2>🔐 API Key Required</h2>
            <p style="margin-bottom: 5px;">Please enter your <a href="https://twelvedata.com" target="_blank" style="color: #21BA1C; text-decoration: none; font-weight: bold;">Twelve Data</a> API Key to continue.</p>
            <p style="font-size: 0.8rem; margin-bottom: 15px;"><a href="https://twelvedata.com/account/api-keys" target="_blank" style="color: inherit; text-decoration: underline; opacity: 0.8;">Get your key here</a></p>
        """, unsafe_allow_html=True)
        
        input_key = st.text_input("API Key", type="password", label_visibility="collapsed", placeholder="Enter your key here...")
        
        st.markdown('<p class="auth-disclaimer">Your key will be securely stored in your browser for 7 days.</p>', unsafe_allow_html=True)
        
        # Use columns to force Right Alignment of the button
        cols = st.columns([1.5, 1])
        with cols[1]:
            submitted = st.form_submit_button("Initialise ➜")
        
        if submitted and input_key:
            set_api_key(cookie_manager, input_key)
            st.success("Key Saved! reloading...")
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
            curr_col1, curr_col2 = st.columns(2)
            with curr_col1:
                st.markdown("**Base Currencies**")
                base_currencies_input = st.text_input("Base", value="ZAR", placeholder="e.g. ZAR, USD", label_visibility="collapsed", key="extract_base")
            with curr_col2:
                st.markdown("**Source Currencies**")
                source_currencies_input = st.text_input("Source", value="USD", placeholder="e.g. USD, EUR", label_visibility="collapsed", key="extract_source")
            
            st.markdown("**Date Range**")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                start_date = st.date_input("Start Date", key="extract_start")
            with d_col2:
                end_date = st.date_input("End Date", key="extract_end")
                
            st.markdown("---")
            
            # Validation for Run
            run_disabled = False
            if not base_currencies_input or not source_currencies_input:
                run_disabled = True
                
            if st.button("Run Extraction", type="primary", disabled=run_disabled, key="extract_run"):
                with st.spinner("Fetching rates from Twelve Data..."):
                    try:
                        # Parse currencies
                        bases = [b.strip() for b in base_currencies_input.split(',') if b.strip()]
                        sources = [s.strip() for s in source_currencies_input.split(',') if s.strip()]
                        
                        # Convert dates to string
                        s_date_str = start_date.strftime("%Y-%m-%d")
                        e_date_str = end_date.strftime("%Y-%m-%d")
                        
                        # CALL CORE LOGIC
                        from logic.facade import get_rates
                        
                        df = get_rates(api_key, bases, s_date_str, e_date_str)
                        
                        if not df.empty:
                            st.session_state['last_result'] = df
                            st.success(f"Success! Retrieved {len(df)} records.")
                        else:
                            st.warning("No data found for the specified criteria.")
                            
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

            if st.button("Logout / Clear Key", type="secondary", key="logout_btn"):
                clear_api_key(cookie_manager)
                st.rerun()

        # --- RIGHT PANE (Results) ---
        with col_right:
            st.markdown("### 📊 Extraction Results")
            
            if 'last_result' in st.session_state:
                res_df = st.session_state['last_result']
                
                # Fixed height dataframe with internal scroll
                st.dataframe(
                    res_df, 
                    use_container_width=True, 
                    hide_index=True,
                    height=400
                )
                
                # Download Buttons
                st.markdown("#### 📥 Download")
                dl_cols = st.columns(2)
                
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
                type=["xlsx", "xls", "csv"],
                help="File must contain columns: Date, Base, Source, User Rate (or similar)",
                key="audit_file"
            )
            
            # Date Format
            date_format = st.selectbox(
                "Date Format in File",
                options=["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY", "DD-MM-YYYY"],
                index=0,
                key="audit_date_fmt"
            )
            
            # Threshold
            threshold = st.slider(
                "Variance Threshold (%)",
                min_value=0.1,
                max_value=20.0,
                value=5.0,
                step=0.5,
                help="Rates exceeding this variance from API rates will be marked as EXCEPTION",
                key="audit_threshold"
            )
            
            # Testing Mode
            testing_mode = st.checkbox(
                "🧪 Testing Mode (Mock API)",
                value=True,
                help="When enabled, uses mock rates instead of real API calls. Recommended for initial testing.",
                key="audit_test_mode"
            )
            
            st.markdown("---")
            
            # Generate Audit Button
            audit_disabled = uploaded_file is None
            
            if st.button("Generate Audit", type="primary", disabled=audit_disabled, key="audit_run"):
                # Clear previous results
                if 'audit_result' in st.session_state:
                    del st.session_state['audit_result']
                
                # Clear rate cache for fresh start
                clear_rate_cache()
                
                # Create progress containers
                progress_bar = st.progress(0, text="Initializing...")
                status_text = st.empty()
                
                try:
                    # Call the generator
                    gen = process_audit_file(
                        file=uploaded_file,
                        date_fmt=date_format,
                        threshold=threshold,
                        api_key=api_key,
                        testing_mode=testing_mode
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
                    
                    # Store result
                    if final_result:
                        st.session_state['audit_result'] = final_result
                        progress_bar.progress(1.0, text="Complete!")
                        st.rerun()
                    else:
                        st.error("Audit completed but no results returned.")
                        
                except Exception as e:
                    st.error(f"Audit failed: {e}")

        # --- RIGHT PANE (Audit Results) ---
        with col_right:
            st.markdown("### 📋 Audit Results")
            
            if 'audit_result' in st.session_state:
                df, summary = st.session_state['audit_result']
                
                # Summary Metrics
                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.metric("Total Rows", summary.get('total_rows', 0))
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
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=350
                    )
                    
                    # Download Buttons
                    st.markdown("#### 📥 Download Audit Report")
                    dl_cols = st.columns(2)
                    
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
                st.markdown('''
                    <div class="results-placeholder">
                        <p>Upload a file and click 'Generate Audit' to validate rates.</p>
                    </div>
                ''', unsafe_allow_html=True)
