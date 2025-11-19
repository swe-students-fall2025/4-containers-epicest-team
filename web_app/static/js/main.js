// Minimal UI hooks — no mic/ML yet.

const recordBtn = document.getElementById("record-btn");
const statusText = document.getElementById("status-text");
const guessText = document.getElementById("guess-text");
const resultMessage = document.getElementById("result-message");
const attemptsEl = document.getElementById("attempts-left");
const hintText = document.getElementById("hint-text");

//elements for "create new secret" UI 
const newSecretModal = document.getElementById("new-secret-modal");
const newSecretInput = document.getElementById("new-secret-input");
const newHintInput = document.getElementById("new-hint-input");
const createSecretBtn = document.getElementById("create-secret-btn");

let isRecording = false;

// recording-related globals
let mediaStream = null;
let mediaRecorder = null;
let audioChunks = [];

// lockout timer globals
let lockoutInterval = null;

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

    // Map backend
    const mapped_data = {
      recognized_text: data.guess,
      message: data.message,
      attempts_left: data.attempts_left,
      match: data.result === "correct",
      can_create_secret: data.can_create_secret,
      locked_until: data.locked_until,
    }

    // Send result to server to be stored as metadata
    await fetch("/api/send-metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(mapped_data),
    });

    //showResult expected format
    showResult(mapped_data);
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


// Function to format time remaining
function formatTimeRemaining(lockedUntil) {
  const now = new Date();
  const unlockTime = new Date(lockedUntil);
  const diff = unlockTime - now;

  if (diff <= 0) {
    return null; // Lockout has expired
  }

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  
  if (hours > 0) {
    return `${hours} hour${hours !== 1 ? 's' : ''} and ${minutes} minute${minutes !== 1 ? 's' : ''}`;
  } else {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  }
}

// Update lockout display with current time remaining
function updateLockoutDisplay(lockedUntil) {
  const timeRemaining = formatTimeRemaining(lockedUntil);
  
  if (!timeRemaining) {
    // Lockout expired, reload to get new attempts
    location.reload();
    return false;
  }
  
  statusText.textContent = `You're out of attempts. Try again in ${timeRemaining}.`;
  return true;
}

// Check and display lockout status
function checkLockoutStatus(data) {
  // Clear any existing lockout interval
  if (lockoutInterval) {
    clearInterval(lockoutInterval);
    lockoutInterval = null;
  }
  
  if (data.attempts_left === 0 && data.locked_until) {
    const timeRemaining = formatTimeRemaining(data.locked_until);
    
    if (timeRemaining) {
      // User is locked out
      recordBtn.disabled = true;
      recordBtn.textContent = "🔒 Locked";
      recordBtn.style.opacity = "0.5";
      recordBtn.style.cursor = "not-allowed";
      
      statusText.textContent = `You're out of attempts. Try again in ${timeRemaining}.`;
      statusText.style.color = "var(--danger)";
      
      // Update the countdown every minute
      lockoutInterval = setInterval(() => {
        const stillLocked = updateLockoutDisplay(data.locked_until);
        if (!stillLocked && lockoutInterval) {
          clearInterval(lockoutInterval);
          lockoutInterval = null;
        }
      }, 60000); // Update every minute
      
      // Set up a timer to refresh the page when lockout expires
      setTimeout(() => {
        location.reload();
      }, new Date(data.locked_until) - new Date());
    } else {
      // Lockout expired, reload to get new attempts
      location.reload();
    }
  } else {
    // Not locked out, ensure button is enabled
    recordBtn.disabled = false;
    recordBtn.textContent = "🎙 Start Recording";
    recordBtn.style.opacity = "1";
    recordBtn.style.cursor = "pointer";
    statusText.textContent = "Ready to record your guess.";
    statusText.style.color = "";
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

    // Update hint on page load
    if (hintText && data.hint) {
      hintText.textContent = data.hint;
    }

    // Check lockout status
    checkLockoutStatus(data);

    // Check if user can create a secret
    if (data.can_create_secret) {
      showNewSecretModal();
    }
  } catch (err) {
    console.error("Error loading game state:", err);
  }
}


