from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.infrastructure.database import engine
from app.api.routes import tax_rule_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: kiểm tra kết nối database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"[ERROR] Database connection failed on startup: {e}")
    yield
    # Shutdown logic nếu có


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

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    """Tự động chuyển hướng từ trang chủ sang giao diện Swagger UI"""
    return RedirectResponse(url="/docs")

