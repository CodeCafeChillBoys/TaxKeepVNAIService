import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.tax_rule.tax_rule_extraction_service import TaxRuleExtractionService
from app.errors.tax_rule_errors import TaxRuleExtractionError, TaxRuleErrorMessages


def test_extract_tax_rules_no_input():
    service = TaxRuleExtractionService()
    with pytest.raises(TaxRuleExtractionError) as exc_info:
        service.extract_tax_rules(document_text=None, pdf_bytes=None)
    assert exc_info.value.detail == TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED


def test_extract_tax_rules_applies_after_first_effective_year():
    service = TaxRuleExtractionService()

    fake_json = {
        "taxRuleSet": {"name": "Luật 2020", "effectiveFrom": "2020-01-01"},
        "taxRules": [{"ruleCode": "PIT_01", "ruleName": "Giảm trừ", "ruleType": "DEDUCTION"}],
        "verification": {"isTaxYearMatched": True, "extractedTaxYear": 2020}
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = service.extract_tax_rules(document_text="Luật thuế có hiệu lực từ 2020", tax_year=2025)

    assert result["taxRuleSet"]["name"] == "Luật 2020"
    assert result["taxRuleSet"]["taxYear"] == 2025
    assert result["taxRuleSet"]["status"] == "Draft"
    assert len(result["taxRules"]) == 1
    assert result["verification"]["isTaxYearMatched"] is True
    assert "warning" not in result


def test_extract_tax_rules_with_pdf_bytes_and_markdown_fence():
    service = TaxRuleExtractionService()

    fake_json = {
        "taxRuleSet": {},
        "taxRules": [{"ruleCode": ""}],  # Thiếu ruleCode, ruleName, ruleType để test gán mặc định
        "verification": None  # verification là None để test gán mặc định
    }

    # Bọc chuỗi JSON trong ```json ... ```
    raw_markdown = f"```json\n{json.dumps(fake_json)}\n```"

    mock_resp = MagicMock()
    mock_resp.text = raw_markdown

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = service.extract_tax_rules(pdf_bytes=b"pdf_binary", tax_year=2026)

    assert "PIT_RULE_" in result["taxRules"][0]["ruleCode"]
    assert result["taxRules"][0]["ruleType"] == "DEDUCTION"
    assert result["taxRuleSet"]["taxYear"] == 2026
    assert result["verification"]["isTaxYearMatched"] is None
    assert "Chưa xác định" in result["warning"]


def test_extract_tax_rules_tax_year_mismatch_warning():
    """Cảnh báo khi văn bản đã hết áp dụng cho kỳ tính thuế được chọn."""
    service = TaxRuleExtractionService()

    fake_json = {
        "taxRuleSet": {"name": "Luật 2025"},
        "taxRules": [{"ruleCode": "PIT_01"}],
        "verification": {
            "isTaxYearMatched": False,
            "extractedTaxYear": 2025,
            "mismatchReason": "Văn bản chỉ áp dụng cho kỳ tính thuế 2025"
        }
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = service.extract_tax_rules(document_text="Văn bản 2025", tax_year=2026)

    assert "warning" in result
    assert result["verification"]["isTaxYearMatched"] is False
    assert result["verification"]["warningMessage"] is not None


def test_extract_tax_rules_json_parse_fallback_and_error():
    service = TaxRuleExtractionService()

    # 1. Fallback tìm { ... } thành công
    valid_obj = {"taxRuleSet": {}, "taxRules": [{"ruleCode": "R1"}]}
    messy_text = f"Lời chào đầu: {json.dumps(valid_obj)} Lời kết thúc"
    mock_resp = MagicMock()
    mock_resp.text = messy_text

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        res = service.extract_tax_rules(document_text="test", tax_year=2026)
        assert len(res["taxRules"]) == 1

    # 2. Hoàn toàn không parse được JSON -> ném TaxRuleExtractionError
    mock_resp.text = "Không có json nào ở đây cả"
    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        with pytest.raises(TaxRuleExtractionError):
            service.extract_tax_rules(document_text="test", tax_year=2026)


def test_extract_tax_rules_with_dynamic_system_configs():
    """Kiểm tra khi có cấu hình động ALLOWED_DOCUMENT_TYPES và ALLOWED_DEPENDENT_TYPES từ DB."""
    mock_db = MagicMock()
    service = TaxRuleExtractionService(db=mock_db)

    fake_json = {
        "taxRuleSet": {"name": "Luật 2026"},
        "taxRules": [{"ruleCode": "PIT_01", "ruleName": "Giảm trừ", "ruleType": "DEDUCTION"}],
        "verification": {"isTaxYearMatched": True, "extractedTaxYear": 2026}
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch("app.repositories.system_config.system_config_repository.SystemConfigRepository.get_list_value") as mock_get_list:
        def side_effect(key, default=None):
            if key == "ALLOWED_DOCUMENT_TYPES":
                return ["CUSTOM_VNEID_LEVEL_2", "CUSTOM_CERT"]
            if key == "ALLOWED_DEPENDENT_TYPES":
                return ["CUSTOM_CHILD_GROUP"]
            return default
        mock_get_list.side_effect = side_effect

        with patch.object(service.client.models, "generate_content", return_value=mock_resp) as mock_generate:
            result = service.extract_tax_rules(document_text="Nội dung luật thuế", tax_year=2026)
            assert result["taxRuleSet"]["name"] == "Luật 2026"
            # Kiểm tra prompt gửi tới Gemini có chứa mã custom từ system_configs
            call_args = mock_generate.call_args
            contents = call_args[1]["contents"]
            prompt_str = contents[-1]
            assert "CUSTOM_VNEID_LEVEL_2" in prompt_str
            assert "CUSTOM_CHILD_GROUP" in prompt_str


def test_extract_tax_rules_no_rules_without_warning_raises_error():
    """Nếu không trích xuất được rules nào và không có cảnh báo lệch năm -> ném lỗi."""
    service = TaxRuleExtractionService()
    fake_json = {
        "taxRuleSet": {},
        "taxRules": [],
        "verification": {"isTaxYearMatched": True}
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        with pytest.raises(TaxRuleExtractionError):
            service.extract_tax_rules(document_text="test", tax_year=2026)


def test_extract_tax_rules_with_dynamic_system_configs():
    """Kiểm tra khi có cấu hình động ALLOWED_DOCUMENT_TYPES và ALLOWED_DEPENDENT_TYPES từ DB."""
    mock_db = MagicMock()
    service = TaxRuleExtractionService(db=mock_db)

    fake_json = {
        "taxRuleSet": {"name": "Luật 2026"},
        "taxRules": [{"ruleCode": "PIT_01", "ruleName": "Giảm trừ", "ruleType": "DEDUCTION"}],
        "verification": {"isTaxYearMatched": True, "extractedTaxYear": 2026}
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch("app.repositories.system_config.system_config_repository.SystemConfigRepository.get_list_value") as mock_get_list:
        def side_effect(key, default=None):
            if key == "ALLOWED_DOCUMENT_TYPES":
                return ["CUSTOM_VNEID_LEVEL_2", "CUSTOM_CERT"]
            if key == "ALLOWED_DEPENDENT_TYPES":
                return ["CUSTOM_CHILD_GROUP"]
            return default
        mock_get_list.side_effect = side_effect

        with patch.object(service.client.models, "generate_content", return_value=mock_resp) as mock_generate:
            result = service.extract_tax_rules(document_text="Nội dung luật thuế", tax_year=2026)
            assert result["taxRuleSet"]["name"] == "Luật 2026"
            # Kiểm tra prompt gửi tới Gemini có chứa mã custom từ system_configs
            call_args = mock_generate.call_args
            contents = call_args[1]["contents"]
            prompt_str = contents[-1]
            assert "CUSTOM_VNEID_LEVEL_2" in prompt_str
            assert "CUSTOM_CHILD_GROUP" in prompt_str
