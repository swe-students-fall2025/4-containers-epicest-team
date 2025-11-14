// Minimal UI hooks — no mic/ML yet.

const recordBtn = document.getElementById("record-btn");
const statusText = document.getElementById("status-text");
const guessText = document.getElementById("guess-text");
const resultMessage = document.getElementById("result-message");

let isRecording = false;

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
      match: data.result === "correct", // will matter later
    });
  } catch (err) {
    console.error("Error submitting guess:", err);
    resultMessage.textContent = "Error: could not submit guess.";
  }
}

async function loadGameState() {
  try {
    const response = await fetch("/api/game-state");
    const data = await response.json();

    console.log("game-state:", data);

    // Update attempts on page load
    const attempts = document.getElementById("attempts-left");
    if (attempts && typeof data.attempts_left === "number") {
      attempts.textContent = data.attempts_left;
    }
  } catch (err) {
    console.error("Error loading game state:", err);
  }
}

// ---------------- UI BEHAVIOR ---------------- //

function onRecordStart() {
  isRecording = true;
  statusText.textContent = "Listening...";
  recordBtn.textContent = "🛑 Stop Recording";
}

function onRecordStop() {
  isRecording = false;
  statusText.textContent = "Waiting to start...";
  recordBtn.textContent = "🎙 Start Recording";

// Fake guess for now — ML team will replace this
  const fakeGuess = "placeholder guess";
  submitGuessToAPI(fakeGuess);
}


function showResult({ match, message, attempts_left, recognized_text }) {
  guessText.textContent = recognized_text ?? "—";
  resultMessage.textContent = message ?? "";
  resultMessage.className = match ? "result-message success" : "result-message error";
  
  
  const attempts = document.getElementById("attempts-left");
  if (attempts && typeof attempts_left === "number") attempts.textContent = attempts_left;

// Update status text after receiving API response
  statusText.textContent = "Waiting to start...";
}

// Attach UI behavior
// Temporary: toggle only
recordBtn?.addEventListener("click", () => {
  if (!isRecording) onRecordStart();
  else onRecordStop();
});


// Load state on page load
loadGameState();