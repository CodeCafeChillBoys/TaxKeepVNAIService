import json
import pytest
from unittest.mock import MagicMock, patch

from app.schemas.ocr import (
    ConfidenceScores,
    OcrExtractionResponse,
    ExtractedDependentData
)
from app.services.ocr.dependent_ocr_service import (
    evaluate_dynamic_threshold,
    DependentOcrService
)


# ==============================================================================
# 1. Test evaluate_dynamic_threshold()
# ==============================================================================
def test_evaluate_dynamic_threshold_pass():
    scores = ConfidenceScores(
        citizenId=0.95,
        fullName=0.90,
        birthDate=0.92
    )
    result = evaluate_dynamic_threshold(confidence_scores=scores, applied_threshold=0.85)

    assert result.is_passed_threshold is True
    assert result.overall_confidence == 0.92
    assert result.warning_message is None
    assert len(result.low_confidence_fields) == 0


def test_evaluate_dynamic_threshold_fail_with_warning():
    scores = ConfidenceScores(
        citizenId=0.95,
        fullName=0.60,
        birthDate=0.70
    )
    result = evaluate_dynamic_threshold(confidence_scores=scores, applied_threshold=0.80)

    assert result.is_passed_threshold is False
    assert result.overall_confidence == 0.75
    assert result.warning_message is not None
    assert "fullName" in result.low_confidence_fields
    assert "birthDate" in result.low_confidence_fields


def test_evaluate_dynamic_threshold_empty_scores():
    scores = ConfidenceScores()
    # Loại bỏ các trường để dict rỗng
    result = evaluate_dynamic_threshold(confidence_scores=scores, applied_threshold=0.80)
    assert result.overall_confidence == 0.0


# ==============================================================================
# 2. Test DependentOcrService.extract_document()
# ==============================================================================
def test_extract_document_success():
    mock_repo = MagicMock()
    mock_repo.get_system_threshold.return_value = 0.85

    service = DependentOcrService(repo=mock_repo)

    fake_response_data = {
        "success": True,
        "statusCode": 200,
        "message": "Success",
        "data": {
            "fullName": "NGUYỄN VĂN A",
            "citizenId": "012345678901",
            "confidenceScores": {
                "fullName": 0.95,
                "citizenId": 0.90
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_response_data)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        res = service.extract_document(
            files=[(b"fake_image_bytes", "image/jpeg")],
            target_group="CHILD"
        )

    assert res.success is True
    assert res.status_code == 200
    assert res.data.full_name == "NGUYỄN VĂN A"
    assert res.data.threshold_validation.is_passed_threshold is True
    mock_repo.get_system_threshold.assert_called_once()


def test_extract_document_low_confidence_warning():
    service = DependentOcrService(repo=None)

    fake_response_data = {
        "success": True,
        "statusCode": 200,
        "message": "Success",
        "data": {
            "fullName": "NGUYỄN VĂN B",
            "confidenceScores": {
                "fullName": 0.50
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_response_data)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        res = service.extract_document(
            files=[(b"bytes", "image/png")],
            applied_threshold=0.80
        )

    assert res.success is True
    assert res.data.threshold_validation.is_passed_threshold is False
    assert "Độ tin cậy trích xuất" in res.message


def test_extract_document_exception_handling():
    service = DependentOcrService(repo=None)

    with patch.object(service.client.models, "generate_content", side_effect=RuntimeError("AI Timeout")):
        res = service.extract_document(files=[(b"bytes", "image/png")])

    assert res.success is False
    assert res.status_code == 500
    assert "AI Timeout" in res.errors
