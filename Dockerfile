FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app && useradd --system --gid app app
COPY taskmanager ./taskmanager
COPY frontend ./frontend
COPY wsgi.py ./
RUN mkdir -p /app/instance && chown -R app:app /app
USER app
EXPOSE 8000
# One worker keeps this starter's in-process Prometheus registry accurate.
CMD ["sh", "-c", "flask --app wsgi init-db && exec gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8000 wsgi:app"]
