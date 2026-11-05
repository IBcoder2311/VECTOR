(async () => {
    const initData = window.WebApp?.initData;

    if (!initData) {
        console.error("MAX initData не получены");
        return;
    }

    const startParam = window.WebApp?.initDataUnsafe?.start_param;
    const match = /^idea_(\d+)$/.exec(startParam || "");

    const returnTo = match
        ? `/ideas/${match[1]}`
        : "/";

    try {
        const response = await fetch("/auth/max", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                init_data: initData,
                return_to: returnTo
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail);
        }

        if (data.ok) {
            window.location.replace(data.redirect_url || "/");
        }

    } catch (error) {
        console.error("Ошибка авторизации:", error);
    }
})();