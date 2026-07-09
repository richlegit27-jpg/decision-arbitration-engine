(async function novaSmokeTestHarness() {
  console.log("ðŸ”¥ Starting Nova Phase 4 automated smoke test harness (AI stub active)...");

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const messages = document.getElementById("messages");
  const emptyState = document.getElementById("novaEmptyState");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("fileInput");
  const sessionId = "default-session"; // Ensure this session exists

  const sleep = (ms) => new Promise(res => setTimeout(res, ms));

  // Wait for AI response to appear in DOM
  async function waitForAI(lastCount, timeout = 5000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const count = messages.querySelectorAll(".assistant-message").length;
      if (count > lastCount) return true;
      await sleep(100);
    }
    console.warn("âš  AI response did not appear in time");
    return false;
  }

  // Send chat message and verify AI response
  async function sendMessage(content) {
    const lastCount = messages.querySelectorAll(".assistant-message").length;
    chatInput.value = content;
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    sendBtn.click();
    console.log(`Sent: "${content}"`);
    const aiAppeared = await waitForAI(lastCount);
    if (!aiAppeared) console.error(`âŒ AI response missing for message: "${content}"`);
    else console.log(`âœ… AI response received for: "${content}"`);
    return aiAppeared;
  }

  // Upload file helper (manual click required in browser)
  async function uploadFile(name, type) {
    console.log(`âš  Manual attachment test: Click ðŸ“Ž and select ${name} in browser to continue`);
    await sleep(2000); // pause for manual upload
  }

  try {
    // ------------------ Empty state check ------------------
    if (emptyState && emptyState.style.display !== "none") console.log("âœ… Empty state visible");

    // ------------------ Chat messages ------------------
    const chatTests = [
      "Hello Nova!",
      "Testing long message for wrapping and scrolling behavior...",
      "Special characters: !@#$%^&*()_+{}[]<>?/ðŸ˜Š",
      "Rapid 1",
      "Rapid 2",
      "Rapid 3"
    ];

    for (const msg of chatTests) {
      await sendMessage(msg);
    }

    // ------------------ Attachments (manual only) ------------------
    const attachments = [
      {name:"test-image.png", type:"image/png"},
      {name:"test-video.mp4", type:"video/mp4"},
      {name:"test-file.pdf", type:"application/pdf"}
    ];

    for (const file of attachments) {
      await uploadFile(file.name, file.type);
    }

    // ------------------ Scroll check ------------------
    if (messages.scrollTop + messages.clientHeight >= messages.scrollHeight - 10) {
      console.log("âœ… Scroll auto-down working");
    }

    console.log("ðŸ”¥ Automated Phase 4 smoke test harness completed successfully!");
  } catch (err) {
    console.error("âŒ Smoke test harness failed:", err);
  }
})();

