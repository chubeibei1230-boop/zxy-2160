import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from routers.reception_router import router as reception_router
from routers.supervisor_router import router as supervisor_router
from routers.stats_router import router as stats_router, run_anomaly_detection

anomaly_detection_task: Optional[asyncio.Task] = None


async def anomaly_detection_loop():
    while True:
        try:
            _ = run_anomaly_detection()
        except Exception:
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global anomaly_detection_task
    anomaly_detection_task = asyncio.create_task(anomaly_detection_loop())
    try:
        yield
    finally:
        if anomaly_detection_task and not anomaly_detection_task.done():
            anomaly_detection_task.cancel()
            try:
                await anomaly_detection_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="训练室短时储物格预约管理 RESTful API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(reception_router)
app.include_router(supervisor_router)
app.include_router(stats_router)


@app.get("/", tags=["根路径"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
