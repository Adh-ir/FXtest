import io

import pandas as pd


def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """
    Converts a DataFrame to CSV bytes.
    """
    return df.to_csv(index=False).encode("utf-8")


def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """
    Converts a DataFrame to Excel bytes.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Forex Rates")
    return output.getvalue()


def create_template_excel() -> bytes:
    """
    Creates a template Excel file with the required headers.
    """
    # Create empty DataFrame with required headers
    headers = ["Date", "Base Currency", "Source Currency", "User Rate"]
    df = pd.DataFrame(columns=headers)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()
