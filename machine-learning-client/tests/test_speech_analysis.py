"""Tests for speech analysis"""

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest
from ml_client.speech_analysis import (
    check_password_in_transcription,
    load_whisper_model,
    transcribe_audio,
)

TEST_WAV_PATH = Path(__file__).resolve().parent / "test_recordings" / "hello_there.wav"
EXPECTED_TRANSCRIPTION = ["hello", "there"]


@pytest.fixture
def model_name():
    """Fixture for model name to ensure consistent model use."""
    return "small"


@pytest.fixture
def password():
    """Fixture for password to ensure consistent model use."""
    return "there"


@pytest.fixture
def query():
    """Fixture for query to ensure consistent model use."""
    return ["hello", "there"]


def test_load_whisper_model(model_name):
    """
    Test if the model is loaded correctly.
    """
    model = load_whisper_model(model_name)
    assert (
        model is not None
    ), f"Model '{model_name}' should be loaded successfully as type {type(model)}"


def test_transcribe_audio(model_name):
    """
    Test transcription function to ensure correct text output.
    """
    assert TEST_WAV_PATH.exists(), f"The test WAV file {TEST_WAV_PATH} does not exist."
    transcribed_words, transcription_success = transcribe_audio(
        str(TEST_WAV_PATH), model_name
    )
    assert (
        transcription_success is True
    ), "Transcription failed, check wav file or if model loaded correctly"
    assert isinstance(
        transcribed_words, list
    ), "Transcription result should be a list of words."
    assert (
        len(transcribed_words) > 0
    ), "Transcription result should not be empty. Please check if the model try another model"
    assert (
        transcribed_words == EXPECTED_TRANSCRIPTION
    ), f"Expected {EXPECTED_TRANSCRIPTION} but got {transcribed_words}."


def test_password_check_return_types(password, query):
    """
    Test if password checker return correctly depending on transcription flag
    """
    password_in_successful_transcription = check_password_in_transcription(
        password, query, True
    )
    password_in_failed_transcription = check_password_in_transcription(
        password, query, False
    )
    assert isinstance(
        password_in_successful_transcription, bool
    ), "Transcriptions flagged as success must return bool on check"
    assert isinstance(
        password_in_failed_transcription, type(None)
    ), "Transcriptions flagged as failed must return None"


def test_password_check_success_output(password, query):
    """
    Test password checking logic
    """
    expected_success = check_password_in_transcription(password, query, True)
    assert isinstance(
        expected_success, bool
    ), "Transcriptions flagged as success must return bool on check"
    assert (
        expected_success is True
    ), "This check must be true, please check password checking logic"
