FROM python:3.11-slim

WORKDIR /app

# Install build tools and libolm3 (runtime) + libolm-dev (headers)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libolm3 \
    libolm-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install matrix-nio with e2e support
RUN pip install --upgrade pip

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "poc/websocket-poc.py"]