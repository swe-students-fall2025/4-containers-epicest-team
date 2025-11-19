"""
Functionality to handle speech transcription and password checking
"""

import string

import whisper


def load_whisper_model(model_name: str = "small"):
    """
    Helper to load Whisper model

    Returns:
        whisper.model
    """
    try:
        print(f"[ml-client] Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name, in_memory=True, device="cpu")
        print("[ml-client] Whisper model loaded.")
        return model
    except RuntimeError as e:
        raise RuntimeError(
            f"[ml-client] Unable to load Whisper model {model_name}"
        ) from e


def transcribe_audio(audio_path: str, model) -> tuple[list[str], bool]:
    """
    Helper to run speech transcription

    Parameters:
    audio_path (str)
    model: (Whisper) loaded speech transcription model

    Returns:
    tuple[list[str], bool] regardless of transcription success
    If transcription success, return True
    """
    try:
        result = model.transcribe(audio_path)
        return (
            result["text"]
            .lower()
            .strip()
            .translate(str.maketrans("", "", string.punctuation))
            .strip(),
            True,
        )
    except (AttributeError, FileNotFoundError, ValueError, RuntimeError):
        return "Transcription Failed", False
