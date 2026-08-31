# ══════════════════════════════════════════════════════════════════════════════
# Aero Piston Engine Digital Twin - AI Service (Fusion ML)
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TORCH_HOME=/app/.torch \
    PIP_NO_CACHE_DIR=1

# Install system dependencies for PyTorch
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies with PyTorch CPU-only for smaller image
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/fusion_ml/models /app/data /app/logs

# Copy pre-trained models if they exist
# (In production, these would be mounted or copied during build)

# Expose ports
# 8766: AI service WebSocket (receives from simulator, broadcasts to backend)
EXPOSE 8766

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8766/health || exit 1

# Default command
CMD ["python", "-m", "fusion_ml.ai_service"]
