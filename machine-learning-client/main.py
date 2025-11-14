from __future__ import annotations

from ml_client.recorder import record_clip


def main() -> None:
    """Record one audio clip and print where it was saved."""
    info = record_clip()
    print("\n[main] Recording finished.")
    print("[main] File:", info["file_path"])
    print("[main] Duration (s):", info["duration_seconds"])
    print("[main] Sample rate:", info["sample_rate"])
    print("[main] Channels:", info["channels"])


if __name__ == "__main__":
    main()
