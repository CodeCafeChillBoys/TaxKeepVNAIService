from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.infrastructure.database import engine
from app.api.routes.tax_rule import tax_rule_routes
from app.api.routes.url_rule import url_rule_routes
from app.api.routes.ocr import dependent_ocr_routes


import asyncio
from app.messaging import start_rabbitmq_consumer, rabbitmq_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: kiểm tra kết nối database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"[ERROR] Database connection failed on startup: {e}")

    # Khởi động RabbitMQ consumer chạy ngầm
    consumer_task = asyncio.create_task(start_rabbitmq_consumer())

    yield

    # Shutdown logic: Dừng background consumer và đóng kết nối RabbitMQ
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await rabbitmq_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Tax AI Service - Bóc tách văn bản pháp luật và RAG hỏi đáp Luật Thuế",
    lifespan=lifespan
)

# Cấu hình CORS cho phép ASP.NET Core Backend và Frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router
app.include_router(tax_rule_routes.router)
app.include_router(url_rule_routes.router)
app.include_router(dependent_ocr_routes.router)

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    """Tự động chuyển hướng từ trang chủ sang giao diện Swagger UI"""
    return RedirectResponse(url="/docs")

