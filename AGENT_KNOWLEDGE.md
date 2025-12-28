# Forex Rate Extractor - Agent Knowledge Base

> **Last Updated:** 2025-12-28  
> **Purpose:** Comprehensive handoff document for AI agents working on this project.

---

## 🎯 Project Overview

A **Streamlit-based web application** that extracts historical foreign exchange rates from the [Twelve Data API](https://twelvedata.com/). Users can specify base currencies and date ranges, then download results as CSV or Excel.

---

## 📁 Project Structure

```
Forex Rate Extractor/
├── code/                          # Streamlit Frontend
│   ├── app.py                     # Main Streamlit app (entry point)
│   ├── run_app.sh                 # Shell script to launch the app
│   ├── requirements.txt           # Frontend-specific dependencies
│   ├── favicon_clean.png          # App favicon
│   ├── core/
│   │   └── auth.py                # API key authentication (cookies + session)
│   ├── ui/
│   │   └── styles.css             # Custom CSS styling (dark theme, glassmorphism)
│   └── .streamlit/                # Streamlit config
│
├── logic/                         # Backend Business Logic
│   ├── __init__.py                # Exports: ForexRateFetcher, process_data
│   ├── api_client.py              # Twelve Data API client with rate limiting
│   ├── data_processor.py          # Data transformation and validation
│   ├── auditor.py                 # Rate validation and auditing logic
│   ├── facade.py                  # Simplified interface: get_rates()
│   └── utils.py                   # Helpers: convert_df_to_csv/excel
│
├── requirements.txt               # Root-level dependencies
├── Dockerfile                     # Docker containerization
├── docker-compose.yml             # Docker compose config
├── README.md                      # User documentation
└── .api_key                       # Stored API key (gitignored ideally)
```

---

## 🔑 Key Components

### 1. Authentication (`code/core/auth.py`)
- Uses `extra_streamlit_components.CookieManager` for persistent API key storage
- **Session state priority**: `st.session_state["api_key"]` > cookies
- **force_logout flag**: Set to `True` when user clicks logout to ensure modal shows
- Cookies expire after 7 days

```python
# Key functions:
get_cookie_manager()     # Returns CookieManager with unique key
get_api_key(cm)          # Gets key from session or cookie
set_api_key(cm, key)     # Saves to both session and cookie
clear_api_key(cm)        # Sets force_logout=True, clears session & cookie
```

### 2. Main App (`code/app.py`)
- **Page config**: Wide layout, custom favicon, CSS loaded from `ui/styles.css`
- **Auth flow**: If no API key → show modal; else → show main app
- **Two-column layout**: Left (inputs), Right (results)
- **Imports logic module** via `sys.path.insert()` to find parent directory

### 3. Backend Logic (`logic/`)
- **`facade.py`**: Entry point → `get_rates(api_key, bases, start, end)` returns DataFrame
- **`api_client.py`**: Handles API calls with rate limiting (8 requests/min for free tier)
- **`data_processor.py`**: Cleans, validates, and transforms API responses
- **`auditor.py`**: Cross-validates rates against expected values

---

## 🚀 How to Run

```bash
cd code
./run_app.sh
# OR
streamlit run app.py
```

**Default URL**: `http://localhost:8501`

---

## ⚠️ Known Issues & Solutions

| Issue | Solution |
|-------|----------|
| Logout doesn't work | Fixed: Added `force_logout` session flag in `auth.py` |
| Cookie manager async issues | Use session state as primary, cookie as backup |
| `logic` module not found | `sys.path.insert(0, parent_dir)` in `app.py` line 6 |
| `extra-streamlit-components` missing | `pip install extra-streamlit-components` |

---

## 🔧 Configuration

### API Rate Limits (Twelve Data Free Tier)
- 8 API calls per minute
- 800 API calls per day
- The `api_client.py` implements throttling to respect these limits

### Supported Currencies
All major currencies: USD, EUR, GBP, ZAR, CHF, JPY, CAD, AUD, NZD, etc.

---

## 📦 Dependencies

```
streamlit
pandas
openpyxl
requests
extra-streamlit-components
```

---

## 🎨 UI Design

- **Theme**: Dark with gradient accents (green to blue)
- **Modal**: Glassmorphism-style API key input
- **Layout**: Responsive two-column design
- **Styling**: All custom CSS in `ui/styles.css`

---

## 🧪 Testing

```bash
# Unit tests
python test_backend.py
python test_auditor.py
```

---

## 📝 Recent Changes (Dec 2025)

1. **Fixed authentication flow** - Logout button now works correctly
2. **Code cleanup** - Removed debug prints, unused imports
3. **Security** - API keys use session/cookies, not hardcoded
4. **Dependencies** - Updated `requirements.txt`

---

## 💡 Tips for Agents

1. **Always use absolute paths** when importing logic: `sys.path.insert(0, ...)`
2. **Cookie manager quirks**: The component sometimes returns stale values; always check session state first
3. **Streamlit reruns**: Use `st.rerun()` after state changes, not page redirects
4. **Testing auth**: Use `force_logout` flag to simulate fresh user experience
5. **Run from `/code` directory** for relative paths to work (`ui/styles.css`, `favicon_clean.png`)
