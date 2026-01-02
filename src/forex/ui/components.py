"""
Reusable UI Components for Streamlit App

Contains extracted functions to reduce code duplication and improve testability.
"""

import os

import pandas as pd
import streamlit as st

# Get directory of this file for relative path resolution
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_css(file_name: str) -> None:
    """
    Loads a CSS file and injects it into the Streamlit app.

    Args:
        file_name: Path to CSS file relative to the code/ directory.
    """
    # Resolve path relative to code/ directory (parent of ui/)
    code_dir = os.path.dirname(_CURRENT_DIR)
    file_path = os.path.join(code_dir, file_name)

    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found at: {file_path}")


def render_download_buttons(df: pd.DataFrame, prefix: str, convert_to_csv, convert_to_excel) -> None:
    """
    Renders CSV and Excel download buttons for a DataFrame.

    Args:
        df: The DataFrame to make downloadable.
        prefix: Filename prefix (e.g., 'forex_rates', 'audit_report').
        convert_to_csv: Function to convert DataFrame to CSV bytes.
        convert_to_excel: Function to convert DataFrame to Excel bytes.
    """
    # Spacer
    st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

    # Create columns with specific widths
    dl_cols = st.columns([107, 115, 200], gap="small")

    csv_data = convert_to_csv(df)
    excel_data = convert_to_excel(df)

    with dl_cols[0]:
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name=f"{prefix}.csv",
            mime="text/csv",
            key=f"dl_csv_{prefix}",
        )
    with dl_cols[1]:
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name=f"{prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_excel_{prefix}",
        )


def render_results_placeholder(message: str) -> None:
    """
    Renders a placeholder message in the results area.

    Args:
        message: The placeholder message to display.
    """
    st.markdown(
        f"""
        <div class="results-placeholder">
            <p>{message}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )
