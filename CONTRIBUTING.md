# Contributing to Forex Rate Extractor

Thank you for your interest in improving the Forex Rate Extractor! This document provides guidelines for developers to ensure code quality and consistency.

## 🛠️ Development Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd Forex\ Rate\ Extractor
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    # Install app dependencies
    pip install -r requirements.txt
    
    # Install test/dev dependencies
    pip install -r requirements-test.txt
    ```

4.  **Set up Pre-commit (Optional but Recommended)**:
    Ensure you run `flake8` before committing to catch linting errors.

## 🧪 Testing Standards

We use `pytest` for all testing. Strict quality gates are enforced via `pytest.ini`.

### Running Tests
To run the full suite:
```bash
pytest
```

To run only unit tests (skipping integration tests):
```bash
pytest -m "not integration"
```

To run with coverage:
```bash
pytest --cov=logic tests/
```

### Writing Tests
*   All new logic must have accompanying unit tests in `tests/`.
*   Use `pytest-mock` to avoid hitting real APIs during tests.
*   **Do not** store real API keys in test files; use mocks or environment variables.

## 🎨 Coding Standards

*   **Style**: Follow PEP 8 guidelines.
*   **Linting**: We use `flake8`. Run `flake8 .` to check for issues.
*   **Docstrings**: All public functions and classes must have clear docstrings explaining:
    *   Purpose
    *   Arguments (type and description)
    *   Return values
*   **Type Hinting**: Use Python type hints (`typing` module) for function signatures.

## 🔄 Pull Request Process

1.  Create a new branch for your feature or fix: `feature/my-new-feature` or `fix/bug-id`.
2.  Ensure all tests pass locally.
3.  Update the `README.md` if you are changing user-facing functionality.
4.  Submit a Pull Request.

## 🤝 Architecture Overview

*   **Frontend**: `code/app.py` (Streamlit)
*   **Business Logic**: `logic/` (Python modules)
    *   `facade.py`: Main entry point for the UI.
    *   `api_client.py`: Handles Twelve Data API interactions and rate limiting.
    *   `auditor.py`: Logic for file processing and reconciliation.
*   **Data Flow**: User Input -> Streamlit UI -> Facade -> API Client -> Twelve Data API.
