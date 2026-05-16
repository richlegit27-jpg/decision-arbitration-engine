(async function novaSmokeTestHarness() {
  console.log("🔥 Starting Nova Phase 4 automated smoke test harness...");

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const messages = document.getElementById("messages");
  const emptyState = document.getElementById("novaEmptyState");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("fileInput");
  const sessionId = "default-session"; // Ensure session exists

  const sleep = (ms) => new Promise(res => setTimeout(res, ms));

  // Wait for AI response to appear
  async function waitForAI(lastCount, timeout = 5000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const count = messages.querySelectorAll(".assistant-message").length;
      if (count > lastCount) return true;
      await sleep(100);
    }
    console.warn("⚠ AI response did not appear in time");
    return false;
  }

  // Send chat message and verify
  async function sendMessage(content) {
    const lastCount = messages.querySelectorAll(".assistant-message").length;
    chatInput.value = content;
    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
    sendBtn.click();
    console.log(`Sent: "${content}"`);
    const aiAppeared = await waitForAI(lastCount);
    if (!aiAppeared) console.error(`❌ AI response missing for message: "${content}"`);
    return aiAppeared;
  }

  // Upload file and verify rendering
  async function uploadFile(name, type) {
    const blob = new Blob(["Test content"], { type });
    const file = new File([blob], name, { type });
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    uploadBtn.click();
    console.log(`Uploading: ${name}`);
    await sleep(1500);
    const attachCount = messages.querySelectorAll(".attachment-message").length;
    if (attachCount === 0) console.error(`❌ Attachment failed: ${name}`);
    else console.log(`✅ Attachment succeeded: ${name}`);
  }

  // ------------------ Test sequence ------------------
  try {
    console.log("➡ Testing empty state...");
    if (emptyState && emptyState.style.display !== "none") console.log("✅ Empty state visible");

    // Chat tests
    const chatTests = [
      "Hello Nova!",
      "Testing long message for wrapping and scrolling behavior...",
      "Special characters: !@#$%^&*()_+{}[]<>?/😊",
      "Rapid 1",
      "Rapid 2",
      "Rapid 3"
    ];

    for (const msg of chatTests) {
      await sendMessage(msg);
    }

    // Attachment tests
    const attachments = [
      {name:"test-image.png", type:"image/png"},
      {name:"test-video.mp4", type:"video/mp4"},
      {name:"test-file.pdf", type:"application/pdf"}
    ];

    for (const file of attachments) {
      await uploadFile(file.name, file.type);
    }

    // Scroll check
    if (messages.scrollTop + messages.clientHeight >= messages.scrollHeight - 10) {
      console.log("✅ Scroll auto-down working");
    }

    console.log("🔥 Automated smoke test harness completed successfully!");
  } catch (err) {
    console.error("❌ Smoke test harness failed:", err);
  }
})();