FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN adduser --system --group --no-create-home streamlit

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Change ownership to non-root user
RUN chown -R streamlit:streamlit /app

# Expose Streamlit port
EXPOSE 8501

# Switch to non-root user
USER streamlit

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Command to run the app
CMD ["streamlit", "run", "code/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
