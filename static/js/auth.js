(() => {
"use strict";
const API_BASE = "";

function getEl(id) {
    return document.getElementById(id);
}

async function apiFetch(path, options = {}) {

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

    let data = {};

    try {
        data = await response.json();
    } catch (error) {
        data = {};
    }

    if (!response.ok) {

        const message =
            data.error ||
            data.message ||
            "Something went wrong.";

        throw new Error(message);
    }

    return data;
}

async function login(
    username,
    password
) {

    return await apiFetch(
        "/api/auth/login",
        {
            method: "POST",

            body: JSON.stringify({
                username,
                password,
            }),
        }
    );
}

async function register(
    username,
    email,
    password
) {

    return await apiFetch(
        "/api/auth/register",
        {
            method: "POST",

            body: JSON.stringify({
                username,
                email,
                password,
            }),
        }
    );
}

async function logout() {

    return await apiFetch(
        "/api/auth/logout",
        {
            method: "POST",
        }
    );
}

async function forgotPassword(email) {

    return await apiFetch(
        "/api/auth/forgot-password",
        {
            method: "POST",

            body: JSON.stringify({
                email,
            }),
        }
    );
}

async function resetPassword(
    token,
    newPassword
) {

    return await apiFetch(
        "/api/auth/reset-password",
        {
            method: "POST",

            body: JSON.stringify({
                token,
                new_password: newPassword,
            }),
        }
    );
}

async function getAuthStatus() {

    return await apiFetch(
        "/api/auth/status",
        {
            method: "GET",
        }
    );
}


/*
------------------------------------------------
PUBLIC NOVA AUTH API
------------------------------------------------
*/

window.NovaAuth = {

    login,

    register,

    logout,

    forgotPassword,

    resetPassword,

    getAuthStatus,

};


/*
------------------------------------------------
PAGE ELEMENTS
------------------------------------------------
*/

const el = {

    loginForm:
        getEl("loginForm"),

    loginUsername:
        getEl("loginUsername"),

    loginPassword:
        getEl("loginPassword"),

    registerForm:
        getEl("registerForm"),

    registerUsername:
        getEl("registerUsername"),

    registerEmail:
        getEl("registerEmail"),

    registerEmailConfirm:
        getEl("registerEmailConfirm"),

    registerPassword:
        getEl("registerPassword"),

    registerPasswordConfirm:
        getEl("registerPasswordConfirm"),

    authMessage:
        getEl("authMessage"),

    registerMessage:
        getEl("registerMessage"),

    forgotPasswordForm:
        getEl("forgotPasswordForm"),

    forgotEmail:
        getEl("forgotEmail"),

    resetPasswordForm:
        getEl("resetPasswordForm"),

    resetToken:
        getEl("resetToken"),

    resetPassword:
        getEl("resetPassword"),

    resetPasswordConfirm:
        getEl("resetPasswordConfirm"),

};


/*
------------------------------------------------
MESSAGE HELPERS
------------------------------------------------
*/

function setMessage(
    target,
    message,
    type = "error"
) {

    if (!target) {
        return;
    }

    target.textContent =
        message || "";

    target.className =
        "message " + type;
}

function clearMessage(target) {

    if (!target) {
        return;
    }

    target.textContent = "";

    target.className =
        "message";
}


/*
------------------------------------------------
LOGIN
------------------------------------------------
*/

if (el.loginForm) {

    el.loginForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            clearMessage(
                el.authMessage
            );

            const username =
                el.loginUsername
                    ?.value
                    .trim() || "";

            const password =
                el.loginPassword
                    ?.value || "";

            if (!username || !password) {

                setMessage(
                    el.authMessage,
                    "Username or email and password are required.",
                    "error"
                );

                return;
            }

            const submitButton =
                el.loginForm.querySelector(
                    'button[type="submit"]'
                );

            const originalText =
                submitButton?.textContent;

            try {

                if (submitButton) {

                    submitButton.disabled =
                        true;

                    submitButton.textContent =
                        "Signing in...";
                }

                await login(
                    username,
                    password
                );

                setMessage(
                    el.authMessage,
                    "Signed in successfully.",
                    "success"
                );

                window.location.href =
                    "/app";

            } catch (error) {

                setMessage(
                    el.authMessage,
                    error.message ||
                    "Unable to sign in.",
                    "error"
                );

            } finally {

                if (submitButton) {

                    submitButton.disabled =
                        false;

                    submitButton.textContent =
                        originalText ||
                        "Sign in";
                }
            }
        }
    );
}


/*
------------------------------------------------
REGISTER
------------------------------------------------
*/

