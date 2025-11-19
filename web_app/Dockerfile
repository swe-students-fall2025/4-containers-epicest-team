#use a lightweight Python image
FROM python:3.11-slim

#prevent Python from writing .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#set work directory inside the container
WORKDIR /app

#install pipenv and dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

# Install OpenSSL (needed for certificate generation)
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# Create directory for certificates
RUN mkdir -p /certs

# Generate self-signed certificate and private key at build time
RUN openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout /certs/key.pem \
    -out /certs/cert.pem \
    -subj "/CN=localhost"

#copy the rest of the app code
COPY . .

#flask app listens on port 3000
EXPOSE 3000

#run the web app
CMD ["python", "app.py"]
