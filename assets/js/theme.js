// The body already reflects defaultTheme; only a saved preference overrides it.
try {
    const preferred = localStorage.getItem('pref-theme');
    if (preferred === 'light' || preferred === 'dark') {
        document.body.classList.toggle('dark', preferred === 'dark');
    }
} catch {
    // Navigation and the configured theme remain usable when storage is blocked.
}
