# Forex Rate Extractor

A Python-based tool to extract historical foreign exchange rates using the Twelve Data API.

## Features
*   **Historical Data**: Fetches the past 365 days of exchange rates for requested pairs.
*   **Cross-Rate Calculation**: Automatically calculates cross-rates (e.g., ZAR -> BWP) via USD if direct pairs are unavailable.
*   **Excel Export**: Saves data to `Forex_Output.xlsx` with clean formatting.
*   **Interactive CLI**: Simple prompts for API key, currency pairs, and date range.

## Setup

1.  **Get an API Key**: Sign up at [Twelve Data](https://twelvedata.com/) to get your free API key.
2.  **Install Python**: Ensure Python 3 is installed on your system.
3.  **Install Dependencies**:
    ```bash
    pip install -r code/requirements.txt
    ```

## Usage

### Windows
Double-click `run_forex_extractor.bat`.

### Mac / Linux
Double-click `run_forex_extractor.command` or run in terminal:
```bash
./run_forex_extractor.command
```

### First Run
1.  Enter your Twelve Data API Key when prompted. It will be saved locally to `.api_key`.
2.  Enter the currency pairs you need (e.g., `USD/ZAR` or `ZAR, USD`).
3.  Press Enter to fetch data for the past year ending today.

## Project Structure
*   `code/`: link to source code (main script and core modules).
*   `Forex_Output.xlsx`: The generated output file (created after running).
*   `.api_key`: Local file storing your API key (not ignored by git, keep it safe!).

## Core Modules
*   **ConfigManager**: Handles user input and configuration.
*   **APIFetcher**: Manages API requests and throttling.
*   **DataSerializer**: Processes data and handles file I/O.
