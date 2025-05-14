document.addEventListener('DOMContentLoaded', () => {
    const burger = document.querySelector('.burger');
    const navLinks = document.querySelector('.nav-links');

    burger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });
});

/* funcionamiento del formulario */
document.getElementById('contact-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const submitButton = this.querySelector('button[type="submit"]');
    submitButton.classList.add('loading');

    const formData = new FormData(this);

    fetch('http://127.0.0.1:5000/send_email', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(data => {
        showFlashMessage('Mensaje enviado correctamente.', 'success');
        this.reset(); // limpia el formulario
        submitButton.classList.remove('loading');
    })
    .catch(error => {
        showFlashMessage('Hubo un error al enviar tu mensaje.', 'danger');
        console.error('Error:', error);
        submitButton.classList.remove('loading');
    });
});

function showFlashMessage(message, category) {
    const flashContainer = document.getElementById('flash-messages');
    const flashMessage = document.createElement('div');
    flashMessage.className = `alert ${category}`;
    flashMessage.textContent = message;

    flashContainer.appendChild(flashMessage);

    setTimeout(() => {
        flashMessage.remove();
    }, 5000);
}

function eliminarConsultas() {
    const password = prompt("Introduce la contraseña para eliminar las consultas del día:");

    if (password) {
        fetch('/eliminar_consultas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                mostrarToast();
                setTimeout(() => {
                    location.reload(); // Recarga después de mostrar el toast
                }, 1500); // 1.5 segundos después
            } else {
                alert(data.message);
            }
        });
    }
}

function mostrarToast() {
    const toastElement = document.getElementById('successToast');
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

