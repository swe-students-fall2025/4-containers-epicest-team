from __future__ import annotations
from ml_client.recorder import record_clip
from ml_client.speech_analysis import transcribe_audio
from dotenv import load_dotenv
from pathlib import Path
import os
import pymongo
import sounddevice as sd

PARENT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH  = PARENT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

def main() -> None:
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB]
    except Exception as e:
        print("Could not connection to database")

    """Record one audio clip and print where it was saved."""

    # Get default sample rate from input device
    sample_rate = int(sd.query_devices(sd.default.device[0])['default_samplerate'])

    info = record_clip(sample_rate = sample_rate)
    print("\n[main] Recording finished.")
    print("[main] File:", info["file_path"])
    print("[main] Duration (s):", info["duration_seconds"])
    print("[main] Sample rate:", info["sample_rate"])
    print("[main] Channels:", info["channels"])

    transcription, transcription_success = transcribe_audio(info['file_path'])
    info['transcription_success'] = transcription_success
    info['transcription'] = transcription
    print(f"Transcription: {info['transcription']}")
    print(f"Transcription Success: {info['transcription_success']}")
    try:
        db['attempts'].insert_one(info)
    except Exception as e:
        print("Could not write to database", e)

if __name__ == "__main__":
    main()
