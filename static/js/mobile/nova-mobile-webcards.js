(function () {
"use strict";

let webCardCount = 0;

const MAX_VISIBLE_WEB_CARDS = 3;

function appendWebCardSkeleton() {
    if (!chatContainer) return null;

    const wrapper = document.createElement("div");

    wrapper.className =
        "mobile-chat-message assistant mobile-web-card";

    const previous =
        chatContainer.lastElementChild;

    if (
        previous &&
        previous.classList.contains("mobile-web-card")
    ) {
        wrapper.classList.add(
            "mobile-web-card-stacked"
        );
    }

    const card = document.createElement("div");

    card.className =
        "mobile-web-card-inner mobile-web-card-skeleton";

    card.innerHTML = `
        <div class="mobile-skeleton-line short"></div>
        <div class="mobile-skeleton-line tiny"></div>
        <div class="mobile-skeleton-line"></div>
        <div class="mobile-skeleton-line"></div>
        <div class="mobile-skeleton-line medium"></div>
    `;

    wrapper.appendChild(card);

    chatContainer.appendChild(wrapper);

    scrollBottom();

    return wrapper;
}

function appendWebSectionHeader() {
    if (!chatContainer) return;

    const previous =
        chatContainer.lastElementChild;

    if (
        previous &&
        (
            previous.classList.contains("mobile-web-card") ||
            previous.classList.contains("mobile-web-section-header")
        )
    ) {
        return;
    }

    document
        .querySelectorAll(".mobile-web-show-more")
        .forEach(function (button) {
            button.remove();
        });

    const header = document.createElement("div");

    header.className =
        "mobile-web-section-header";

    header.textContent = "Sources";

    webCardCount = 0;

    chatContainer.appendChild(header);
}

function appendWebCard(
    title,
    url,
    description
) {
    if (!chatContainer) return;

    appendWebSectionHeader();

    const hostname =
        getHostnameFromUrl(url);

    const badgeType =
        getWebCardBadge(hostname);

    let qualityScore = "Standard";

    if (
        hostname.includes("reuters") ||
        hostname.includes("apnews") ||
        hostname.includes("nytimes") ||
        hostname.includes("bbc") ||
        hostname.includes("cbc")
    ) {
        qualityScore = "Trusted";
    }

    if (
        hostname.includes("reddit") ||
        hostname.includes("x.com") ||
        hostname.includes("twitter")
    ) {
        qualityScore = "Community";
    }

    webCardCount += 1;

    const wrapper = document.createElement("div");

    wrapper.className =
        "mobile-chat-message assistant mobile-web-card";

    if (
        webCardCount >
        MAX_VISIBLE_WEB_CARDS
    ) {
        wrapper.classList.add(
            "mobile-web-card-hidden"
        );
    }

    const card = document.createElement("div");

    card.className =
        "mobile-web-card-inner";

    card.tabIndex = 0;

    card.setAttribute("role", "button");

    const favicon =
        document.createElement("img");

    favicon.className =
        "mobile-web-card-favicon";

    favicon.src =
        "https://www.google.com/s2/favicons?domain=" +
        encodeURIComponent(hostname) +
        "&sz=64";

    favicon.alt = hostname;

    favicon.onerror = function () {
        favicon.style.display = "none";
    };

    const badge =
        document.createElement("div");

    badge.className =
        "mobile-web-card-badge";

    badge.dataset.badgeType =
        badgeType.toLowerCase();

    if (
        hostname.includes("bbc") ||
        hostname.includes("cnn") ||
        hostname.includes("nytimes") ||
        hostname.includes("cbc") ||
        hostname.includes("reuters")
    ) {
        card.classList.add(
            "mobile-web-card-trusted"
        );
    }

    badge.textContent =
        webCardCount +
        ". " +
        getWebCardBadgeIcon(badgeType) +
        " " +
        badgeType;

    const externalIcon =
        document.createElement("div");

    externalIcon.className =
        "mobile-web-card-external";

    externalIcon.textContent = "↗";

    const heading =
        document.createElement("div");

    heading.className =
        "mobile-web-card-title";

    heading.textContent =
        title || "Web Result";

    const topRow =
        document.createElement("div");

    topRow.className =
        "mobile-web-card-top-row";

    const titleWrap =
        document.createElement("div");

    titleWrap.className =
        "mobile-web-card-title-wrap";

    titleWrap.appendChild(favicon);
    titleWrap.appendChild(heading);

    topRow.appendChild(titleWrap);
    topRow.appendChild(externalIcon);

    const domain =
        document.createElement("div");

    domain.className =
        "mobile-web-card-domain";

    domain.textContent = hostname;

    const link =
        document.createElement("a");

    link.className =
        "mobile-web-card-url";

    link.href = url || "#";

    link.target = "_blank";

    link.rel =
        "noopener noreferrer";

    link.textContent = url || "";

    link.addEventListener(
        "click",
        function (event) {
            event.stopPropagation();
        }
    );

    const body =
        document.createElement("div");

    body.className =
        "mobile-web-card-description collapsed";

    body.textContent =
        description && description.trim()
            ? description
            : "No summary available yet.";

    const actions =
        document.createElement("div");

    actions.className =
        "mobile-image-actions";

    const openBtn =
        document.createElement("button");

    openBtn.type = "button";

    openBtn.className =
        "mobile-inline-action";

    openBtn.textContent =
        getWebCardActionLabel(
            badgeType
        );

    openBtn.addEventListener(
        "click",
        function (event) {
            event.stopPropagation();

            if (!url) return;

            vibrate(8);

            showToast(
                "Opening source..."
            );

            openBtn.textContent =
                "Opening";

            flashWebCardDomain(
                domain,
                "Opening..."
            );

            activateWebCard(card);

            window.open(
                url,
                "_blank",
                "noopener,noreferrer"
            );
        }
    );

    const copyBtn =
        document.createElement("button");

    copyBtn.type = "button";

    copyBtn.className =
        "mobile-inline-action";

    copyBtn.textContent =
        "Copy link";

    copyBtn.addEventListener(
        "click",
        function (event) {
            event.stopPropagation();

            if (
                !hasCopyableSourceUrl(url)
            ) {
                return;
            }

            copyText(url);

            notifySourceCopied();

            activateWebCard(card);

            resetCopyButton(copyBtn);

            card.classList.add(
                "mobile-web-card-active"
            );
        }
    );

    actions.appendChild(openBtn);
    actions.appendChild(copyBtn);

    card.addEventListener(
        "click",
        function (event) {
            if (
                event.target.closest(
                    "button"
                ) ||
                event.target.closest("a")
            ) {
                return;
            }

            if (!url) return;

            vibrate(8);

            showToast(
                "Opening source..."
            );

            flashWebCardDomain(
                domain,
                "Opening..."
            );

            activateWebCard(card);

            window.open(
                url,
                "_blank",
                "noopener,noreferrer"
            );
        }
    );

    card.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key !== "Enter" &&
                event.key !== " "
            ) {
                return;
            }

            event.preventDefault();

            if (!url) return;

            notifyOpeningSource();

            activateWebCard(card);

            flashWebCardDomain(
                domain,
                "Opening..."
            );

            window.open(
                url,
                "_blank",
                "noopener,noreferrer"
            );
        }
    );

    card.addEventListener(
        "touchstart",
        function () {
            card.style.transform =
                "scale(0.992) translateY(1px)";
        }
    );

    card.addEventListener(
        "touchend",
        function () {
            card.style.transform = "";
        }
    );

    card.addEventListener(
        "touchcancel",
        function () {
            card.style.transform = "";
        }
    );

    card.appendChild(topRow);
    card.appendChild(badge);
    card.appendChild(domain);

    const quality =
        document.createElement("div");

    quality.className =
        "mobile-web-card-quality";

    quality.textContent =
        "Source: " + qualityScore;

    card.appendChild(quality);

    if (url) {
        card.appendChild(link);
    }

    if (
        description &&
        description.length > 180
    ) {
        body.classList.add("collapsed");
    }

    card.appendChild(body);
    card.appendChild(actions);

    if (
        description &&
        description.length > 180
    ) {
        const expandBtn =
            document.createElement(
                "button"
            );

        expandBtn.type = "button";

        expandBtn.className =
            "mobile-inline-action mobile-web-expand";

        expandBtn.textContent =
            "Expand";

        expandBtn.addEventListener(
            "click",
            function (event) {
                event.stopPropagation();

                body.classList.toggle(
                    "collapsed"
                );

                expandBtn.textContent =
                    body.classList.contains(
                        "collapsed"
                    )
                        ? "Expand"
                        : "Collapse";

                vibrate(8);
            }
        );

        actions.appendChild(
            expandBtn
        );
    }

    wrapper.appendChild(card);

    wrapper.addEventListener(
        "contextmenu",
        function (event) {
            event.preventDefault();

            if (!hasSourceUrl(url)) {
                return;
            }

            navigator.clipboard.writeText(
                url
            );

            showToast(
                "Source link copied."
            );

            flashWebCardDomain(
                domain,
                "Copied link"
            );

            vibrate(18);
        }
    );

    chatContainer.appendChild(wrapper);

    if (
        webCardCount >
        MAX_VISIBLE_WEB_CARDS
    ) {
        appendShowMoreWebCardsButton();
    }

    scrollBottom();
}

