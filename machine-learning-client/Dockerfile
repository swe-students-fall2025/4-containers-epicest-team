# Use a lightweight Python image
FROM python:3.10-slim
# Keep Python from writing .pyc files and use unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Install system dependencies needed for sounddevice / soundfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libportaudio2 \
        libsndfile1 \
        ffmpeg && \
    rm -rf /var/lib/apt/lists/*
# Set the working directory inside the container
WORKDIR /app
# Copy Pipenv files first so Docker can cache dependency install
COPY Pipfile Pipfile.lock ./
# Install Python dependencies using Pipenv into the system env
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy --ignore-pipfile
# Copy the rest of the ML client code
COPY . .
# Make sure the recordings directory exists
RUN mkdir -p recordings
# Default command: run the ML client main script
CMD ["python", "main.py"]
