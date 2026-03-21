// Function to authenticate and retrieve the token
function authenticate(username, password) {
    fetch("/api/authenticate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            // Store the token in local storage or a variable
            const token = data.token;
            console.log("Authenticated successfully. Token: ", token);

            // Now, use the token in the session creation request
            createSession(token);
        } else {
            console.error("Authentication failed: ", data.detail);
        }
    })
    .catch(error => console.error("Error during authentication:", error));
}

// Function to create a session using the token
function createSession(token) {
    fetch("/api/session/new", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`  // Use the token received from authentication
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        console.log("Session created:", data);
    })
    .catch(error => console.error("Error creating session:", error));
}

// Call the authenticate function
authenticate("validUser", "validPassword");
