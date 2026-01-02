# Forex Rate Extractor

A Python-based Streamlit application to extract and audit historical foreign exchange rates using the Twelve Data API.

## Features

### 📊 Rate Extraction
*   **Historical Data**: Fetches exchange rates for requested currency pairs and date ranges.
*   **Cross-Rate Calculation**: Automatically calculates cross-rates (e.g., ZAR → BWP) via USD.
*   **Export Options**: Download results as CSV or Excel.

### 🔍 Audit & Reconciliation
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
│   ├── core/auth.py               # API key authentication (cookie-based)
│   └── ui/styles.css              # Custom CSS styling
│
├── logic/                         # Backend Business Logic
│   ├── facade.py                  # Rate extraction interface
│   ├── auditor.py                 # Audit & reconciliation module
│   ├── api_client.py              # Twelve Data API client
│   ├── data_processor.py          # Data transformation
│   └── utils.py                   # CSV/Excel export helpers
│
├── Dockerfile                     # Container definition
├── docker-compose.yml             # Container orchestration
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

### High-Level Architecture

```mermaid
graph TD
    User([User]) <--> UI[Streamlit UI (code/app.py)]
    UI --> Facade[Logic Facade (logic/facade.py)]
    
    subgraph "Business Logic Layer"
        Facade --> Auditor[Auditor Module]
        Facade --> Client[API Client (logic/api_client.py)]
        Auditor --> Client
    end
    
    Client -- "HTTPS (Rate Limited)" --> TwelveData[((Twelve Data API))]
    
    classDef component fill:#d4ebf2,stroke:#005580,stroke-width:1px;
    class UI,Facade,Auditor,Client component;
```


## Setup

1.  **Get an API Key**: Sign up at [Twelve Data](https://twelvedata.com/) (Free tier available).
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running Locally
```bash
cd code
streamlit run app.py
```

### Running with Docker
```bash
docker-compose up --build
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

## Security

- API keys are stored in **browser cookies** (7-day expiry)
- No API keys are saved on the server
- `.env` files are gitignored

## API Rate Limits (Twelve Data Free Tier)

- 8 API calls per minute
- 800 API calls per day

The application implements smart throttling to respect these limits.

## Dependencies

```
streamlit
pandas
openpyxl
requests
extra-streamlit-components
watchdog
```
