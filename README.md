# Forex Rate Extractor

A Python-based Streamlit application to extract and audit historical foreign exchange rates using the Twelve Data API.

## Features

### 📊 Rate Extraction
*   **Historical Data**: Fetches exchange rates for requested currency pairs and date ranges.
*   **Cross-Rate Calculation**: Automatically calculates cross-rates (e.g., ZAR → BWP) via USD.
*   **Export Options**: Download results as CSV or Excel.

### 🔍 Audit & Reconciliation (NEW)
*   **Rate Validation**: Upload your own rates file and compare against official Twelve Data API rates.
*   **Flexible Schema**: Supports various column naming conventions (Date, Base, Source, Rate).
*   **Variance Detection**: Marks rates as PASS or EXCEPTION based on configurable threshold.
*   **Testing Mode**: Use mock data to test without consuming API credits.
*   **Smart Rate Limiting**: Respects Twelve Data's free tier limits (8 req/min).

## Project Structure

```
Forex Rate Extractor/
├── code/                          # Streamlit Frontend
│   ├── app.py                     # Main app (Rate Extraction + Audit tabs)
│   ├── run_app.sh                 # Shell launcher
│   ├── requirements.txt           # Frontend dependencies
│   ├── core/auth.py               # API key authentication
│   └── ui/styles.css              # Custom CSS styling
│
├── logic/                         # Backend Business Logic
│   ├── facade.py                  # Rate extraction interface
│   ├── auditor.py                 # Audit & reconciliation module
│   ├── api_client.py              # Twelve Data API client
│   ├── data_processor.py          # Data transformation
│   └── utils.py                   # CSV/Excel export helpers
│
├── requirements.txt               # Root-level dependencies
├── dummy_data.csv                 # Sample data for testing audit
└── README.md                      # This file
```

## Setup

1.  **Get an API Key**: Sign up at [Twelve Data](https://twelvedata.com/) (Free tier available).
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

```bash
cd code
streamlit run app.py
# OR
./run_app.sh
```

**Default URL**: `http://localhost:8501`

### Rate Extraction
1. Enter base and source currencies (e.g., ZAR, USD)
2. Select date range
3. Click "Run Extraction"

### Audit & Reconciliation
1. Switch to the "Audit & Reconciliation" tab
2. Upload your Excel/CSV file with columns: Date, Base, Source, User Rate
3. Configure date format and variance threshold
4. Enable "Testing Mode" for initial testing (recommended)
5. Click "Generate Audit"

## Dependencies

```
streamlit
pandas
openpyxl
requests
extra-streamlit-components
watchdog
```

## API Rate Limits (Twelve Data Free Tier)

- 8 API calls per minute
- 800 API calls per day

The application implements smart throttling to respect these limits.
