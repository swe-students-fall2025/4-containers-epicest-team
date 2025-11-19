document.addEventListener("DOMContentLoaded", () => {
  const METADATA_URL = "/api/send-metadata";
  const statusEl = document.getElementById("metadata-status");

  const metadata = {
    page: "dashboard",
    loaded_at: new Date().toISOString(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
  };

  async function sendMetadata() {
    try {
      const response = await fetch(METADATA_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(metadata),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        console.error("Metadata error:", err);
        if (statusEl) statusEl.textContent = "⚠️ Could not send metadata.";
        return;
      }

      if (statusEl) statusEl.textContent = "✓ Metadata sent.";
      console.log("Metadata sent successfully");
    } catch (e) {
      console.error("Metadata request failed:", e);
      if (statusEl) statusEl.textContent =
        "⚠️ Network error sending metadata.";
    }
  }

  sendMetadata();

  // -------- FETCH AGGREGATED METADATA -------- //

async function loadSummary() {
  try {
    const response = await fetch("/api/metadata-summary");
    if (!response.ok) {
      console.error("Failed to load summary");
      return;
    }

    const data = await response.json();
    console.log("summary data:", data);

    document.getElementById("stat-total").textContent = data.total_entries;
    document.getElementById("stat-user").textContent = data.user_entries;
    document.getElementById("stat-latest").textContent = data.latest_timestamp || "None";

    // Populate page_counts
    const list = document.getElementById("stat-page-counts");
    list.innerHTML = "";
    data.page_counts.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item._id}: ${item.count}`;
      list.appendChild(li);
    });

  } catch (e) {
    console.error("Error fetching summary:", e);
  }
}

loadSummary();

});


