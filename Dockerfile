# ---- Base image ----
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user to run the application
RUN groupadd --system appgroup && \
    useradd --system --no-log-init --gid appgroup appuser

# Set working directory
WORKDIR /app

# ---- Install system dependencies (if any) ----
# No extra system packages needed for our current stack.
# If you need libgl for opencv, uncomment the following line:
# RUN apt-get update && apt-get install -y --no-install-recommends libgl1-mesa-glx && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies (separate for caching) ----
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Application source ----
COPY app/ ./app/

# Switch to non-root user
USER appuser

# Expose the port the API listens on
EXPOSE 8000

# Health check (uses the /health endpoint once we build it)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]