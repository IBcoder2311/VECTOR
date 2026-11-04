from fastapi.responses import RedirectResponse, JSONResponse


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]

        public_paths = (
            path == "/",
            path == "/auth/max",
            path.startswith("/static/"),
        )

        session = scope.get("session", {})
        is_authenticated = bool(session.get("user_id"))

        if any(public_paths) or is_authenticated:
            await self.app(scope, receive, send)
            return

        if method in ("GET", "HEAD"):
            response = RedirectResponse("/", status_code=303)
        else:
            response = JSONResponse(
                {"detail": "Требуется авторизация"},
                status_code=401,
            )

        await response(scope, receive, send)