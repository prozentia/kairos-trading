# Kairos Trading - Notification Service
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY adapters/ adapters/
COPY notifier/ notifier/

CMD ["python", "-m", "notifier.main"]
