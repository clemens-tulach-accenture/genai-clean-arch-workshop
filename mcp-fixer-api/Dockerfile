FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/app/
COPY knowledge-base/ /app/knowledge-base/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
RUN useradd -m -u 10001 appuser
USER appuser
EXPOSE 8000
ENV PYTHONUNBUFFERED=1 APP_MODE=http KB_DIR=/app/knowledge-base OPENAI_API_BASE=https://api.openai.com/v1
CMD ["/app/entrypoint.sh"]
