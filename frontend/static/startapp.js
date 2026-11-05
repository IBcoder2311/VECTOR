
(() => {
    const startParam = window.WebApp?.initDataUnsafe?.start_param;
    const match = /^idea_(\d+)$/.exec(startParam || "");

    if (!match) return;

    const target = `/ideas/${match[1]}`;
    const key = `vector_startapp_${startParam}`;

    if (sessionStorage.getItem(key)) return;

    sessionStorage.setItem(key, "1");

    if (window.location.pathname !== target) {
        window.location.replace(target);
    }
})();
