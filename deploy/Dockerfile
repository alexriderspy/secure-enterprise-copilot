FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HUB_OFFLINE=1 PYTHONWARNINGS=ignore TOKENIZERS_PARALLELISM=false
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app /data   # the only writable place
WORKDIR /app

# the CPU-only PyTorch wheel: no GPU libraries to download or ship
COPY deploy/requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
 && pip install -r requirements.txt

COPY kb kb
COPY app app
COPY data/fixtures data/fixtures
COPY deploy/egress_check.py deploy/egress_check.py
USER app
EXPOSE 8000
CMD ["sh", "-c", "python -m kb.ingest && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
