from fastapi import FastAPI

from app.api.routes.system import router as system_router
from app.core.logging import configure_logging
from app.core.version import APP_VERSION

configure_logging()

app = FastAPI(title="quantStock1", version=APP_VERSION)
app.include_router(system_router)
