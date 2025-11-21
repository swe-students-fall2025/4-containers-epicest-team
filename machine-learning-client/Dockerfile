# Use a lightweight Python image
FROM python:3.10-slim
# Keep Python from writing .pyc files and use unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# FS setup
ENV AUDIO_DIR /tmp/audio_uploads
# Install system dependencies needed for sounddevice / soundfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libportaudio2 \
        libsndfile1 \
        ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Set the working directory inside the container
WORKDIR /app

# Set PYTHONPATH so tests can import modules
ENV PYTHONPATH=/app

# Copy Pipfile and Pipfile.lock first
COPY Pipfile Pipfile.lock ./

# Install dependencies using pipenv
RUN pipenv install --deploy --system

# Copy the rest of the ML client code
COPY . .

RUN mkdir -p ${AUDIO_DIR}

EXPOSE 5001

# Default command: run the ML client main script
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
