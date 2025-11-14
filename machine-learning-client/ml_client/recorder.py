"""
This  is responsible for
- recording audio from the default microphone
- saves as a .wav file on disk- local 
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, Any

import sounddevice as sd
import soundfile as sf

# Default recording settings — these are cross-platform.
DEFAULT_SAMPLE_RATE = 16_000  
DEFAULT_CHANNELS = 1          
DEFAULT_DURATION_SECONDS = 4  


DEFAULT_OUTPUT_DIR = Path("recordings")


def record_clip(
    *,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    
    # Make sure the directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use timestamp in filename so each recording is unique
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    file_path = output_dir / f"recording-{timestamp}.wav"

    # Number of frames to record
    num_frames = int(duration_seconds * sample_rate)

    print(f"[recorder] Recording {duration_seconds:.1f}s of audio...")
    recording = sd.rec(
        num_frames,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
    )
    sd.wait()  # Blocks until recording is finished
    print(f"[recorder] Recording complete. Saving to {file_path}")

    # Save the numpy array to a .wav file
    sf.write(str(file_path), recording, sample_rate)

    created_at = dt.datetime.utcnow()

    info: Dict[str, Any] = {
        "file_path": str(file_path),
        "duration_seconds": float(duration_seconds),
        "sample_rate": int(sample_rate),
        "channels": int(channels),
        "created_at": created_at,
    }

    print(
        "[recorder] Saved file:",
        info["file_path"],
        "| duration:",
        info["duration_seconds"],
        "s",
    )

    return info