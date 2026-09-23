FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Prefer the pinned lock file when it is committed, so the image matches the
# environment the project was actually tested in. Falls back to the ranges.
COPY requirements.txt ./
COPY requirements.lock.tx[t] ./
RUN if [ -s requirements.lock.txt ]; then \
      pip install --no-cache-dir -r requirements.lock.txt \
        || { echo "Lock file does not resolve on this Python, falling back to ranges."; \
             pip install --no-cache-dir -r requirements.txt; }; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)"

ENTRYPOINT ["sh", "scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
