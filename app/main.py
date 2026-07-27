from fastapi import FastAPI

from app.api.routes.system import router as system_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="quantStock1", version="0.1.0")
app.include_router(system_router)
