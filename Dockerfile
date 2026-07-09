FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY spec2schematic ./spec2schematic
COPY service ./service
COPY examples ./examples

RUN pip install --no-cache-dir ".[dxf,service]"

EXPOSE 7860

# $PORT is honored when the host injects it (e.g. Render); otherwise default to
# 7860 (what Hugging Face Spaces' app_port metadata expects).
CMD ["/bin/sh", "-c", "uvicorn service.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
