FROM python:3.11-slim

# Runtime ffmpeg only — avoid libav*-dev so pip won't compile PyAV against new FFmpeg headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Prefer binary wheels for av (faster-whisper dependency); then the rest
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir "av>=12.3.0" --only-binary=:all: \
 && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/

RUN mkdir -p uploads outputs temp

ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
