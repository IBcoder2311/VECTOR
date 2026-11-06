
(() => {
    "use strict";

    const STORAGE_KEY = "vector-theme";
    const THEMES = ["dark", "light", "system"];
    const root = document.documentElement;

    const media = window.matchMedia
        ? window.matchMedia("(prefers-color-scheme: dark)")
        : null;

    function readTheme() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            return THEMES.includes(saved) ? saved : "dark";
        } catch {
            return "dark";
        }
    }

    function resolveTheme(theme) {
        if (theme === "system") {
            return media?.matches ? "dark" : "light";
        }

        return THEMES.includes(theme) ? theme : "dark";
    }

    function applyTheme(theme) {
        const actualTheme = resolveTheme(theme);

        root.setAttribute("data-bs-theme", actualTheme);
        root.setAttribute("data-theme", actualTheme);
        root.style.colorScheme = actualTheme;

        const select = document.getElementById("theme-select");
        if (select) select.value = theme;

        return actualTheme;
    }

    window.getVectorTheme = readTheme;

    window.applyVectorTheme = (theme, save = false) => {
        const selected = THEMES.includes(theme) ? theme : "dark";

        if (save) {
            try {
                localStorage.setItem(STORAGE_KEY, selected);
            } catch (error) {
                console.error("Ошибка сохранения темы:", error);
            }
        }

        const actualTheme = applyTheme(selected);

        window.dispatchEvent(new CustomEvent("vector:themechange", {
            detail: { selectedTheme: selected, actualTheme }
        }));

        return actualTheme;
    };

    applyTheme(readTheme());

    document.addEventListener("DOMContentLoaded", () => {
        applyTheme(readTheme());

        const select = document.getElementById("theme-select");

        if (select) {
            select.addEventListener("change", () => {
                window.applyVectorTheme(select.value, true);
            });
        }
    });

    if (media) {
        const handleChange = () => {
            if (readTheme() === "system") {
                applyTheme("system");
            }
        };

        if (media.addEventListener) {
            media.addEventListener("change", handleChange);
        } else {
            media.addListener(handleChange);
        }
    }
})();
