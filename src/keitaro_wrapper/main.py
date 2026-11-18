from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from keitaro_wrapper.api.common.exception_handlers import register_exception_handlers
from keitaro_wrapper.api.common.middleware.security import register_security
from keitaro_wrapper.api.health.handlers import router as health_router
from keitaro_wrapper.api.v1.router import router as api_router
from keitaro_wrapper.bootstrap.container import Container
from keitaro_wrapper.bootstrap.lifespan import ApplicationLifespan
from keitaro_wrapper.config import Settings
from keitaro_wrapper.web.routes import WEB_ROOT
from keitaro_wrapper.web.routes import router as web_router


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or Settings()
    services = container or Container(settings)
    app = FastAPI(title="Keitaro Wrapper", version="0.1.0", lifespan=ApplicationLifespan(services))
    app.state.container = services
    register_security(app, settings)
    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(health_router)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")
    return app
