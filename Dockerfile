FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DECIDER_DEVICE=cpu \
    HF_HOME=/home/lurker/.cache/huggingface \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-deploy.txt ./

# Install the official CPU-only PyTorch wheel first so pip does not pull CUDA
# runtime packages into this CPU deployment image.
RUN python -m pip install --no-cache-dir \
        torch==2.7.1 \
        --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir \
        --constraint requirements-deploy.txt \
        --requirement requirements.txt

COPY . .

RUN groupadd --system lurker \
    && useradd --system --gid lurker --create-home lurker \
    && mkdir -p /app/data /app/results "${HF_HOME}" \
    && chown -R lurker:lurker /app/data /app/results /home/lurker

USER lurker

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)); raise SystemExit(0 if data.get('status') == 'ok' else 1)"

CMD ["sh", "-c", "exec uvicorn src.lurker.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
