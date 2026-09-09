(() => {
    "use strict";

    const API_BASE = "";

    const state = {
        account: null,
        plans: [],
        loading: false,
    };


    function $(id) {
        return document.getElementById(id);
    }


    function formatNumber(value) {
        return Number(
            value || 0
        ).toLocaleString();
    }


    function setText(id, value) {
        const element = $(id);

        if (!element) {
            return;
        }

        element.textContent = value;
    }


    function setStatus(message) {
        setText(
            "billing-account-status",
            message
        );
    }


    async function apiRequest(
        path,
        options = {}
    ) {
        const response = await fetch(
            API_BASE + path,
            {
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    ...(options.headers || {}),
                },
                ...options,
            }
        );

        let data = null;

        try {
            data = await response.json();
        } catch (error) {
            data = null;
        }

        if (!response.ok) {
            const message =
                data &&
                (
                    data.error ||
                    data.message
                )
                    ? (
                        data.error ||
                        data.message
                    )
                    : (
                        "Request failed."
                    );

            throw new Error(message);
        }

        return data || {};
    }


    function normalizePlan(plan) {
        return String(
            plan || "free"
        )
            .trim()
            .toLowerCase();
    }


    function updateUsage(account) {
        const credits = Number(
            account.credits || 0
        );

        const monthlyCredits = Number(
            account.monthly_credits || 0
        );

        const usedCredits = Math.max(
            0,
            monthlyCredits - credits
        );

        const usagePercent =
            monthlyCredits > 0
                ? Math.min(
                    100,
                    Math.round(
                        (
                            usedCredits /
                            monthlyCredits
                        ) * 100
                    )
                )
                : 0;

        setText(
            "billing-credits",
            formatNumber(credits)
        );

        setText(
            "billing-monthly-credits",
            formatNumber(monthlyCredits)
        );

        setText(
            "billing-used-credits",
            formatNumber(usedCredits)
        );

        setText(
            "billing-usage-percent",
            usagePercent + "%"
        );

        const usageBar = $(
            "billing-usage-bar"
        );

        if (usageBar) {
            usageBar.style.width =
                usagePercent + "%";
        }

        setText(
            "billing-usage-description",
            formatNumber(credits) +
            " of " +
            formatNumber(monthlyCredits) +
            " credits remaining this period."
        );
    }


    function updatePlan(account) {
        const plan = normalizePlan(
            account.plan
        );

        const label =
            plan.charAt(0).toUpperCase() +
            plan.slice(1);

        setText(
            "billing-current-plan",
            label
        );

        setText(
            "billing-plan-label",
            label
        );

        setStatus(
            plan === "free"
                ? "Free account"
                : "Active subscription"
        );

        document
            .querySelectorAll(
                ".billing-upgrade-button"
            )
            .forEach(
                (button) => {
                    const buttonPlan =
                        normalizePlan(
                            button.dataset.plan
                        );

                    const isCurrent =
                        buttonPlan === plan;

                    button.disabled = isCurrent;

                    if (isCurrent) {
                        button.textContent =
                            "Current Plan";
                    }
                }
            );

        const freeStatus = $(
            "billing-free-status"
        );

        if (freeStatus) {
            freeStatus.textContent =
                plan === "free"
                    ? "Current plan"
                    : "Available";
        }
    }


    function renderAccount(account) {
        state.account = account || {};

        updatePlan(state.account);

        updateUsage(state.account);
    }


    async function loadAccount() {
        setStatus(
            "Loading account..."
        );

        const data = await apiRequest(
            "/api/billing/account"
        );

        if (!data.ok) {
            throw new Error(
                data.error ||
                "Could not load billing account."
            );
        }

        renderAccount(
            data.account || data
        );

        return data;
    }


    async function loadPlans() {
        const data = await apiRequest(
            "/api/billing/plans"
        );

        if (data.ok) {
            state.plans =
                Array.isArray(data.plans)
                    ? data.plans
                    : [];
        }

        return data;
    }


    async function startCheckout(plan) {
        if (state.loading) {
            return;
        }

        plan = normalizePlan(plan);

        if (
            plan !== "plus" &&
            plan !== "pro"
        ) {
            return;
        }

        state.loading = true;

        const buttons =
            Array.from(
                document.querySelectorAll(
                    ".billing-upgrade-button"
                )
            );

        buttons.forEach(
            (button) => {
                button.disabled = true;
            }
        );

        setStatus(
            "Preparing checkout..."
        );

        try {
            const data = await apiRequest(
                "/api/billing/checkout",
                {
                    method: "POST",
                    body: JSON.stringify({
                        plan: plan,
                    }),
                }
            );

            if (!data.ok) {
                throw new Error(
                    data.error ||
                    "Checkout could not be started."
                );
            }

            const checkoutUrl =
                data.checkout_url ||
                data.url ||
                data.redirect_url ||
                "";

            if (checkoutUrl) {
                window.location.href =
                    checkoutUrl;
                return;
            }

            if (data.mode === "development") {
                setStatus(
                    "Development billing mode active."
                );

                await loadAccount();

                return;
            }

            if (data.message) {
                setStatus(
                    data.message
                );
            } else {
                setStatus(
                    "Checkout is ready but no redirect URL was returned."
                );
            }

        } catch (error) {
            console.error(
                "[Nova Billing] Checkout failed:",
                error
            );

            setStatus(
                error.message ||
                "Checkout failed."
            );

            alert(
                error.message ||
                "Could not start checkout."
            );

        } finally {
            state.loading = false;

            const currentPlan =
                normalizePlan(
                    state.account &&
                    state.account.plan
                );

            buttons.forEach(
                (button) => {
                    const buttonPlan =
                        normalizePlan(
                            button.dataset.plan
                        );

                    button.disabled =
                        buttonPlan === currentPlan;
                }
            );
        }
    }


    function bindUpgradeButtons() {
        document
            .querySelectorAll(
                ".billing-upgrade-button"
            )
            .forEach(
                (button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            startCheckout(
                                button.dataset.plan
                            );
                        }
                    );
                }
            );
    }


    async function initialize() {
        try {
            bindUpgradeButtons();

            await Promise.all([
                loadAccount(),
                loadPlans(),
            ]);

        } catch (error) {
            console.error(
                "[Nova Billing] Initialization failed:",
                error
            );

            setStatus(
                error.message ||
                "Billing information could not be loaded."
            );
        }
    }


    document.addEventListener(
        "DOMContentLoaded",
        initialize
    );


    window.NovaBilling = {
        state,
        loadAccount,
        loadPlans,
        startCheckout,
    };

})();
