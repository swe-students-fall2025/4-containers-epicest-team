import speech_recognition as sr

def record_password(
    output_path: str = "password_attempt.wav",
    phrase_time_limit: int = 5,
) -> None:
    """Record from the default microphone and save as a WAV file."""
    recognizer = sr.Recognizer()

    # Use the default system microphone
    with sr.Microphone() as source:
        print("Calibrating for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        print(f"Speak your password now (listening up to {phrase_time_limit} seconds)...")
        audio = recognizer.listen(source, phrase_time_limit=phrase_time_limit)

    # We are NOT doing any recognition here, just saving the raw audio
    wav_bytes = audio.get_wav_data()
    with open(output_path, "wb") as f:
        f.write(wav_bytes)

    print(f"Saved recording to {output_path}")

if __name__ == "__main__":
    record_password()
