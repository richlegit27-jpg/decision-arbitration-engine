(function () {
  const panel = document.getElementById("novaMemoryPanel");
  window.Nova = window.Nova || {};
  window.Nova.openMemory = function () { panel.classList.add("is-active"); };

  const searchInput = document.getElementById("memorySearch");
  const memoryList = document.getElementById("memoryList");
  if (searchInput && memoryList) {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.toLowerCase();
      Array.from(memoryList.children).forEach(li => {
        li.style.display = li.textContent.toLowerCase().includes(query) ? "" : "none";
      });
    });
  }
})();