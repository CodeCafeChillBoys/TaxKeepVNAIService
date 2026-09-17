import uuid
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from app.models.ai_extraction_models import AiExtraction, AiExtractionValue
from app.schemas.expense_ocr.expense_ocr_schema import ExtractedFieldDetail


class ExpenseOcrRepository:
    """
    Repository phụ trách lưu trữ và truy vấn kết quả bóc tách chứng từ chi phí
    vào 2 bảng: AI_EXTRACTIONS và AI_EXTRACTIONS_Value.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_extraction_result(
        self,
        document_id: Union[uuid.UUID, str],
        overall_confidence: float,
        applied_threshold: float,
        is_passed_threshold: bool,
        raw_payload: Dict[str, Any],
        field_details: List[ExtractedFieldDetail]
    ) -> AiExtraction:
        """
        Lưu kết quả bóc tách hoàn chỉnh:
        1. Tạo record bảng cha AI_EXTRACTIONS
        2. Tạo các record bảng con AI_EXTRACTIONS_Value cho từng trường
        """
        doc_uuid = uuid.UUID(str(document_id))

        # 1. Lưu bảng cha: AI_EXTRACTIONS
        extraction_record = AiExtraction(
            document_id=doc_uuid,
            overall_confidence=overall_confidence,
            applied_threshold=applied_threshold,
            is_passed_threshold=is_passed_threshold,
            raw_payload=raw_payload
        )

        self.db.add(extraction_record)
        self.db.flush()  # Lấy ID của extraction_record

        # 2. Lưu bảng con: AI_EXTRACTIONS_Value (từng trường + bounding_box)
        for field in field_details:
            bbox_dict = field.boundingBox.model_dump() if field.boundingBox else None
            val_record = AiExtractionValue(
                extraction_id=extraction_record.id,
                field_name=field.fieldName,
                extracted_value=field.extractedValue,
                user_corrected_value=None,  # Để trống chờ User Review
                confidence_score=field.confidenceScore,
                bounding_box=bbox_dict
            )
            self.db.add(val_record)

        self.db.commit()
        return extraction_record

    def get_by_document_id(self, document_id: Union[uuid.UUID, str]) -> Optional[AiExtraction]:
        """Lấy lịch sử bóc tách mới nhất theo document_id"""
        doc_uuid = uuid.UUID(str(document_id))
        return (
            self.db.query(AiExtraction)
            .filter(AiExtraction.document_id == doc_uuid)
            .order_by(AiExtraction.created_at.desc())
            .first()
        )
