// Minimal UI hooks — no mic/ML yet.

const recordBtn = document.getElementById("record-btn");
const statusText = document.getElementById("status-text");
const guessText = document.getElementById("guess-text");
const resultMessage = document.getElementById("result-message");
const attemptsEl = document.getElementById("attempts-left");

//elements for "set new passphrase" UI 
const newPassphraseModal = document.getElementById("new-passphrase-modal");
const newPassphraseInput = document.getElementById("new-passphrase-input");
const setPassphraseBtn = document.getElementById("set-passphrase-btn");
const closePassphraseBtn = document.getElementById("close-passphrase-btn");

let isRecording = false;

// recording-related globals
let mediaStream = null;
let mediaRecorder = null;
let audioChunks = [];

// ---------------- API HELPERS ---------------- //

async function submitGuessToAPI(guess) {
  try {
    const response = await fetch("/api/submit-guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guess }),
    });

    const data = await response.json();
    console.log("submit-guess response:", data);

    // Map backend → showResult expected format
    showResult({
      recognized_text: data.guess,
      message: data.message,
      attempts_left: data.attempts_left,
      match: data.result === "correct", //Not sure yet
      can_change_passphrase: data.can_change_passphrase,
    });
  } catch (err) {
    console.error("Error submitting guess:", err);
    resultMessage.textContent = "Error: could not submit guess.";
    resultMessage.className = "result-message error";
  }
}

async function uploadAudioToServer(blob) {
  try {
    const formData = new FormData();
    formData.append("audio_file", blob, "recording.webm");

    const response = await fetch("/api/upload-audio", {
      method: "POST",
      body: formData,
    });

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      const text = await response.text();
      console.error("Non-JSON response from server:", text);
      throw new Error("Server returned non-JSON response (likely HTML error page).");
    }

    const data = await response.json();
    console.log("upload-audio response:", data);

    if (!response.ok) {
      resultMessage.textContent =
        data.error || "Error: could not process audio.";
      resultMessage.className = "result-message error";
      return;
    }

    const recognizedText = data.recognized_text || "";
    if (!recognizedText) {
      resultMessage.textContent = "No speech recognized.";
      resultMessage.className = "result-message error";
      return;
    }

    // Feed the recognized text into existing guess logic
    submitGuessToAPI(recognizedText);
  } catch (err) {
    console.error("Error uploading audio:", err);
    resultMessage.textContent = "Error: could not upload audio.";
    resultMessage.className = "result-message error";
  }
}


async function loadGameState() {
  try {
    const response = await fetch("/api/game-state");
    const data = await response.json();

    console.log("game-state:", data);

    // Update attempts on page load
    if (attemptsEl && typeof data.attempts_left === "number") {
      attemptsEl.textContent = data.attempts_left;
    }
  } catch (err) {
    console.error("Error loading game state:", err);
  }
}


async function submitNewPassphrase() {
  if (!newPassphraseInput) return;

  const passphrase = newPassphraseInput.value.trim();
  if (!passphrase) {
    resultMessage.textContent = "Passphrase cannot be empty.";
    resultMessage.className = "result-message error";
    return;
  }

  try {
    const response = await fetch("/api/set-passphrase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase }),
    });

    const data = await response.json();
    console.log("set-passphrase response:", data);

    if (response.ok) {
      resultMessage.textContent = data.message || "New passphrase set.";
      resultMessage.className = "result-message success";
      if (attemptsEl && typeof data.attempts_left === "number") {
        attemptsEl.textContent = data.attempts_left;
      }
      newPassphraseInput.value = "";
      hideNewPassphraseModal();
    } else {
      resultMessage.textContent =
        data.error || "Error: could not set new passphrase.";
      resultMessage.className = "result-message error";
    }
  } catch (err) {
    console.error("Error setting new passphrase:", err);
    resultMessage.textContent = "Error: could not set new passphrase.";
    resultMessage.className = "result-message error";
  }
}

// ---------------- UI HELPERS ---------------- //

function showNewPassphraseModal() {
  if (!newPassphraseModal) return;
  newPassphraseModal.classList.remove("hidden");
  if (newPassphraseInput) {
    newPassphraseInput.value = "";
    newPassphraseInput.focus();
  }
}

function hideNewPassphraseModal() {
  if (!newPassphraseModal) return;
  newPassphraseModal.classList.add("hidden");
}


// ---------------- UI BEHAVIOR ---------------- //
async function onRecordStart() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    resultMessage.textContent =
      "This browser does not support microphone recording.";
    resultMessage.className = "result-message error";
    return;
  }

  try {
    // Request microphone access if not already granted
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      // Stop the audio tracks so we do not hold the mic indefinitely
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
      }

      if (audioChunks.length === 0) {
        resultMessage.textContent = "No audio captured.";
        resultMessage.className = "result-message error";
        return;
      }

      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      audioChunks = [];

      statusText.textContent = "Uploading and transcribing...";
      await uploadAudioToServer(audioBlob);
      // `uploadAudioToServer` will call submitGuessToAPI when done
    };

    mediaRecorder.start();
    isRecording = true;
    statusText.textContent = "Listening...";
    recordBtn.textContent = "🛑 Stop Recording";
  } catch (err) {
    console.error("Error accessing microphone:", err);
    resultMessage.textContent =
      "Could not access microphone. Check permissions.";
    resultMessage.className = "result-message error";
    isRecording = false;
  }
}

function onRecordStop() {
  if (!isRecording || !mediaRecorder) {
    return;
  }

  isRecording = false;
  statusText.textContent = "Processing recording...";
  recordBtn.textContent = "🎙 Start Recording";

  mediaRecorder.stop();
}


function showResult({
  match,
  message,
  attempts_left,
  recognized_text,
  can_change_passphrase,
}) {
  guessText.textContent = recognized_text ?? "—";
  resultMessage.textContent = message ?? "";
  resultMessage.className = match
    ? "result-message success"
    : "result-message error";

  if (attemptsEl && typeof attempts_left === "number") {
    attemptsEl.textContent = attempts_left;
  }

  if (can_change_passphrase) {
    showNewPassphraseModal();
  }

  statusText.textContent = "Waiting to start...";
}

// Attach UI behavior
// Temporary: toggle only
recordBtn?.addEventListener("click", () => {
  if (!isRecording) onRecordStart();
  else onRecordStop();
});

// Modal buttons
setPassphraseBtn?.addEventListener("click", submitNewPassphrase);
closePassphraseBtn?.addEventListener("click", hideNewPassphraseModal);

// Allow Enter to submit new passphrase
newPassphraseInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    submitNewPassphrase();
  }
});

// Load state on page load
loadGameState();