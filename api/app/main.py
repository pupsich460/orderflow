from fastapi import FastAPI
from routers.routers import main_router
from shared.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="OrderFlow API", version="1.0.0")

app.include_router(main_router)


@app.on_event("startup")
async def on_startup():
    logger.info("OrderFlow API запущен")
