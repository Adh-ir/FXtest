import streamlit as st

from core.auth import get_api_key, set_api_key, get_cookie_manager, clear_api_key
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
# Wait a moment for cookie manager to load (simulated async)
time.sleep(0.5)

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
        cols = st.columns([1.5, 1]) # Spacer takes 60%, Button column takes 40%
        with cols[1]:
            submitted = st.form_submit_button("Initialise ➜")
        
        if submitted and input_key:
            set_api_key(cookie_manager, input_key)
            st.success("Key Saved! reloading...")
            time.sleep(1)
            st.rerun()

else:
    # --- MAIN APP SHELL ---
    col_left, col_right = st.columns([1, 1.5], gap="large")
    
    # --- LEFT PANE (Inputs) ---
    with col_left:
        st.markdown("### 🛠️ Configuration")
        
        # User Inputs
        st.markdown("**Base Currencies**")
        base_currencies_input = st.text_input("e.g. ZAR, USD", value="ZAR", placeholder="ZAR")
        
        st.markdown("**Date Range**")
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            start_date = st.date_input("Start Date")
        with d_col2:
            end_date = st.date_input("End Date")
            
        st.markdown("---")
        
        # Validation for Run
        run_disabled = False
        if not base_currencies_input:
            run_disabled = True
            
        if st.button("Run Extraction", type="primary", disabled=run_disabled):
            with st.spinner("Fetching rates from Twelve Data..."):
                try:
                    # Parse currencies
                    bases = [b.strip() for b in base_currencies_input.split(',') if b.strip()]
                    
                    # Convert dates to string
                    s_date_str = start_date.strftime("%Y-%m-%d")
                    e_date_str = end_date.strftime("%Y-%m-%d")
                    
                    # CALL CORE LOGIC
                    from logic.facade import get_rates
                    from logic.utils import convert_df_to_csv, convert_df_to_excel
                    
                    df = get_rates(api_key, bases, s_date_str, e_date_str)
                    
                    if not df.empty:
                        st.session_state['last_result'] = df
                        st.success(f"Success! Retrieved {len(df)} records.")
                    else:
                        st.warning("No data found for the specified criteria.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        if st.button("Logout / Clear Key", type="secondary"):
            clear_api_key(cookie_manager)
            st.rerun()

    # --- RIGHT PANE (Results) ---
    with col_right:
        st.markdown("### 📊 Extraction Results")
        
        # We use a custom HTML container for the 'Fixed Height + Scroll' requirement
        st.markdown('<div class="results-container">', unsafe_allow_html=True)
             
        if 'last_result' in st.session_state:
            res_df = st.session_state['last_result']
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            # Download Buttons
            st.markdown("#### 📥 Download")
            dl_cols = st.columns(2)
            
            # Lazy import utils if strictly needed, or just rely on imports at top (to be added)
            from logic.utils import convert_df_to_csv, convert_df_to_excel
            
            csv = convert_df_to_csv(res_df)
            excel = convert_df_to_excel(res_df)
            
            with dl_cols[0]:
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="forex_rates.csv",
                    mime="text/csv"
                )
            with dl_cols[1]:
                st.download_button(
                    label="Download Excel",
                    data=excel,
                    file_name="forex_rates.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Configure settings on the left and click 'Run Extraction'.")
             
        st.markdown('</div>', unsafe_allow_html=True)
