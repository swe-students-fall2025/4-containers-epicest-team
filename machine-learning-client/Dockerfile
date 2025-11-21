FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV AUDIO_DIR=/tmp/audio_uploads

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libportaudio2 \
        libsndfile1 \
        ffmpeg \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pipenv

WORKDIR /app
ENV PYTHONPATH=/app

COPY Pipfile Pipfile.lock ./

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pipenv install --deploy --system

COPY . .

RUN mkdir -p ${AUDIO_DIR}

EXPOSE 5001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
