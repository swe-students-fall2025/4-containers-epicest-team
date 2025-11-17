import whisper
import string


def load_whisper_model(model_name: str):
    """
    Helper to load local model for speech transcription

    Parameters:
    model_name (str)

    Returns:
    whisper.model or None if model does not exist
    """
    return whisper.load_model(model_name, device="cpu")


def transcribe_audio(
    audio_path: str, model_name: str = "small"
) -> tuple[list[str], bool]:
    """
    Helper to run speech transcription

    Parameters:
    audio_path (str)
    model_name (str)

    Returns:
    tuple[list[str], bool] regardless of transcription success
    If transcription success, return True
    """
    model = load_whisper_model(model_name)
    try:
        result = model.transcribe(audio_path)
        return (
            result["text"]
            .lower()
            .strip()
            .translate(str.maketrans("", "", string.punctuation))
            .split(),
            True,
        )
    except Exception as e:
        return ["Transcription Failed"], False


def check_password_in_transcription(
    password: str, query: list[str], transcription_success: bool
) -> bool:
    """
    Helper to check

    Parameters:
    password (str)
    query (list of str)
    transcription_failed (bool)

    Returns:
    bool if transcription did not fail, None if transcription failed
    """
    if not transcription_success:
        return None
    else:
        return password.lower().strip() in query
