"""
Machine learning client which records speech, transcribes it, and writes to database
"""

from __future__ import annotations

import datetime
import os
import shutil
import traceback
import uuid
from pathlib import Path

import pymongo
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile

from ml_client import speech_analysis

PARENT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = PARENT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")
AUDIO_DIR = "/tmp/audio_uploads"
os.makedirs(AUDIO_DIR, exist_ok=True)

app = FastAPI(title="ML Client")

try:
    mongo_client = pymongo.MongoClient(
        MONGO_URI, username=MONGO_USER, password=MONGO_PASS
    )
    db = mongo_client[MONGO_DB]
except (TypeError, AttributeError, pymongo.errors.PyMongoError) as e:
    print("Could not connect to MongoDB at startup:", e)
    mongo_client = None
    db = None

app.state.model = None


@app.on_event("startup")
def startup_event():
    """Load model on start of ml client and keep in memory"""
    try:
        print("[ml-client] Loading model at startup...")
        app.state.model = speech_analysis.load_whisper_model()
        print("[ml-client] Model loaded.")
    except RuntimeError as e:
        print("[ml-client] Model load failed:", e)
        traceback.print_exc()
        app.state.model = None


@app.post("/transcribe")
def transcribe(audio: UploadFile = File(...), user_id: str = Form(...)):
    """
    Endpoint that transcribes audio recording \
            and stores metadata into MongoDB. 
    Returns transcription and metadata and records it in DB 
    """
    try:
        filename = f"{uuid.uuid4()}.webm"
        temp_path = os.path.join(AUDIO_DIR, filename)
        audio.file.seek(0)
        # Save uploaded file
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        print("Saved file size:", os.path.getsize(temp_path))
        # Transcribe
        words, success = speech_analysis.transcribe_audio(temp_path, app.state.model)
        doc = {
            "user_id": user_id,
            "audio_path": temp_path,
            "transcription_text": words,
            "transcription_words": words.split(),
            "transcription_success": success,
            "timestamp": datetime.datetime.utcnow(),
        }

        db["attempts"].insert_one(doc)
    except (AttributeError, pymongo.errors.PyMongoError) as e:
        traceback.print_exc()

        print("[ml-client] Error during transcription: ", e)

    # 4. Return summary to web app
    return {
        "transcription": words,
        "transcription_words": doc["transcription_words"],
        "transcription_success": success,
        "audio_path": temp_path,
    }
