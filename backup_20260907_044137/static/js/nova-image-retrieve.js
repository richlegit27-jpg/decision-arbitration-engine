(function () {
  // Ensure window.Nova exists
  window.Nova = window.Nova || {};

  /**
   * Add and display an attachment with download option
   * @param {string} url - Image URL
   * @param {string} type - 'image' or 'video'
   */
  window.Nova.addAttachment = function (url, type = "image") {
    const messagesEl = document.getElementById("messages");
    if (!messagesEl) return;

    const wrapper = document.createElement("div");
    wrapper.className = "nova-msg-attachment";

    let el;
    if (type === "image") {
      el = document.createElement("img");
      el.src = url;
      el.style.cursor = "pointer";
      // Click to download
      el.addEventListener("click", () => {
        const a = document.createElement("a");
        a.href = url;
        a.download = url.split("/").pop();
        a.click();
      });
    } else if (type === "video") {
      el = document.createElement("video");
      el.src = url;
      el.controls = true;
    } else {
      el = document.createElement("iframe");
      el.src = url;
    }

    wrapper.appendChild(el);
    messagesEl.appendChild(wrapper);

    // Scroll to bottom
    messagesEl.scrollTop = messagesEl.scrollHeight;
  };
})();

