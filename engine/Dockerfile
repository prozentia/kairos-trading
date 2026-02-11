# Kairos Trading - Trading Engine
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY adapters/ adapters/
COPY engine/ engine/

CMD ["python", "-m", "engine.main"]
