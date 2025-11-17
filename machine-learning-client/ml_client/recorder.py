"""Microphone recording utilities for the ML client."""

# pylint: disable=invalid-name

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import sounddevice as sd  # type: ignore[import]

    SD_IMPORT_ERROR: Optional[BaseException] = None
except OSError as err:  # PortAudio library not found
    sd = None  # type: ignore[assignment]
    SD_IMPORT_ERROR = err

import soundfile as sf  # type: ignore[import]

DEFAULT_SAMPLE_RATE = 16000  # 16 kHz, good enough for speech
DEFAULT_CHANNELS = 1  # mono audio
DEFAULT_DURATION_SECONDS = 4  # seconds

DEFAULT_OUTPUT_DIR = Path("recordings")


def record_clip(
    *,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    """Record audio from the default microphone and save as a .wav file."""
    # If sounddevice/PortAudio is not available (e.g. on CI), fail cleanly
    if sd is None:
        msg = "Audio recording is not available: PortAudio / sounddevice is missing."
        raise RuntimeError(msg) from SD_IMPORT_ERROR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    file_path = output_dir / f"recording-{timestamp}.wav"

    num_frames = int(duration_seconds * sample_rate)

    print(f"[recorder] Recording {duration_seconds:.1f}s of audio...")
    recording = sd.rec(
        num_frames,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
    )
    sd.wait()
    print(f"[recorder] Recording complete. Saving to {file_path}")

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
