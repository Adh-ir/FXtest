"""
Rate Finder View - Extracted from the original monolith app.py
Handles currency pair input, date range selection, and rate extraction.
"""
import streamlit as st


def render_finder(api_key: str):
    """
    Render the Rate Finder view.
    
    Args:
        api_key: The authenticated Twelve Data API key.
    """
    col_left, col_right = st.columns([1, 1.5], gap="large")
    
    # --- LEFT PANE (Inputs) ---
    with col_left:
        st.markdown("### 🛠️ Configuration")
        
        # User Inputs - Currency Pair Row
        curr_col1, curr_col2 = st.columns(2)
        with curr_col1:
            st.markdown("**Base Currencies**")
            base_currencies_input = st.text_input("Base", value="ZAR", placeholder="e.g. ZAR, USD", label_visibility="collapsed")
        with curr_col2:
            st.markdown("**Source Currencies**")
            source_currencies_input = st.text_input("Source", value="USD", placeholder="e.g. USD, EUR", label_visibility="collapsed")
        
        st.markdown("**Date Range**")
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            start_date = st.date_input("Start Date")
        with d_col2:
            end_date = st.date_input("End Date")
            
        st.markdown("---")
        
        # Validation for Run
        run_disabled = False
        if not base_currencies_input or not source_currencies_input:
            run_disabled = True
            
        if st.button("Run Extraction", type="primary", disabled=run_disabled):
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
                    from logic.utils import convert_df_to_csv, convert_df_to_excel
                    
                    df = get_rates(api_key, bases, s_date_str, e_date_str)
                    
                    if not df.empty:
                        st.session_state['last_result'] = df
                        st.success(f"Success! Retrieved {len(df)} records.")
                    else:
                        st.warning("No data found for the specified criteria.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {e}")

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
                height=400  # Fixed height in pixels
            )
            
            # Download Buttons OUTSIDE the container
            st.markdown("#### 📥 Download")
            dl_cols = st.columns(2)
            
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
            # Placeholder message in styled container
            st.markdown('''
                <div class="results-placeholder">
                    <p>Configure settings on the left and click 'Run Extraction'.</p>
                </div>
            ''', unsafe_allow_html=True)
