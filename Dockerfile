FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY tools ./tools
RUN python tools/make_sample_recordings.py
ENV PYTHONUNBUFFERED=1
# CasparCG runs on the host: on Docker Desktop use ENGINE_HOST=host.docker.internal
ENV ENGINE_HOST=host.docker.internal
CMD ["python", "-m", "app.main"]
