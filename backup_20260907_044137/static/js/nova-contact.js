(function () {
    "use strict";

    if (window.__NOVA_CONTACT_PAGE_20260709__) {
        return;
    }

    window.__NOVA_CONTACT_PAGE_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-contact-ready", "true");
        console.log("[NOVA CONTACT] page ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();

// NOVA_CONTACT_LEAD_CAPTURE_20260709
(function () {
    "use strict";

    const MARK = "NOVA_CONTACT_LEAD_CAPTURE_20260709";

    if (window.__NOVA_CONTACT_LEAD_CAPTURE_20260709__) {
        return;
    }

    window.__NOVA_CONTACT_LEAD_CAPTURE_20260709__ = true;

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn, { once: true });
        } else {
            fn();
        }
    }

    function isContactPage() {
        return /\/contact\/?$|\/early-access\/?$/i.test(location.pathname);
    }

    function ensureStatus(form) {
        let status = form.querySelector("[data-nova-lead-status]");

        if (!status) {
            status = document.createElement("div");
            status.dataset.novaLeadStatus = "1";
            status.style.cssText = "margin-top:10px;font-size:13px;color:rgba(226,232,240,.78);";
            form.appendChild(status);
        }

        return status;
    }

    function collectForm(form) {
        const data = {};

        form.querySelectorAll("input, textarea, select").forEach(function (field) {
            const name = field.name || field.id || field.getAttribute("aria-label") || "";
            if (!name) return;

            if ((field.type === "checkbox" || field.type === "radio") && !field.checked) {
                return;
            }

            data[name] = field.value || "";
        });

        data.source = data.source || form.dataset.novaLeadSource || location.pathname;
        data.page = location.pathname;

        return data;
    }

    function endpointFor(form) {
        const source = String(form.dataset.novaLeadSource || form.id || form.action || location.pathname).toLowerCase();

        if (source.includes("early")) {
            return "/api/early-access";
        }

        return "/api/contact";
    }

    async function submitLead(form) {
        const status = ensureStatus(form);
        const button = form.querySelector("button[type='submit'], button:not([type])");
        const oldText = button ? button.textContent : "";

        status.textContent = "Sending…";

        if (button) {
            button.disabled = true;
            button.textContent = "Sending…";
        }

        try {
            const response = await fetch(endpointFor(form), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(collectForm(form))
            });

            const payload = await response.json().catch(function () {
                return {};
            });

            if (!response.ok || payload.ok === false) {
                throw new Error(payload.error || "Could not submit right now.");
            }

            status.textContent = payload.message || "Thanks — received.";
            form.dataset.novaLeadSubmitted = "1";

            form.querySelectorAll("input, textarea").forEach(function (field) {
                if (field.type !== "hidden") {
                    field.value = "";
                }
            });
        } catch (error) {
            status.textContent = error && error.message ? error.message : "Could not submit right now.";
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = oldText || "Send";
            }
        }
    }

    function makeFallbackForm() {
        if (document.querySelector("[data-nova-lead-form]")) {
            return;
        }

        const mount =
            document.querySelector("main") ||
            document.querySelector(".nova-contact") ||
            document.body;

        const section = document.createElement("section");
        section.style.cssText = "width:min(920px,calc(100% - 32px));margin:34px auto;padding:24px;border:1px solid rgba(226,214,255,.16);border-radius:26px;background:rgba(255,255,255,.055);";
        section.innerHTML = `
            <h2 style="margin:0 0 8px;color:#fff;font-size:30px;letter-spacing:-.04em;">Contact / early access</h2>
            <p style="margin:0 0 18px;color:rgba(226,232,240,.72);line-height:1.55;">Leave a note and Richard can follow up.</p>
            <form data-nova-lead-form="1" data-nova-lead-source="contact" style="display:grid;gap:10px;">
                <input name="name" autocomplete="name" placeholder="Name" style="min-height:44px;border-radius:14px;border:1px solid rgba(226,214,255,.18);background:rgba(7,6,12,.45);color:#fff;padding:0 13px;">
                <input name="email" type="email" autocomplete="email" placeholder="Email" style="min-height:44px;border-radius:14px;border:1px solid rgba(226,214,255,.18);background:rgba(7,6,12,.45);color:#fff;padding:0 13px;">
                <select name="interest" style="min-height:44px;border-radius:14px;border:1px solid rgba(226,214,255,.18);background:rgba(7,6,12,.45);color:#fff;padding:0 13px;">
                    <option value="early_access">Early access</option>
                    <option value="product_question">Product question</option>
                    <option value="billing_question">Billing question</option>
                    <option value="other">Other</option>
                </select>
                <textarea name="message" placeholder="Message" rows="4" style="border-radius:14px;border:1px solid rgba(226,214,255,.18);background:rgba(7,6,12,.45);color:#fff;padding:13px;resize:vertical;"></textarea>
                <button type="submit" style="min-height:44px;border:0;border-radius:999px;background:#b8ff7a;color:#101014;font-weight:900;">Send</button>
            </form>
        `;

        mount.appendChild(section);
    }

    function bindForms() {
        if (!isContactPage()) {
            return;
        }

        makeFallbackForm();

        document.querySelectorAll("form").forEach(function (form) {
            if (form.dataset.novaLeadBound === "1") {
                return;
            }

            const hasInputs = !!form.querySelector("input, textarea, select");

            if (!hasInputs) {
                return;
            }

            form.dataset.novaLeadBound = "1";

            if (!form.dataset.novaLeadForm) {
                form.dataset.novaLeadForm = "1";
            }

            form.addEventListener("submit", function (event) {
                event.preventDefault();
                submitLead(form);
            });
        });
    }

    ready(bindForms);
    window.NovaContactLeadCaptureBind = bindForms;

    console.log("[" + MARK + "] ready");
})();
// /NOVA_CONTACT_LEAD_CAPTURE_20260709

/* NOVA_CONTACT_CAPTURE_FORM_20260709 */
(function () {
    "use strict";

    const form = document.getElementById("nova-contact-form-20260709");
    const status = document.getElementById("nova-contact-form-status-20260709");

    if (!form || !status) {
        return;
    }

    function setStatus(message, mode) {
        status.textContent = message || "";
        status.dataset.mode = mode || "";
    }

    function getValue(name) {
        const field = form.elements[name];
        return field ? String(field.value || "").trim() : "";
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const payload = {
            name: getValue("name"),
            email: getValue("email"),
            interest: getValue("interest") || "early_access",
            message: getValue("message"),
            source: getValue("source") || "public_contact_page"
        };

        if (!payload.name || !payload.email || !payload.message) {
            setStatus("Please add your name, email, and message.", "error");
            return;
        }

        setStatus("Saving lead…", "loading");

        try {
            const response = await fetch("/api/contact", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            let data = {};
            try {
                data = await response.json();
            } catch (error) {
                data = {};
            }

            if (!response.ok || data.ok === false) {
                throw new Error(data.error || "Lead save failed");
            }

            form.reset();
            setStatus("Saved. Nova has your contact request.", "success");
        } catch (error) {
            console.error("[Nova Contact] submit failed", error);
            setStatus("Could not save yet. Please try again.", "error");
        }
    });
})();
