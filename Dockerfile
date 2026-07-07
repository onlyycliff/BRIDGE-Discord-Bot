FROM python:3.12-slim

WORKDIR /app

# Runtime dependencies (mostly psycopg2-binary for optional sync use;
# asyncpg is installed from requirements.txt).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "dashboard:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "120", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
