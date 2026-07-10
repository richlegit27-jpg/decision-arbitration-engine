(function () {
    "use strict";

    const MARK = "NOVA_HOME_FINAL_POLISH_20260709";

    if (window.__NOVA_HOME_FINAL_POLISH_20260709__) {
        return;
    }

    window.__NOVA_HOME_FINAL_POLISH_20260709__ = true;

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn, { once: true });
        } else {
            fn();
        }
    }

    function firstExisting(selectors) {
        for (const selector of selectors) {
            const found = document.querySelector(selector);
            if (found) return found;
        }
        return null;
    }

    function insertAfter(target, node) {
        if (!target || !target.parentNode) {
            document.body.appendChild(node);
            return;
        }

        if (target.nextSibling) {
            target.parentNode.insertBefore(node, target.nextSibling);
            return;
        }

        target.parentNode.appendChild(node);
    }

    function makeAnnouncement() {
        if (document.querySelector("[data-nova-home-polish-announcement]")) {
            return;
        }

        const bar = document.createElement("div");
        bar.className = "nova-home-polish-announcement";
        bar.dataset.novaHomePolishAnnouncement = "1";
        bar.innerHTML = `
            <div class="nova-home-polish-announcement-inner">
                <div>
                    <strong>Nova is moving from prototype to launch polish.</strong>
                    <span>Public pages, legal links, sitemap, robots, favicon, social preview, and release checks are now wired.</span>
                </div>
                <a href="/contact">Join early access</a>
            </div>
        `;

        document.body.insertBefore(bar, document.body.firstChild);
    }

    function makeProofCards() {
        if (document.querySelector("[data-nova-home-polish-proof]")) {
            return;
        }

        const anchor = firstExisting([
            "main section",
            "main",
            ".hero",
            ".nova-hero",
            ".landing-hero",
            "header"
        ]);

        const proof = document.createElement("section");
        proof.className = "nova-home-polish-shell nova-home-polish-proof";
        proof.dataset.novaHomePolishProof = "1";
        proof.innerHTML = `
            <div class="nova-home-polish-proof-card">
                <b>Project memory</b>
                <span>Keep long-running build context instead of restarting every conversation.</span>
            </div>
            <div class="nova-home-polish-proof-card">
                <b>Sessions</b>
                <span>Return to previous work, compare threads, and keep project history alive.</span>
            </div>
            <div class="nova-home-polish-proof-card">
                <b>Uploads</b>
                <span>Bring files, images, notes, and code into the workspace when building.</span>
            </div>
            <div class="nova-home-polish-proof-card">
                <b>Billing-ready</b>
                <span>Credit and model-tier foundations are prepared for real usage later.</span>
            </div>
        `;

        insertAfter(anchor, proof);
    }

    function makeBuilderSection() {
        if (document.querySelector("[data-nova-home-polish-builder]")) {
            return;
        }

        const section = document.createElement("section");
        section.className = "nova-home-polish-section";
        section.dataset.novaHomePolishBuilder = "1";
        section.innerHTML = `
            <h2>Built for people shipping real projects.</h2>
            <p>
                Nova is not just a chat screen. It is a project command center for keeping context,
                restoring sessions, working with uploads, tracking useful memory, and turning messy
                build work into a cleaner workflow.
            </p>

            <div class="nova-home-polish-grid">
                <div class="nova-home-polish-feature">
                    <strong>Less restart pain</strong>
                    <span>Carry project context forward instead of explaining the same thing again and again.</span>
                </div>
                <div class="nova-home-polish-feature">
                    <strong>Cleaner build loops</strong>
                    <span>Use sessions, files, and project state to keep frontend/backend work organized.</span>
                </div>
                <div class="nova-home-polish-feature">
                    <strong>Launch foundation</strong>
                    <span>Public pages, SEO basics, legal pages, contact, and release checks are now in place.</span>
                </div>
            </div>

            <div class="nova-home-polish-cta-row">
                <a class="nova-home-polish-primary" href="/richard-login">Open Nova</a>
                <a class="nova-home-polish-secondary" href="/contact">Request early access</a>
            </div>
        `;

        const footer = document.querySelector("footer");
        if (footer && footer.parentNode) {
            footer.parentNode.insertBefore(section, footer);
        } else {
            document.body.appendChild(section);
        }
    }

    function makeStickyCta() {
        if (document.querySelector("[data-nova-home-polish-sticky-cta]")) {
            return;
        }

        const cta = document.createElement("div");
        cta.className = "nova-home-polish-sticky-cta";
        cta.dataset.novaHomePolishStickyCta = "1";
        cta.innerHTML = `
            <span>Ready to keep building?</span>
            <a href="/richard-login">Open Nova</a>
        `;

        document.body.appendChild(cta);
    }

    ready(function () {
        document.documentElement.dataset.novaHomeFinalPolish = "1";
        makeAnnouncement();
        makeProofCards();
        makeBuilderSection();
        makeStickyCta();
        console.log("[" + MARK + "] ready");
    });
})();
