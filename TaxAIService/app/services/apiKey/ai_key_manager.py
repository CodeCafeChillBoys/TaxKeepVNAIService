import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from google import genai

from app.core.config import settings
from app.models.ai_provider_key import AiProviderKey
from app.schemas.apiKey.ai_provider_key_schema import AiKeyCreateRequest, AiKeyUpdateRequest, AiKeyResponse

logger = logging.getLogger(__name__)

class AiKeyManager:
    @staticmethod
    def mask_key(raw_key: str) -> str:
        if len(raw_key) <= 10:
            return "******"
        return f"{raw_key[:6]}...{raw_key[-4:]}"

    @classmethod
    def to_response_dto(cls, entity: AiProviderKey) -> AiKeyResponse:
        return AiKeyResponse(
            id=entity.id,
            provider=entity.provider,
            key_name=entity.key_name,
            masked_api_key=cls.mask_key(entity.api_key),
            priority=entity.priority,
            is_active=entity.is_active,
            status=entity.status,
            request_count=entity.request_count,
            last_used_at=entity.last_used_at,
            cooldown_until=entity.cooldown_until,
            created_at=entity.created_at
        )

    @classmethod
    def test_gemini_key(cls, api_key: str) -> bool:
        """Thử gọi 1 request tối thiểu để kiểm tra xem key có hoạt động không"""
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents="ping"
            )
            return True
        except Exception as e:
            logger.error(f"Xác thực API Key thất bại: {e}")
            raise ValueError(f"API Key không hợp lệ hoặc đã bị khóa bởi Google: {str(e)}")

    @classmethod
    def create_key(cls, db: Session, payload: AiKeyCreateRequest) -> AiKeyResponse:
        cls.test_gemini_key(payload.api_key)
        provider_val = payload.provider.upper() if isinstance(payload.provider, str) else payload.provider.value
        new_key = AiProviderKey(
            id=uuid.uuid4(),
            provider=provider_val,
            key_name=payload.key_name,
            api_key=payload.api_key.strip(),
            priority=payload.priority,
            is_active=True,
            status="ACTIVE",
            request_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        return cls.to_response_dto(new_key)

    @classmethod
    def get_all_keys(cls, db: Session) -> List[AiKeyResponse]:
        keys = db.query(AiProviderKey).order_by(AiProviderKey.priority.asc(), AiProviderKey.created_at.desc()).all()
        return [cls.to_response_dto(k) for k in keys]

    @classmethod
    def update_key(cls, db: Session, key_id: uuid.UUID, payload: AiKeyUpdateRequest) -> Optional[AiKeyResponse]:
        key = db.query(AiProviderKey).filter(AiProviderKey.id == key_id).first()
        if not key:
            return None
        if payload.key_name is not None: key.key_name = payload.key_name
        if payload.priority is not None: key.priority = payload.priority
        if payload.is_active is not None: key.is_active = payload.is_active
        key.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(key)
        return cls.to_response_dto(key)

    @classmethod
    def delete_key(cls, db: Session, key_id: uuid.UUID) -> bool:
        key = db.query(AiProviderKey).filter(AiProviderKey.id == key_id).first()
        if not key:
            return False
        db.delete(key)
        db.commit()
        return True

    # ================= LOGIC XOAY VÒNG KEY TỰ ĐỘNG =================
    @classmethod
    def get_client_and_model(cls, db: Optional[Session] = None, default_client: Optional[genai.Client] = None) -> tuple[genai.Client, str]:
        """Lấy nhanh Client và Model đang Active có Priority cao nhất từ DB, hoặc fallback về .env"""
        if db:
            try:
                now = datetime.now(timezone.utc)
                key_item = db.query(AiProviderKey).filter(
                    AiProviderKey.provider == "GEMINI",
                    AiProviderKey.is_active == True,
                    AiProviderKey.status != "INVALID",
                    (AiProviderKey.cooldown_until == None) | (AiProviderKey.cooldown_until <= now)
                ).order_by(AiProviderKey.priority.asc(), AiProviderKey.last_used_at.asc().nullsfirst()).first()

                if key_item and key_item.api_key:
                    return genai.Client(api_key=key_item.api_key), settings.GEMINI_MODEL
            except Exception as e:
                logger.warning(f"Lỗi khi đọc AI Key từ DB, chuyển sang fallback: {e}")

        fallback = default_client or (genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None)
        return fallback, settings.GEMINI_MODEL

    @classmethod
    def execute_with_failover(
        cls,
        db: Optional[Session],
        ai_operation_func,
        default_client: Optional[genai.Client] = None
    ):
        """Tự động chọn key theo độ ưu tiên, nếu dính 429 thì tự động chuyển key tiếp theo"""
        if db:
            try:
                now = datetime.now(timezone.utc)
                available_keys = db.query(AiProviderKey).filter(
                    AiProviderKey.provider == "GEMINI",
                    AiProviderKey.is_active == True,
                    AiProviderKey.status != "INVALID",
                    (AiProviderKey.cooldown_until == None) | (AiProviderKey.cooldown_until <= now)
                ).order_by(AiProviderKey.priority.asc(), AiProviderKey.last_used_at.asc().nullsfirst()).all()

                for key_item in available_keys:
                    try:
                        client = genai.Client(api_key=key_item.api_key)
                        # Dùng model mặc định settings.GEMINI_MODEL từ đầu đến cuối
                        result = ai_operation_func(client, settings.GEMINI_MODEL)

                        # Thành công: Tăng số lượt gọi & cập nhật thời gian
                        key_item.request_count += 1
                        key_item.last_used_at = datetime.now(timezone.utc)
                        key_item.status = "ACTIVE"
                        key_item.cooldown_until = None
                        db.commit()
                        return result

                    except Exception as e:
                        err_msg = str(e).lower()
                        # Bắt lỗi 429 Quota Exceeded / Rate Limit
                        if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                            logger.warning(f"Key '{key_item.key_name}' dính lỗi 429. Tạm khóa 2 phút và chuyển key khác...")
                            key_item.status = "QUOTA_EXCEEDED"
                            key_item.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=2)
                            db.commit()
                            continue # Nhảy sang key tiếp theo trong vòng for
                        else:
                            raise e
            except Exception as db_err:
                logger.warning(f"Lỗi khi truy vấn AI Keys pool: {db_err}")

        # Nếu DB không còn key nào hoặc tất cả đều cạn quota -> Fallback về key trong .env hoặc default_client đã mock
        logger.warning("Toàn bộ Key trong DB đều hết Quota hoặc không có sẵn! Sử dụng key mặc định từ file .env")
        fallback_client = default_client or (genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None)
        return ai_operation_func(fallback_client, settings.GEMINI_MODEL)
