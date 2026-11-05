document.addEventListener("DOMContentLoaded", () => {
    const viewport = document.getElementById("category-viewport");
    const track = document.getElementById("category-track");

    if (!viewport || !track) return;

    const selected = viewport.dataset.selected === "true";

    let paused = selected;
    let animationFrame;
    let previousTime = 0;
    let resumeTimeout;

    const speed = 40;

    function stop() {
        paused = true;
        clearTimeout(resumeTimeout);
    }

    function resume() {
        if (selected) return;

        clearTimeout(resumeTimeout);

        resumeTimeout = setTimeout(() => {
            paused = false;
            previousTime = 0;
        }, 1200);
    }

    function animate(time) {
        if (!previousTime) previousTime = time;

        const delta = Math.min((time - previousTime) / 1000, 0.05);
        previousTime = time;

        if (!paused) {
            const halfWidth = track.scrollWidth / 2;

            if (halfWidth > 0) {
                viewport.scrollLeft += speed * delta;

                if (viewport.scrollLeft >= halfWidth) {
                    viewport.scrollLeft -= halfWidth;
                }
            }
        }

        animationFrame = requestAnimationFrame(animate);
    }

    // Компьютер
    viewport.addEventListener("mouseenter", stop);
    viewport.addEventListener("mouseleave", resume);

    // Телефон
    viewport.addEventListener("touchstart", stop, { passive: true });
    viewport.addEventListener("touchend", resume, { passive: true });
    viewport.addEventListener("touchcancel", resume, { passive: true });

    // Ручная прокрутка
    viewport.addEventListener("wheel", () => {
        stop();
        resume();
    }, { passive: true });

    // Клавиатура
    viewport.addEventListener("focusin", stop);
    viewport.addEventListener("focusout", resume);

    animationFrame = requestAnimationFrame(animate);
});