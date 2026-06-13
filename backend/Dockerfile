FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compiling psycopg2 and general helper utilities
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose backend API port
EXPOSE 8000

# Start server dynamically binding to PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