if (el.registerForm) {

    el.registerForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            clearMessage(
                el.registerMessage
            );

            const username =
                el.registerUsername
                    ?.value
                    .trim() || "";

            const email =
                el.registerEmail
                    ?.value
                    .trim()
                    .toLowerCase() || "";

            const emailConfirm =
                el.registerEmailConfirm
                    ?.value
                    .trim()
                    .toLowerCase() || "";

            const password =
                el.registerPassword
                    ?.value || "";

            const passwordConfirm =
                el.registerPasswordConfirm
                    ?.value || "";


            if (
                !username ||
                !email ||
                !emailConfirm ||
                !password ||
                !passwordConfirm
            ) {

                setMessage(
                    el.registerMessage,
                    "All fields are required.",
                    "error"
                );

                return;
            }


            if (
                email !== emailConfirm
            ) {

                setMessage(
                    el.registerMessage,
                    "Email addresses do not match.",
                    "error"
                );

                return;
            }


            if (
                password !== passwordConfirm
            ) {

                setMessage(
                    el.registerMessage,
                    "Passwords do not match.",
                    "error"
                );

                return;
            }


            if (
                password.length < 8
            ) {

                setMessage(
                    el.registerMessage,
                    "Password must be at least 8 characters.",
                    "error"
                );

                return;
            }


            const usernamePattern =
                /^[a-z0-9_-]{3,32}$/;

            if (
                !usernamePattern.test(
                    username
                )
            ) {

                setMessage(
                    el.registerMessage,
                    "Username must be 3–32 lowercase letters, numbers, underscores, or dashes.",
                    "error"
                );

                return;
            }


            const submitButton =
                el.registerForm.querySelector(
                    'button[type="submit"]'
                );

            const originalText =
                submitButton?.textContent;


            try {

                if (submitButton) {

                    submitButton.disabled =
                        true;

                    submitButton.textContent =
                        "Creating account...";
                }


                await register(
                    username,
                    email,
                    password
                );


                setMessage(
                    el.registerMessage,
                    "Account created successfully. Entering Nova...",
                    "success"
                );


                setTimeout(
                    () => {

                        window.location.href =
                            "/app";

                    },
                    500
                );


            } catch (error) {

                setMessage(
                    el.registerMessage,
                    error.message ||
                    "Unable to create account.",
                    "error"
                );


            } finally {

                if (submitButton) {

                    submitButton.disabled =
                        false;

                    submitButton.textContent =
                        originalText ||
                        "Create account";
                }
            }

        }
    );
}


/*
------------------------------------------------
FORGOT PASSWORD
------------------------------------------------
*/

if (el.forgotPasswordForm) {

    el.forgotPasswordForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            const messageTarget =
                getEl("authMessage") ||
                getEl("forgotPasswordMessage");

            clearMessage(
                messageTarget
            );

            const email =
                el.forgotEmail
                    ?.value
                    .trim()
                    .toLowerCase() || "";

            if (!email) {

                setMessage(
                    messageTarget,
                    "Email address is required.",
                    "error"
                );

                return;
            }

            try {

                const result =
                    await forgotPassword(
                        email
                    );

                setMessage(
                    messageTarget,
                    result.message ||
                    "If an account exists for that email, a password reset link has been sent.",
                    "success"
                );

            } catch (error) {

                setMessage(
                    messageTarget,
                    error.message ||
                    "Unable to process password reset.",
                    "error"
                );
            }
        }
    );
}


/*
------------------------------------------------
RESET PASSWORD
------------------------------------------------
*/

if (el.resetPasswordForm) {

    el.resetPasswordForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            const messageTarget =
                getEl("authMessage") ||
                getEl("resetPasswordMessage");

            clearMessage(
                messageTarget
            );

            const token =
                el.resetToken
                    ?.value
                    .trim() || "";

            const password =
                el.resetPassword
                    ?.value || "";

            const passwordConfirm =
                el.resetPasswordConfirm
                    ?.value || "";


            if (
                !token ||
                !password ||
                !passwordConfirm
            ) {

                setMessage(
                    messageTarget,
                    "All fields are required.",
                    "error"
                );

                return;
            }


            if (
                password !== passwordConfirm
            ) {

                setMessage(
                    messageTarget,
                    "Passwords do not match.",
                    "error"
                );

                return;
            }


            if (
                password.length < 8
            ) {

                setMessage(
                    messageTarget,
                    "Password must be at least 8 characters.",
                    "error"
                );

                return;
            }


            try {

                const result =
                    await resetPassword(
                        token,
                        password
                    );

                setMessage(
                    messageTarget,
                    result.message ||
                    "Password reset successfully.",
                    "success"
                );

                setTimeout(
                    () => {

                        window.location.href =
                            "/login";

                    },
                    1000
                );

            } catch (error) {

                setMessage(
                    messageTarget,
                    error.message ||
                    "Unable to reset password.",
                    "error"
                );
            }

        }
    );
}


console.log(
    "[NOVA AUTH] Production authentication loaded."
);
})();


