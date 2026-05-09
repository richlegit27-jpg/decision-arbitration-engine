(function () {
  window.Nova = window.Nova || {};

  /**
   * Generate a new AI dog image and display it in chat
   * @param {string} prompt - Image generation prompt
   */
  window.Nova.generateDogImage = async function(prompt) {
    if (!window.Nova.sessionReady) {
      console.warn("Session not ready yet");
      return;
    }

    const sessionId = await window.Nova.sessionReady;

    // Send the prompt as a "message" to trigger image generation
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: prompt, session_id: sessionId })
    });
    const data = await response.json();

    // Display AI text response
    if (data.messages_preview)
      data.messages_preview.forEach(m => window.Nova.renderMessage(m.content, "assistant"));

    // Display generated image
    if (data.attachments)
      data.attachments.forEach(att => window.Nova.addAttachment(att.url, att.type));
  };
})();