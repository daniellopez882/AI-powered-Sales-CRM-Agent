# Use official lightweight Python image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR 1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create directory for SQLite database
RUN mkdir -p /app/data

# Environment variable defaults
ENV ENVIRONMENT=production
ENV PORT=8000
ENV LOG_LEVEL=INFO
ENV DATABASE_URL=sqlite:////app/data/salesiq.db

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "api.main"]
