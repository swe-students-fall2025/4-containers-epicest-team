"""Tests for the microphone recorder module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ml_client.recorder import record_clip, DEFAULT_SAMPLE_RATE, DEFAULT_CHANNELS


@patch("ml_client.recorder.sf")
@patch("ml_client.recorder.sd")
def test_record_clip_returns_info_and_calls_write(mock_sd, mock_sf, tmp_path):
    """record_clip should call sounddevice + soundfile and return a metadata dict."""
    # Make sd.rec return some fake "audio data"
    mock_sd.rec.return_value = ["fake-audio"]

    info = record_clip(
        duration_seconds=1.0,
        sample_rate=DEFAULT_SAMPLE_RATE,
        channels=DEFAULT_CHANNELS,
        output_dir=tmp_path,
    )
    # Ensure sounddevice.rec and sounddevice.wait were called
    mock_sd.rec.assert_called_once()
    mock_sd.wait.assert_called_once()

    # Ensure soundfile.write was called to save the file
    mock_sf.write.assert_called_once()
    args, _kwargs = mock_sf.write.call_args
    assert isinstance(args[0], str)  # first arg is file path as string
    assert args[1] == ["fake-audio"]
    assert args[2] == DEFAULT_SAMPLE_RATE

    # Check the returned info dict has expected keys and types
    assert "file_path" in info
    assert "duration_seconds" in info
    assert "sample_rate" in info
    assert "channels" in info
    assert "created_at" in info
    assert Path(info["file_path"]).suffix == ".wav"
    assert info["duration_seconds"] == 1.0
    assert info["sample_rate"] == DEFAULT_SAMPLE_RATE
    assert info["channels"] == DEFAULT_CHANNELS
