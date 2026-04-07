FROM ubuntu:22.04

LABEL maintainer="mohammed-mutee"
LABEL description="SRE Sandbox — Single-container Hugging Face Spaces deployment"
LABEL version="2.0.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system services and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    postgresql \
    curl \
    htop \
    net-tools \
    sudo \
    iptables \
    procps \
    coreutils \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Enable execution of scripts
RUN chmod +x /app/scripts/*.sh

# Create backups of clean system configurations so /reset can restore them natively
RUN cp -a /etc/nginx /etc/nginx.bak && \
    cp /etc/resolv.conf /etc/resolv.conf.bak || true

# HF Spaces use port 7860
EXPOSE 7860

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -sf http://localhost:7860/health || exit 1

# Start the OpenEnv FastAPI Server (it will handle the tasks)
CMD service postgresql start || true; service nginx start || true; python3 -m server.app
