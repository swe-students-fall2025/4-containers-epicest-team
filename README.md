![Lint-free](https://github.com/swe-students-fall2025/4-containers-epicest-team/actions/workflows/lint.yml/badge.svg)
![ML Client CI](https://github.com/swe-students-fall2025/4-containers-epicest-team/actions/workflows/ml-client-ci.yml/badge.svg)
![Web App CI](https://github.com/swe-students-fall2025/4-containers-epicest-team/actions/workflows/web-app-ci.yml/badge.svg)

# Codebreaker - Containerized Speech Recognition App

A multi-container application that combines speech recognition, web interface, and database storage. Users attempt to guess secret passphrases using voice input, with a local machine learning client handling speech-to-text transcription.

## Team Members

- [Amira Adum](https://github.com/amiraadum)
- [Daniel Lee](https://github.com/danielleesignup)
- [Ezra Shapiro](https://github.com/ems9856-lgtm)
- [Jasir Nawar](https://github.com/jawarbx)
- [Omer Hortig](https://github.com/ohortig)

## Architecture Overview

- **Web App → ML Client**: The web app sends audio files to the ML client's API endpoint for transcription
- **Web App → MongoDB**: Stores user data, game states, secrets, and metadata
- **ML Client → MongoDB**: Stores transcription attempts and results
- **Docker Networking**: All services communicate via service names

## Deployment Options

You can run this application in two ways:

### Option A: All Services in Docker (including MongoDB)

Run all three services (web app, ML client, and MongoDB) locally using Docker Compose.

### Option B: Cloud Database (MongoDB Atlas)

Run the web app and ML client locally in Docker, but connect to a cloud-hosted MongoDB Atlas database.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) 

Verify your installation:

```bash
docker --version
docker-compose --version
```

---

## Setup Instructions

### Step 1: Clone the Repository

```bash
git clone https://github.com/swe-students-fall2025/4-containers-epicest-team
cd 4-containers-epicest-team
```

### Step 2: Configure Environment Variables

Create your environment configuration file from the provided env.example:

```bash
cp env.example .env
```

Edit the `.env` file based on your chosen deployment option:

#### For Option A (Local Docker MongoDB):

Use the default values in `.env` or customize the credentials:

```bash
# Local Docker MongoDB configuration
MONGO_URI=mongodb://admin:password123@mongodb:27017/passworddb?authSource=admin
MONGO_DB=passworddb
MONGO_USER=admin
MONGO_PASS=admin

# Flask secret key (change this!)
SECRET_KEY=your-super-secret-key-change-this-in-production

# ML Client URL (automatic with docker-compose)
ML_CLIENT_URL=http://machine-learning-client:5001
```

Change `SECRET_KEY` to a secure random string. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### For Option B (MongoDB Atlas):

1. Ensure you have a cluster, database user, and network access set up properly in MongoDB Atlas
2. Obtain your connection string from MongoDB Atlas
3. Update your `.env` file:

```bash
# MongoDB Atlas configuration
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/passworddb?retryWrites=true&w=majority
MONGO_DB=passworddb
MONGO_USER=<your-atlas-username>
MONGO_PASS=<your-atlas-password>

# Flask secret key
SECRET_KEY=your-super-secret-key-change-this-in-production

# ML Client URL
ML_CLIENT_URL=http://machine-learning-client:5001
```

### Step 3: Start the Services

#### For Option A (All Services in Docker):

Start all three containers:

```bash
docker-compose up --build
```

#### For Option B (MongoDB Atlas):

Modify `docker-compose.yaml` to comment out the `mongodb` service:

```yaml
# Comment out or remove the mongodb service
# mongodb:
#   image: mongo:latest
#   ...
```

Then start the web app and ML client:

```bash
docker-compose up --build web_app machine-learning-client
```

## Using the Application

### First Time Setup

1. Navigate to `http://localhost:3000`
2. Click "Register" to create a new account
3. Log in with your credentials

### Playing the Game

1. View the hint for the current secret phrase
2. Click the microphone button to record your guess
3. Speak clearly and click "Stop Recording"
4. The ML client will transcribe your speech
5. Submit your guess (you have 3 attempts per secret)
6. If you guess correctly, you can create a new secret for others!