(() => {
  const form = document.getElementById("topic-form");
  const input = document.getElementById("topic-input");
  const output = document.getElementById("output");
  const status = document.getElementById("status");
  const generateBtn = document.getElementById("generate-btn");
  const stopBtn = document.getElementById("stop-btn");
  const providerMeta = document.getElementById("provider-meta");
  const cursorMeta = document.getElementById("cursor-meta");

  let source = null;

  function setBusy(busy) {
    generateBtn.disabled = busy;
    stopBtn.hidden = !busy;
    cursorMeta.hidden = !busy;
  }

  function closeSource() {
    if (source) {
      source.close();
      source = null;
    }
  }

  async function loadConfig() {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      if (data.ok) {
        providerMeta.textContent = `${data.provider} · ${data.model}`;
      } else {
        providerMeta.textContent = "config error";
        status.textContent = data.error || "Missing API key configuration.";
      }
    } catch {
      providerMeta.textContent = "offline";
    }
  }

  stopBtn.addEventListener("click", () => {
    closeSource();
    setBusy(false);
    status.textContent = "Stopped.";
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const topic = input.value.trim();
    if (!topic) return;

    closeSource();
    output.textContent = "";
    status.textContent = "Opening channel…";
    setBusy(true);

    source = new EventSource(`/stream?topic=${encodeURIComponent(topic)}`);

    source.addEventListener("error", (ev) => {
      // Named SSE `event: error` payloads from the server (not transport failures).
      if (ev instanceof MessageEvent && ev.data) {
        status.textContent = `Error: ${ev.data}`;
        closeSource();
        setBusy(false);
      }
    });

    source.onmessage = (ev) => {
      if (ev.data === "[DONE]") {
        closeSource();
        setBusy(false);
        status.textContent = "Complete.";
        return;
      }
      output.textContent += ev.data;
      output.scrollTop = output.scrollHeight;
      status.textContent = "Receiving…";
    };

    source.onerror = () => {
      if (!source) return;
      status.textContent = "Connection lost.";
      closeSource();
      setBusy(false);
    };
  });

  loadConfig();
  input.focus();
})();
