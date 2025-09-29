/**
 * JavaScript para el sistema de autenticación
 * PIE: Código expresivo y fácil de entender con funciones bien nombradas
 */

// DRY: Funciones reutilizables para validación
class FormValidator {
    /**
     * Valida formato de DNI argentino
     * POLA: Esta función tiene una única responsabilidad
     */
    static validateDNI(dni) {
        if (!dni) {
            return { isValid: false, message: 'El DNI no puede estar vacío' };
        }
        
        if (!/^\d+$/.test(dni)) {
            return { isValid: false, message: 'El DNI debe contener solo números' };
        }
        
        if (dni.length < 6 || dni.length > 8) {
            return { isValid: false, message: 'El DNI debe tener entre 6 y 8 dígitos' };
        }
        
        return { isValid: true, message: 'DNI válido' };
    }

    /**
     * Valida fortaleza de contraseña
     */
    static validatePassword(password) {
        if (password.length < 8 || password.length > 12) {
            return { isValid: false, message: 'La contraseña debe tener entre 8 y 12 caracteres' };
        }
        
        if (!/(?=.*[A-Z])/.test(password)) {
            return { isValid: false, message: 'Debe contener al menos una mayúscula' };
        }
        
        if (!/(?=.*[!@#$%^&*(),.?":{}|<>])/.test(password)) {
            return { isValid: false, message: 'Debe contener al menos un carácter especial' };
        }
        
        return { isValid: true, message: 'Contraseña válida' };
    }

    /**
     * Valida que dos contraseñas coincidan
     * KISS: Función simple y directa
     */
    static validatePasswordMatch(password, confirmPassword) {
        return password === confirmPassword;
    }
}

// Utilidades para el administrador
class AdminUtils {
    /**
     * Cambia el estado de un usuario via AJAX
     */
    static changeUserStatus(dni, newStatus) {
        if (!confirm(`¿Está seguro de cambiar el estado a ${newStatus}?`)) {
            return;
        }

        const formData = new FormData();
        formData.append('dni', dni);
        formData.append('new_status', newStatus);

        fetch('/admin/change_status', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Estado cambiado exitosamente');
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al cambiar el estado');
        });
    }

    /**
     * Cambia la contraseña de un usuario
     */
    static changeUserPassword(dni) {
        const newPassword = prompt('Ingrese la nueva contraseña:');
        
        if (!newPassword) return;

        // Validar contraseña en cliente
        const validation = FormValidator.validatePassword(newPassword);
        if (!validation.isValid) {
            alert('Error: ' + validation.message);
            return;
        }

        const formData = new FormData();
        formData.append('dni', dni);
        formData.append('new_password', newPassword);

        fetch('/admin/change_password', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Contraseña cambiada exitosamente');
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al cambiar la contraseña');
        });
    }
}

// Inicialización cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
    // Validación en tiempo real para formularios de registro
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        initializeRegisterFormValidation(registerForm);
    }

    // Validación para formulario de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        initializeLoginFormValidation(loginForm);
    }
});

/**
 * Inicializa la validación en tiempo real para el formulario de registro
 */
function initializeRegisterFormValidation(form) {
    const dniInput = form.querySelector('input[name="dni"]');
    const passwordInput = form.querySelector('input[name="password"]');
    const confirmPasswordInput = form.querySelector('input[name="confirm_password"]');

    // Validar DNI en tiempo real
    if (dniInput) {
        dniInput.addEventListener('blur', function() {
            const validation = FormValidator.validateDNI(this.value);
            showValidationMessage(this, validation);
        });
    }

    // Validar contraseña en tiempo real
    if (passwordInput) {
        passwordInput.addEventListener('blur', function() {
            const validation = FormValidator.validatePassword(this.value);
            showValidationMessage(this, validation);
        });
    }

    // Validar coincidencia de contraseñas
    if (confirmPasswordInput && passwordInput) {
        confirmPasswordInput.addEventListener('blur', function() {
            const isValid = FormValidator.validatePasswordMatch(
                passwordInput.value, 
                this.value
            );
            const validation = {
                isValid: isValid,
                message: isValid ? 'Las contraseñas coinciden' : 'Las contraseñas no coinciden'
            };
            showValidationMessage(this, validation);
        });
    }
}

/**
 * Inicializa validación básica para login
 */
function initializeLoginFormValidation(form) {
    form.addEventListener('submit', function(e) {
        const dni = form.querySelector('input[name="dni"]').value;
        const password = form.querySelector('input[name="password"]').value;

        if (!dni || !password) {
            e.preventDefault();
            alert('Por favor complete todos los campos');
            return false;
        }

        return true;
    });
}

/**
 * Muestra mensajes de validación en los campos del formulario
 */
function showValidationMessage(inputElement, validation) {
    // Remover mensaje anterior
    const existingMessage = inputElement.parentNode.querySelector('.validation-message');
    if (existingMessage) {
        existingMessage.remove();
    }

    // Crear nuevo mensaje
    const message = document.createElement('div');
    message.className = `validation-message ${validation.isValid ? 'valid' : 'invalid'}`;
    message.textContent = validation.message;
    message.style.fontSize = '0.8rem';
    message.style.marginTop = '0.25rem';
    message.style.color = validation.isValid ? 'green' : 'red';

    inputElement.parentNode.appendChild(message);

    // Cambiar borde del input
    inputElement.style.borderColor = validation.isValid ? 'green' : 'red';
}

// Funciones globales para uso en templates
window.FormValidator = FormValidator;
window.AdminUtils = AdminUtils;