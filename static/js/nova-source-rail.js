// C:\Users\Owner\nova\static\js\nova-source-rail.js

(function () {
  function ensureRail() {
    let rail = document.getElementById("nova-source-rail");
    if (rail) return rail;

    rail = document.createElement("div");
    rail.id = "nova-source-rail";
    rail.innerHTML =
      '<div class="nova-rail__header">' +
        '<div class="nova-rail__title">Source preview</div>' +
        '<button class="nova-rail__close" data-rail-close>×</button>' +
      "</div>" +
      '<div class="nova-rail__body">' +
        '<iframe id="nova-source-frame" class="nova-rail__frame" src=""></iframe>' +
      "</div>";

    document.body.appendChild(rail);

    document.addEventListener("click", function (e) {
      const btn = e.target.closest("[data-rail-close]");
      if (!btn) return;
      rail.classList.remove("open");
    });

    return rail;
  }

  window.openRailWithSource = function (url) {
    const rail = ensureRail();
    const frame = document.getElementById("nova-source-frame");

    try {
      frame.src = url;
    } catch (e) {
      frame.src = "";
    }

    rail.classList.add("open");
  };
})();