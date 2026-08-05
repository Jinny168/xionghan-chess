FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 MAX_ONLINE_GAMES=200 AI_DEFAULT_DIFFICULTY=medium AI_TIME_SCALE=1.0 RECONNECT_GRACE_SECONDS=90
WORKDIR /app
COPY requirements/core.txt requirements/core.txt
COPY requirements/server.txt requirements/server.txt
RUN pip install --no-cache-dir -r requirements/server.txt
COPY pyproject.toml ./
COPY src ./src
COPY web ./web
RUN pip install --no-cache-dir --no-deps -e .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/health',timeout=3)"
CMD ["sh", "-c", "uvicorn xionghan_chess.service.app:app --host 0.0.0.0 --port ${PORT} --workers 1"]
