// theme-toggle.js - Handles dark/light theme switching

export function initThemeToggle() {
    const savedTheme = localStorage.getItem('quantum_theme') || 'dark';
    document.body.className = `theme-${savedTheme}`;
    updateToggleIcons();
}

export function toggleTheme() {
    const isDark = document.body.classList.contains('theme-dark');
    if (isDark) {
        document.body.className = 'theme-light';
        localStorage.setItem('quantum_theme', 'light');
    } else {
        document.body.className = 'theme-dark';
        localStorage.setItem('quantum_theme', 'dark');
    }
    updateToggleIcons();
}

export function updateToggleIcons() {
    const isDark = document.body.classList.contains('theme-dark');
    document.querySelectorAll('.btn-theme-toggle').forEach(btn => {
        btn.innerHTML = isDark ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
        btn.title = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    });
}
