# pylint: disable=wrong-import-position, import-error

import sys
from pathlib import Path
import io

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from web_app.app import transcribe_audio


def test_transcribe_audio_stub():
    """transcribe_audio should return the stub string."""
    fake_file = io.BytesIO(b"dummy audio data")
    result = transcribe_audio(fake_file)
    assert result == "example guess from audio"
