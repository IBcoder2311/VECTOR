document.addEventListener("DOMContentLoaded", () => {
    const viewport = document.getElementById("category-viewport");
    const track = document.getElementById("category-track");

    if (!viewport || !track) return;

    let position = 0;
    let paused = false;
    let previousTime = 0;
    let resumeTimeout;

    const speed = 40;

    function stop() {
        paused = true;
        clearTimeout(resumeTimeout);
    }

    function resume() {
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

        const halfWidth = track.scrollWidth / 2;

        if (!paused && halfWidth > 0) {
            position += speed * delta;

            if (position >= halfWidth) {
                position -= halfWidth;
            }

            track.style.transform = `translateX(-${position}px)`;
        }

        requestAnimationFrame(animate);
    }

    viewport.addEventListener("mouseenter", stop);
    viewport.addEventListener("mouseleave", resume);

    viewport.addEventListener("touchstart", stop, { passive: true });
    viewport.addEventListener("touchend", resume, { passive: true });
    viewport.addEventListener("touchcancel", resume, { passive: true });

    viewport.addEventListener("wheel", () => {
        stop();
        resume();
    }, { passive: true });

    viewport.addEventListener("focusin", stop);
    viewport.addEventListener("focusout", resume);

    requestAnimationFrame(animate);
});