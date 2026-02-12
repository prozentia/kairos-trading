# Kairos Trading - AI Agent
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY adapters/ adapters/
COPY ai_agent/ ai_agent/

CMD ["python", "-m", "ai_agent.main"]
