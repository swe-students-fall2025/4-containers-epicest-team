// Minimal UI hooks — no mic/ML yet.

const recordBtn = document.getElementById("record-btn");
const statusText = document.getElementById("status-text");
const guessText = document.getElementById("guess-text");
const resultMessage = document.getElementById("result-message");

let isRecording = false;

function onRecordStart() {
  isRecording = true;
  statusText.textContent = "Listening...";
  recordBtn.textContent = "🛑 Stop Recording";
}

function onRecordStop() {
  isRecording = false;
  statusText.textContent = "Waiting to start...";
  recordBtn.textContent = "🎙 Start Recording";
}

function showResult({ match, message, attempts_left, recognized_text }) {
  guessText.textContent = recognized_text ?? "—";
  resultMessage.textContent = message ?? "";
  resultMessage.className = match ? "result-message success" : "result-message error";
  const attempts = document.getElementById("attempts-left");
  if (attempts && typeof attempts_left === "number") attempts.textContent = attempts_left;
}

// Temporary: toggle only
recordBtn?.addEventListener("click", () => {
  if (!isRecording) onRecordStart();
  else onRecordStop();
});