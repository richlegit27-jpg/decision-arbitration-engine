
(function () {
    "use strict";

    if (window.__NOVA_COLLAPSED_SOURCE_DRAWER_20260622__) return;
    window.__NOVA_COLLAPSED_SOURCE_DRAWER_20260622__ = true;

    function sourceGroups() {
        try {
            return Array.from(document.querySelectorAll(
                ".nova-source-cards, [data-nova-forced-source-cards='true']"
            )).filter(function (node) {
                return (
                    node &&
                    node.parentNode &&
                    !node.closest(".nova-source-drawer") &&
                    !node.hasAttribute("data-nova-source-drawer-wrapped")
                );
            });
        } catch (_) {
            return [];
        }
    }

    function countCards(group) {
        try {
            var cards = group.querySelectorAll(".nova-source-card, [data-source-card='true']");
            if (cards && cards.length) return cards.length;
        } catch (_) {}

        try {
            return Math.max(1, group.children.length || 1);
        } catch (_) {
            return 1;
        }
    }

    function wrapGroup(group) {
        if (!group || !group.parentNode) return;

        if (group.closest(".nova-source-drawer")) return;

        var count = countCards(group);

        group.setAttribute("data-nova-source-drawer-wrapped", "true");

        var drawer = document.createElement("details");
        drawer.className = "nova-source-drawer";
        drawer.setAttribute("data-nova-source-drawer", "true");

        var summary = document.createElement("summary");
        summary.textContent = count === 1 ? "Source" : ("Sources " + count);

        drawer.appendChild(summary);

        group.parentNode.insertBefore(drawer, group);
        drawer.appendChild(group);
    }

    function collapseSourceCards() {
        sourceGroups().forEach(wrapGroup);
    }

    collapseSourceCards();

    setTimeout(collapseSourceCards, 250);
    setTimeout(collapseSourceCards, 900);
    setTimeout(collapseSourceCards, 1800);

    document.addEventListener("nova:message:rendered", collapseSourceCards);

    var observer = new MutationObserver(function () {
        clearTimeout(window.__novaCollapsedSourceDrawerTimer);
        window.__novaCollapsedSourceDrawerTimer = setTimeout(collapseSourceCards, 80);
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    window.NovaCollapseSourceCards = collapseSourceCards;

    console.log("[Nova] collapsed source drawer ready");
})();
