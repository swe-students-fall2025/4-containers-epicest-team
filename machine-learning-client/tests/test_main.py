"""Tests for the ML client main entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure the project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import main as run_main  # type: ignore[import]  # pylint: disable=wrong-import-position


@patch("main.record_clip")
def test_main_calls_record_clip_and_prints_summary(mock_record_clip, capsys):
    """main() should call record_clip and print a short summary."""
    mock_record_clip.return_value = {
        "file_path": "recordings/fake.wav",
        "duration_seconds": 4.0,
        "sample_rate": 16_000,
        "channels": 1,
        "created_at": None,
    }
    run_main()
    # Ensure we called record_clip exactly once
    mock_record_clip.assert_called_once()
    # Capture stdout and check for the summary lines
    captured = capsys.readouterr()
    out = captured.out
    assert "[main] Recording finished." in out
    assert "recordings/fake.wav" in out