function appendShowMoreWebCardsButton() {
    if (!chatContainer) return;

    const existing =
        chatContainer.querySelector(
            ".mobile-web-show-more"
        );

    if (existing) {
        existing.remove();
    }

    const hiddenCount =
        chatContainer.querySelectorAll(
            ".mobile-web-card-hidden"
        ).length;

    if (hiddenCount <= 0) return;

    const button =
        document.createElement("button");

    button.className =
        "mobile-web-show-more mobile-inline-action";

    button.type = "button";

    button.textContent =
        "Show " +
        hiddenCount +
        " more source" +
        (hiddenCount === 1
            ? ""
            : "s");

    button.addEventListener(
        "click",
        function () {
            const hiddenCards =
                chatContainer.querySelectorAll(
                    ".mobile-web-card-hidden"
                );

            if (
                hiddenCards.length
            ) {
                hiddenCards.forEach(
                    function (card) {
                        card.classList.remove(
                            "mobile-web-card-hidden"
                        );

                        card.classList.add(
                            "mobile-web-card-reveal"
                        );

                        setTimeout(
                            function () {
                                card.classList.remove(
                                    "mobile-web-card-reveal"
                                );
                            },
                            260
                        );
                    }
                );

                button.textContent =
                    "Collapse";

                vibrate(12);

                return;
            }

            chatContainer
                .querySelectorAll(
                    ".mobile-web-card"
                )
                .forEach(
                    function (
                        card,
                        index
                    ) {
                        if (
                            index >=
                            MAX_VISIBLE_WEB_CARDS
                        ) {
                            card.classList.add(
                                "mobile-web-card-hidden"
                            );
                        }
                    }
                );

            const nextHiddenCount =
                chatContainer.querySelectorAll(
                    ".mobile-web-card-hidden"
                ).length;

            button.textContent =
                nextHiddenCount > 0
                    ? "Show " +
                      nextHiddenCount +
                      " more source" +
                      (nextHiddenCount === 1
                          ? ""
                          : "s")
                    : "Show more sources";

            chatContainer.appendChild(
                button
            );

            vibrate(12);
        }
    );

    chatContainer.appendChild(button);
}

