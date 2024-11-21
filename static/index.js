const signUpButton = document.getElementById('debed');
const signInButton = document.getElementById('embed');
const container = document.getElementById('container');

// Toggle to the decryption panel
signUpButton.addEventListener('click', () => {
    container.classList.add("right-panel-active");
});

// Toggle to the encryption panel
signInButton.addEventListener('click', () => {
    container.classList.remove("right-panel-active");
});
