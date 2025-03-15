document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("authForm");
    const toggleButton = document.getElementById("toggleButton");
    const submitButton = document.getElementById("submitButton");
    const formTitle = document.getElementById("formTitle");
    const errorMessage = document.getElementById("errorMessage");
    let isLogin = true;

    toggleButton.addEventListener("click", () => {
        isLogin = !isLogin;
        formTitle.innerText = isLogin ? "Login" : "Register";
        submitButton.innerText = isLogin ? "Login" : "Register";
        toggleButton.innerText = isLogin ? "Register" : "Login";
        errorMessage.innerText = ""; // Clear any previous messages
    });

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value.trim();

        if (username === "" || password === "") {
            errorMessage.innerText = "Please fill in all fields.";
            errorMessage.style.color = "red";
            return;
        }

        if (isLogin) {
            // Simulate login logic (Replace this with actual backend validation)
            console.log("Logging in:", username);
            errorMessage.innerText = `Welcome back, ${username}!`;
            errorMessage.style.color = "green";
        } else {
            // Simulate registration logic
            console.log("Registering:", username);
            errorMessage.innerText = `Registered successfully! Welcome, ${username}.`;
            errorMessage.style.color = "green";
            // Optionally, switch to login mode after registration
            setTimeout(() => {
                isLogin = true;
                formTitle.innerText = "Login";
                submitButton.innerText = "Login";
                toggleButton.innerText = "Register";
                errorMessage.innerText = "";
            }, 2000);
        }
    });
});