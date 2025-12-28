"""
Audit Tool View - Rate validation and auditing interface.
Allows users to upload Excel files with exchange rates and validate them
against official sources with a configurable threshold.
"""
import streamlit as st


def render_auditor():
    """
    Render the Audit Tool view.
    
    Left Pane: File upload and threshold configuration
    Right Pane: Instructions or Generate button based on state
    """
    col_left, col_right = st.columns([1, 1.5], gap="large")
    
    # --- LEFT PANE (Inputs) ---
    with col_left:
        st.markdown("### 📁 Upload Configuration")
        
        # File Uploader - Excel only
        uploaded_file = st.file_uploader(
            "Upload Excel File",
            type=["xlsx", "xls"],
            help="Upload an Excel file containing exchange rates to audit."
        )
        
        st.markdown("---")
        
        # Threshold Slider
        st.markdown("**Variance Threshold**")
        threshold = st.slider(
            "Threshold (%)",
            min_value=0,
            max_value=20,
            value=5,
            step=1,
            help="Maximum acceptable percentage difference between user rates and official rates.",
            label_visibility="collapsed"
        )
        st.caption(f"Rates with >{threshold}% variance will be flagged.")
    
    # --- RIGHT PANE (Results / Instructions) ---
    with col_right:
        st.markdown("### 🔍 Audit Results")
        
        if uploaded_file is None:
            # State 1: No file uploaded - Show instructions
            st.markdown('''
                <div class="results-placeholder" style="text-align: left; padding: 30px;">
                    <div>
                        <h4 style="margin-bottom: 15px;">📋 Getting Started</h4>
                        <p style="margin-bottom: 10px;">Please upload an Excel file with the following headers:</p>
                        <ul style="margin-left: 20px; margin-bottom: 15px;">
                            <li><strong>Date</strong> — The date of the exchange rate (YYYY-MM-DD)</li>
                            <li><strong>Base</strong> — Base currency code (e.g., ZAR)</li>
                            <li><strong>Source</strong> — Source currency code (e.g., USD)</li>
                            <li><strong>User Rate</strong> — The rate to validate</li>
                        </ul>
                        <p style="opacity: 0.7; font-size: 0.9rem;">
                            The tool will compare your rates against official sources and flag any that exceed the threshold.
                        </p>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            # State 2: File uploaded - Show preview and generate button
            st.success(f"✅ File uploaded: **{uploaded_file.name}**")
            
            # Placeholder for file preview (backend will handle actual parsing)
            st.markdown('''
                <div class="results-placeholder" style="height: 300px;">
                    <p>File preview will appear here after backend integration.</p>
                </div>
            ''', unsafe_allow_html=True)
            
            # Generate Audit Button (placeholder - backend logic to be added by Agent A)
            st.button(
                "🚀 Generate Audit",
                type="primary",
                use_container_width=True,
                help="Click to run the audit against official exchange rate sources."
            )