async function submitNewSecret() {
  if (!newSecretInput || !newHintInput) return;

  const secretPhrase = newSecretInput.value.trim();
  const hint = newHintInput.value.trim();
  
  if (!secretPhrase) {
    resultMessage.textContent = "Secret phrase cannot be empty.";
    resultMessage.className = "result-message error";
    return;
  }

  if (!hint) {
    resultMessage.textContent = "Hint cannot be empty.";
    resultMessage.className = "result-message error";
    return;
  }

  try {
    const response = await fetch("/api/create-secret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret_phrase: secretPhrase, hint: hint }),
    });

    const data = await response.json();
    console.log("create-secret response:", data);

    if (response.ok) {
      resultMessage.textContent = data.message || "New secret created.";
      resultMessage.className = "result-message success";
      newSecretInput.value = "";
      newHintInput.value = "";
      hideNewSecretModal();
      
      // Reload the game state to get the new secret
      setTimeout(() => {
        location.reload();
      }, 1500);
    } else {
      resultMessage.textContent =
        data.error || "Error: could not create new secret.";
      resultMessage.className = "result-message error";
    }
  } catch (err) {
    console.error("Error creating new secret:", err);
    resultMessage.textContent = "Error: could not create new secret.";
    resultMessage.className = "result-message error";
  }
}

// ---------------- UI HELPERS ---------------- //

function showNewSecretModal() {
  if (!newSecretModal) return;
  newSecretModal.classList.remove("hidden");
  if (newSecretInput) {
    newSecretInput.value = "";
    newSecretInput.focus();
  }
  if (newHintInput) {
    newHintInput.value = "";
  }
}

function hideNewSecretModal() {
  if (!newSecretModal) return;
  newSecretModal.classList.add("hidden");
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
  can_create_secret,
  locked_until,
}) {
  guessText.textContent = recognized_text ?? "—";
  resultMessage.textContent = message ?? "";
  resultMessage.className = match
    ? "result-message success"
    : "result-message error";

  if (attemptsEl && typeof attempts_left === "number") {
    attemptsEl.textContent = attempts_left;
  }

  if (can_create_secret) {
    showNewSecretModal();
  }

  // Handle lockout
  // Clear any existing lockout interval
  if (lockoutInterval) {
    clearInterval(lockoutInterval);
    lockoutInterval = null;
  }
  
  if (attempts_left === 0 && locked_until) {
    const timeRemaining = formatTimeRemaining(locked_until);
    if (timeRemaining) {
      recordBtn.disabled = true;
      recordBtn.textContent = "🔒 Locked";
      recordBtn.style.opacity = "0.5";
      recordBtn.style.cursor = "not-allowed";
      
      statusText.textContent = `You're out of attempts. Try again in ${timeRemaining}.`;
      statusText.style.color = "var(--danger)";
      
      // Update the countdown every minute
      lockoutInterval = setInterval(() => {
        const stillLocked = updateLockoutDisplay(locked_until);
        if (!stillLocked && lockoutInterval) {
          clearInterval(lockoutInterval);
          lockoutInterval = null;
        }
      }, 60000); // Update every minute
      
      // Set up a timer to refresh the page when lockout expires
      setTimeout(() => {
        location.reload();
      }, new Date(locked_until) - new Date());
    }
  } else if (attempts_left > 0) {
    statusText.textContent = "Ready to record your guess.";
    statusText.style.color = "";
  }
}

// Attach UI behavior
// Temporary: toggle only
recordBtn?.addEventListener("click", () => {
  // Prevent interaction if button is disabled (locked out)
  if (recordBtn.disabled) {
    return;
  }
  
  if (!isRecording) onRecordStart();
  else onRecordStop();
});

// Modal button
createSecretBtn?.addEventListener("click", submitNewSecret);

// Allow Enter to submit new secret from phrase input
newSecretInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    // Move focus to hint input if phrase is filled
    if (newSecretInput.value.trim() && newHintInput) {
      newHintInput.focus();
    }
  }
});

// Allow Enter to submit new secret from hint input
newHintInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    submitNewSecret();
  }
});

// Load state on page load
loadGameState();