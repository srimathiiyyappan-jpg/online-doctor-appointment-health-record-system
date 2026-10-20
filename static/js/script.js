document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    if (form) {
        form.querySelectorAll('input, select, textarea').forEach(input => {
            input.addEventListener('focus', function () {
                input.classList.add('is-focused');
            });
        });
    }
});
