(() => {
    // Публичный username бота, к которому привязано Mini App.
    const BOT_USERNAME = "se14569084_bot";

    async function copyText(text) {
        if (navigator.clipboard?.writeText && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return;
        }

        // Запасной вариант для WebView, где Clipboard API недоступен.
        const field = document.createElement("textarea");
        field.value = text;
        field.setAttribute("readonly", "");
        field.style.position = "fixed";
        field.style.opacity = "0";
        field.style.pointerEvents = "none";
        document.body.appendChild(field);
        field.select();

        const copied = document.execCommand("copy");
        field.remove();

        if (!copied) {
            throw new Error("Не удалось скопировать ссылку");
        }
    }

    window.shareIdea = async function shareIdea(ideaId, ideaName = "идею") {
        const id = String(ideaId ?? "");
        if (!/^\d+$/.test(id)) {
            window.showToast?.("Не удалось сформировать ссылку", "error");
            return;
        }

        const safeName = String(ideaName || "идею").trim();
        const ideaUrl = `https://max.ru/${BOT_USERNAME}?startapp=idea_${id}`;
        const message = `Посмотри идею «${safeName}» в ВЕКТОРЕ:\n${ideaUrl}`;
        const maxShareUrl = `https://max.ru/:share?text=${encodeURIComponent(message)}`;

        // Внутри MAX открываем штатный экран выбора чата.
        const platform = window.WebApp?.platform;
        const maxShareSupported = !platform || ["ios", "android", "web"].includes(platform);

        if (maxShareSupported && typeof window.WebApp?.openMaxLink === "function") {
            try {
                await window.WebApp.openMaxLink(maxShareUrl);
                return;
            } catch (error) {
                console.warn("MAX share deep link failed:", error);
            }
        }

        // В обычном браузере используем системное меню, если оно есть.
        if (typeof navigator.share === "function") {
            try {
                await navigator.share({
                    title: `Идея «${safeName}» в ВЕКТОРЕ`,
                    text: message,
                    url: ideaUrl,
                });
                return;
            } catch (error) {
                if (error?.name === "AbortError") return;
                console.warn("Web Share API failed, falling back to copy:", error);
            }
        }

        try {
            await copyText(ideaUrl);
            window.showToast?.("Ссылка скопирована!");
        } catch (error) {
            console.error("Share fallback failed:", error);
            window.showToast?.("Не удалось скопировать ссылку", "error");
        }
    };
})();
