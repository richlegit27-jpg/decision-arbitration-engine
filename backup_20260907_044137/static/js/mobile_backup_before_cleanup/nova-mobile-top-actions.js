(function () {
    "use strict";

    const TAG =
        "[NOVA_MOBILE_TOP_ACTIONS_OWNER_V1]";

    if (window.__NOVA_MOBILE_TOP_ACTIONS_OWNER_V1__) {
        return;
    }

    window.__NOVA_MOBILE_TOP_ACTIONS_OWNER_V1__ = true;


    const PARK_IDS = [
        "mobileMenuButton",
        "mobileMemoryButton",
        "nova-mobile-copy-chat",
        "nova-mobile-rail-copy",
        "nova-mobile-rail-regen",
        "nova-mobile-bottom-login",
        "nova-mobile-account-fallback-menu",
        "nova-mobile-real-menu-account"
    ];


    function setImportant(el, prop, value) {
        if (el) {
            el.style.setProperty(
                prop,
                value,
                "important"
            );
        }
    }


    function parkOldButton(id) {
        const el =
            document.getElementById(id);

        if (!el) {
            return;
        }

        if (
            el.closest(
                "#nova-mobile-primary-action-row"
            )
        ) {
            return;
        }

        el.classList.add(
            "nova-mobile-v10-parked"
        );

        el.setAttribute(
            "aria-hidden",
            "true"
        );

        el.setAttribute(
            "tabindex",
            "-1"
        );

        setImportant(el, "position", "fixed");
        setImportant(el, "top", "-12000px");
        setImportant(el, "left", "-12000px");
        setImportant(el, "width", "1px");
        setImportant(el, "height", "1px");
        setImportant(el, "opacity", "0");
        setImportant(el, "visibility", "hidden");
        setImportant(el, "pointer-events", "none");
        setImportant(el, "z-index", "-1");
    }


    function ensureRow() {

        let row =
            document.getElementById(
                "nova-mobile-primary-action-row"
            );

        if (!row) {
            row =
                document.createElement(
                    "div"
                );

            row.id =
                "nova-mobile-primary-action-row";

            document.body.appendChild(row);
        }


        row.innerHTML = `
            <button id="nova-mobile-row-new" type="button">
                New
            </button>

            <button id="nova-mobile-row-copy" type="button">
                Copy
            </button>

            <button id="nova-mobile-row-regen" type="button">
                Regen
            </button>
        `;


        return row;
    }


    function setSessionId(sid) {

        if (!sid) {
            return;
        }

        localStorage.setItem(
            "nova_mobile_active_session_id",
            sid
        );

        localStorage.setItem(
            "nova_active_session_id",
            sid
        );

        window.currentSessionId = sid;
        window.NOVA_SESSION_ID = sid;
    }


    function cleanText(el) {

        if (!el) {
            return "";
        }

        const clone =
            el.cloneNode(true);

        clone
            .querySelectorAll(
                "button, .message-actions, .bubble-actions"
            )
            .forEach(
                x => x.remove()
            );


        return String(
            clone.innerText ||
            clone.textContent ||
            ""
        )
        .replace(
            /\n{3,}/g,
            "\n\n"
        )
        .trim();
    }


    function openNew() {

        fetch(
            "/api/sessions/new",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body:
                    JSON.stringify({
                        source:
                            "mobile-top-actions"
                    })
            }
        )
        .then(
            r => r.json()
        )
        .then(
            data => {

                const sid =
                    data.session_id ||
                    data.id ||
                    data.sessionId ||
                    "";

                if (!sid) {
                    return;
                }


                setSessionId(sid);


                location.href =
                    "/mobile?session_id=" +
                    encodeURIComponent(sid) +
                    "&fresh=top-actions";
            }
        );
    }


    function openSessions() {

        if (
            typeof window.NovaMobileOpenSessions ===
            "function"
        ) {
            return window.NovaMobileOpenSessions();
        }

        console.warn(
            TAG,
            "sessions owner missing"
        );
    }


    async function runCopy() {

        const root =
            document.getElementById(
                "mobileChatMessages"
            );

        const text =
            cleanText(root);


        if (!text) {
            return;
        }


        await navigator.clipboard.writeText(
            text
        );
    }


    function runRegen() {

        const input =
            document.getElementById(
                "nova-mobile-input"
            );

        const send =
            document.getElementById(
                "nova-mobile-send"
            );


        if (!input || !send) {
            return;
        }


        input.focus();


        send.click();
    }


    function bindButton(id, fn) {

        const btn =
            document.getElementById(id);

        if (!btn) {
            return;
        }


        btn.onclick = function (event) {

            event.preventDefault();

            event.stopPropagation();

            fn();

            return false;
        };
    }


    function unparkRealHeaderButtons() {

        [
            "nova-mobile-new-chat",
            "nova-mobile-sessions-toggle"
        ]
        .forEach(id => {

            const el =
                document.getElementById(id);

            if (!el) {
                return;
            }

            el.classList.remove(
                "hidden",
                "nova-mobile-v10-parked"
            );

            el.style.removeProperty(
                "display"
            );
        });
    }


    function apply() {

        PARK_IDS.forEach(
            parkOldButton
        );


        unparkRealHeaderButtons();


        ensureRow();


        bindButton(
            "nova-mobile-row-new",
            openNew
        );


        bindButton(
            "nova-mobile-row-copy",
            runCopy
        );


        bindButton(
            "nova-mobile-row-regen",
            runRegen
        );


        console.log(
            TAG,
            "active"
        );
    }


    window.NovaMobileTopRowV10Apply20260625 =
        apply;


    window.NovaMobileTopRowV10OpenSessions20260625 =
        openSessions;


    document.addEventListener(
        "DOMContentLoaded",
        apply,
        {
            once: true
        }
    );

})();