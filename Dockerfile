FROM python:3.11-slim

# Install system dependencies including ffmpeg and build dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY static/ ./static/

# Create necessary directories
RUN mkdir -p uploads outputs temp

# Expose port (Render will set PORT env var)
ENV PORT=8000
EXPOSE 8000

# Run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
