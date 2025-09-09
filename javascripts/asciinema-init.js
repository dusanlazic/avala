document$.subscribe(() => {
    const nodes = document.querySelectorAll('[data-asciinema]');
    nodes.forEach((el) => {
        if (el.dataset.asciinemaInitialized) return;
        el.dataset.asciinemaInitialized = '1';

        const src = el.dataset.src;
        const cols = Number(el.dataset.cols || 113);
        const rows = Number(el.dataset.rows || 18);
        const idle = Number(el.dataset.idle || 2);

        if (window.AsciinemaPlayer) {
            el.textContent = '';
            AsciinemaPlayer.create(src, el, { cols, rows, idleTimeLimit: idle });
        } else {
            el.textContent = '⚠️ Refresh to see the player';
            console.error('AsciinemaPlayer is not loaded');
        }
    });
});
