FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY spec2schematic ./spec2schematic
COPY service ./service
COPY examples ./examples

RUN pip install --no-cache-dir ".[dxf,service]"

EXPOSE 7860

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "7860"]
