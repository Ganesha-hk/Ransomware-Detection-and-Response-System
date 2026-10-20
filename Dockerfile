FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && useradd --create-home --uid 10001 rdrs && mkdir -p /runtime && chown rdrs:rdrs /runtime /app
COPY --chown=rdrs:rdrs . .
USER rdrs
ENV RDRS_CONFIG=/app/config.docker.yaml PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "-m", "app.main", "--config", "config.docker.yaml"]
