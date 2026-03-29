window.onload = function() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/static/login.html'; // Redirect to login if no token
    }

    // Fetch protected content
    fetch('/api/protected', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('content').innerHTML = data.content; // Show protected content
    })
    .catch(error => {
        console.error('Error fetching protected content:', error);
        window.location.href = '/static/login.html'; // Redirect if authentication fails
    });
};