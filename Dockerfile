FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 5000

# IMPORTANT: --workers MUST stay at 1. The Discord bot thread is started once
# at module import via _ensure_bot_started() in dashboard.py. Multiple workers
# would each spawn a bot process logging in with the same token — Discord will
# kick one, or both will process the same interactions causing double-votes.
CMD ["gunicorn", "dashboard:app", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
