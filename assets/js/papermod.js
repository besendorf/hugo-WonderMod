import * as params from '@params';

function scrollToTop() {
    const topButton = document.getElementById('top-link');
    if (!topButton) return;
    let ticking = false;
    const update = () => {
        topButton.classList.toggle('is-visible', window.scrollY > 600);
        ticking = false;
    };
    window.addEventListener('scroll', () => {
        if (!ticking) {
            ticking = true;
            requestAnimationFrame(update);
        }
    }, { passive: true });
    update();
}

function themeToggle() {
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        const dark = document.body.classList.toggle('dark');
        try { localStorage.setItem('pref-theme', dark ? 'dark' : 'light'); } catch {}
    });
}

function showCodeCopyButtons() {
    document.querySelectorAll('pre > code').forEach((codeblock) => {
        // Chroma renders table line numbers in a separate code element.
        if (codeblock.querySelector('.lnt')) return;
        const copybutton = document.createElement('button');
        copybutton.type = 'button';
        copybutton.classList.add('copy-code');
        const label = params.copyLabel || 'copy';
        copybutton.textContent = label;
        copybutton.addEventListener('click', async () => {
            try {
                const text = codeblock.cloneNode(true);
                text.querySelectorAll('.ln').forEach(number => number.remove());
                await navigator.clipboard.writeText(text.textContent);
                copybutton.textContent = params.copiedLabel || 'copied!';
                setTimeout(() => { copybutton.textContent = label; }, 2000);
            } catch {
                // Leave the code selectable if clipboard permission is unavailable.
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(codeblock);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        });
        const container = codeblock.closest('.highlight') || codeblock.parentElement;
        container.appendChild(copybutton);
    });
}

function openToc() {
    const toc = document.getElementById('toc');
    if (toc && window.innerWidth > 1500 && window.innerHeight > 800) toc.open = true;
}

function progressBar() {
    const bar = document.getElementById('progressBar');
    if (!bar) return;
    let ticking = false;
    const update = () => {
        const height = document.documentElement.scrollHeight - window.innerHeight;
        const percent = height > 0 ? window.scrollY / height * 100 : 0;
        bar.style.setProperty('--scrollAmount', (percent >= 99 ? 0 : percent) + '%');
        ticking = false;
    };
    window.addEventListener('scroll', () => {
        if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
}

if (params.scrollToTop) scrollToTop();
if (params.themeToggle) themeToggle();
if (params.showCodeCopyButtons) showCodeCopyButtons();
openToc();
progressBar();
