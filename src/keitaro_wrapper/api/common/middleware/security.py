import hmac
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from keitaro_wrapper.api.common.responses.errors import error_response
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.config import Settings


async def security(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request.state.request_id = str(Identity.new())
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        expected_origin = f"{request.url.scheme}://{request.url.netloc}"
        token = request.headers.get("x-csrf-token", "")
        expected_token = str(request.session.get("csrf", ""))
        if (
            (origin and origin != expected_origin)
            or not expected_token
            or not hmac.compare_digest(token.encode(), expected_token.encode())
        ):
            return error_response(
                "csrf_failed",
                "Обновите страницу перед изменением данных.",
                request,
                403,
            )
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            return error_response("json_required", "Ожидается JSON-запрос.", request, 415)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def register_security(app: FastAPI, settings: Settings) -> None:
    app.middleware("http")(security)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key.get_secret_value(),
        session_cookie="wrapper_session",
        same_site="strict",
        max_age=86400,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts.split(","))