function getWebCardBadgeIcon(type) {
    switch (
        String(type || "").toUpperCase()
    ) {
        case "VIDEO":
            return "▶";

        case "NEWS":
            return "📰";

        case "GITHUB":
            return "⌘";

        case "DOCS":
            return "📘";

        case "SEARCH":
            return "⌕";

        default:
            return "●";
    }
}

function getWebCardActionLabel(type) {
    switch (
        String(type || "").toUpperCase()
    ) {
        case "VIDEO":
            return "Watch";

        case "GITHUB":
            return "Repo";

        case "NEWS":
            return "Read";

        case "DOCS":
            return "Learn";

        case "SEARCH":
            return "Search";

        default:
            return "Open";
    }
}

function getWebCardBadge(hostname) {
    const host =
        String(hostname || "")
            .toLowerCase();

    if (
        host.includes(
            "youtube.com"
        ) ||
        host.includes("youtu.be")
    ) {
        return "VIDEO";
    }

    if (
        host.includes(
            "github.com"
        )
    ) {
        return "GITHUB";
    }

    if (
        host.includes("news") ||
        host.includes("cnn.com") ||
        host.includes("bbc.com") ||
        host.includes(
            "nytimes.com"
        ) ||
        host.includes(
            "reuters.com"
        )
    ) {
        return "NEWS";
    }

    if (
        host.includes("docs.") ||
        host.includes(
            "developer."
        ) ||
        host.includes("learn.") ||
        host.includes(
            "mozilla.org"
        ) ||
        host.includes(
            "w3schools.com"
        )
    ) {
        return "DOCS";
    }

    if (
        host.includes(
            "google.com"
        ) ||
        host.includes("bing.com") ||
        host.includes(
            "duckduckgo.com"
        )
    ) {
        return "SEARCH";
    }

    return "SOURCE";
}

function flashWebCardDomain(
    domainEl,
    text
) {
    if (!domainEl) return;

    const oldText =
        domainEl.textContent;

    domainEl.textContent = text;

    domainEl.classList.add(
        "copied"
    );

    setTimeout(function () {
        domainEl.textContent =
            oldText;

        domainEl.classList.remove(
            "copied"
        );
    }, 900);
}

function activateWebCard(card) {
    if (!card) return;

    card.classList.add(
        "mobile-web-card-active"
    );

    setTimeout(function () {
        card.classList.remove(
            "mobile-web-card-active"
        );
    }, 320);
}

function notifyOpeningSource() {
    showToast("Opening source...");
    vibrate(8);
}

function hasSourceUrl(url) {
    if (url) return true;

    showToast(
        "No source link available."
    );

    vibrate(20);

    return false;
}

function notifySourceCopied() {
    showToast(
        "Source link copied."
    );

    vibrate(10);
}

function hasCopyableSourceUrl(url) {
    if (url) return true;

    showToast(
        "No source link to copy."
    );

    vibrate(20);

    return false;
}

function resetCopyButton(copyBtn) {
    if (!copyBtn) return;

    copyBtn.textContent = "Copied";

    setTimeout(function () {
        copyBtn.textContent =
            "Copy link";
    }, 900);
}

window.NovaMobileWebCards = {
    appendWebCardSkeleton,
    appendWebSectionHeader,
    appendWebCard,
    appendShowMoreWebCardsButton,
    getWebCardBadge,
    getWebCardBadgeIcon,
    getWebCardActionLabel,
    flashWebCardDomain,
    activateWebCard,
    notifyOpeningSource,
    hasSourceUrl,
    notifySourceCopied,
    hasCopyableSourceUrl,
    resetCopyButton
};

})();