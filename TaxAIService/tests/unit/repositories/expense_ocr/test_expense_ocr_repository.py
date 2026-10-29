import uuid
import pytest
from unittest.mock import MagicMock

from app.models.ai_extraction_models import AiExtraction, AiExtractionValue
from app.schemas.expense_ocr.expense_ocr_schema import ExtractedFieldDetail, BoundingBox
from app.repositories.expense_ocr.expense_ocr_repository import ExpenseOcrRepository


def test_save_extraction_result():
    mock_db = MagicMock()
    repo = ExpenseOcrRepository(db=mock_db)

    doc_id = uuid.uuid4()
    box = BoundingBox(x=10, y=20, w=100, h=40)
    field = ExtractedFieldDetail(
        fieldName="total_amount",
        extractedValue="1,000,000",
        confidenceScore=0.98,
        boundingBox=box
    )
    field_without_box = ExtractedFieldDetail(
        fieldName="seller_name",
        extractedValue="Cửa hàng A",
        confidenceScore=0.95,
        boundingBox=None
    )

    result = repo.save_extraction_result(
        document_id=doc_id,
        overall_confidence=0.96,
        applied_threshold=0.80,
        is_passed_threshold=True,
        raw_payload={"raw": "test"},
        field_details=[field, field_without_box]
    )

    assert result.document_id == doc_id
    assert result.overall_confidence == 0.96
    assert result.applied_threshold == 0.80
    assert result.is_passed_threshold is True
    # db.add được gọi 3 lần (1 cho AiExtraction, 2 cho AiExtractionValue)
    assert mock_db.add.call_count == 3
    mock_db.flush.assert_called_once()
    mock_db.commit.assert_called_once()


def test_get_by_document_id():
    mock_db = MagicMock()
    repo = ExpenseOcrRepository(db=mock_db)

    doc_id = uuid.uuid4()
    dummy_extraction = AiExtraction(document_id=doc_id, overall_confidence=0.95)
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = dummy_extraction

    found = repo.get_by_document_id(doc_id)
    assert found == dummy_extraction
