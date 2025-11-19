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

let mediaRecorder = null;
let recordedChunks = [];
let stopTimer = null;

// ---------------- API HELPERS ---------------- //

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

// ---------------- RECORDING + AUDIO UPLOAD ---------------- //

async function sendAudioToServer(blob) {
  statusText.textContent = "Uploading…";

  const formData = new FormData();
  formData.append("audio", blob, "recording.webm");

  try {
    const response = await fetch("/api/submit-guess", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    console.log("upload-audio response:", data);

    showResult({
      recognized_text: data.guess,
      message: data.message,
      attempts_left: data.attempts_left,
      match: data.result === "correct",
      can_change_passphrase: data.can_change_passphrase,
    });

  } catch (err) {
    console.error("Error submitting guess:", err);
    statusText.textContent = "Server error.";
    resultMessage.textContent = "Error: could not submit guess.";
    resultMessage.className = "result-message error";
  }
}

function stopRecordingAndUpload() {
    if (stopTimer) clearTimeout(stopTimer);

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
}


// ---------------- UI BEHAVIOR ---------------- //

function onRecordStart() {
  isRecording = true;
  statusText.textContent = "Listening...";
  recordBtn.textContent = "🛑 Stop Recording";
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            recordedChunks = [];
            mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) recordedChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(recordedChunks, { type: "audio/webm" });
                sendAudioToServer(blob);
            };

            mediaRecorder.start();
            console.log("Recording started");

            stopTimer = setTimeout(() => {
                stopRecordingAndUpload();
            }, 4000);
        })
        .catch(err => {
            console.error("Microphone error:", err);
            statusText.textContent = "Microphone unavailable.";
            recordBtn.textContent = "🎙 Start Recording";
            isRecording = false;
        });
}

function onRecordStop() {
    isRecording = false;
    statusText.textContent = "Waiting to start...";
    recordBtn.textContent = "🎙 Start Recording";
    stopRecordingAndUpload();
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
