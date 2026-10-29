import json
import uuid
import pytest

from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.enum import TaxRuleStatus
from app.mappers.tax_rule.tax_rule_mapper import (
    parse_condition,
    format_tax_rule_data,
    build_tax_rule_models
)


# ==============================================================================
# 1. Test parse_condition()
# ==============================================================================
def test_parse_condition_none_or_empty():
    assert parse_condition(None) is None
    assert parse_condition("") is None


def test_parse_condition_valid_json_dict():
    result = parse_condition('{"min": 10, "max": 20}')
    assert isinstance(result, dict)
    assert result["min"] == 10
    assert result["max"] == 20


def test_parse_condition_valid_json_list():
    result = parse_condition('["doc1", "doc2"]')
    assert isinstance(result, list)
    assert len(result) == 2


def test_parse_condition_invalid_json():
    # Bắt đầu bằng { nhưng không đúng cú pháp JSON
    raw = "{invalid json content"
    assert parse_condition(raw) == raw


def test_parse_condition_plain_string_or_other_types():
    assert parse_condition("plaintext condition") == "plaintext condition"
    assert parse_condition(12345) == 12345


# ==============================================================================
# 2. Test format_tax_rule_data()
# ==============================================================================
def test_format_tax_rule_data():
    rule_set_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    rule_id = uuid.uuid4()
    dep_id = uuid.uuid4()

    rs = TaxRuleSet(
        rule_set_id=rule_set_id,
        admin_id=admin_id,
        name="Luật Thuế 2026",
        tax_year=2026,
        status="DRAFT"
    )

    rule = TaxRule(
        rule_id=rule_id,
        rule_code="PIT_DEDUCTION_SELF",
        rule_name="Giảm trừ bản thân",
        rule_type="DEDUCTION",
        condition='{"threshold": 11000000}',
        value=11000000.0,
        unit="VND",
        status="DRAFT"
    )

    dep = DependentRule(
        id=dep_id,
        rule_id=rule_id,
        dependent_type="CHILD",
        name="Con dưới 18 tuổi",
        max_age=18,
        conditions='["Chưa đi làm"]',
        required_documents=["Giấy khai sinh"],
        status="DRAFT"
    )

    formatted = format_tax_rule_data(rs, [rule], [dep])

    assert "taxRuleSet" in formatted
    assert formatted["taxRuleSet"]["ruleSetId"] == rule_set_id
    assert formatted["taxRuleSet"]["name"] == "Luật Thuế 2026"

    assert len(formatted["taxRules"]) == 1
    assert formatted["taxRules"][0]["ruleCode"] == "PIT_DEDUCTION_SELF"
    assert formatted["taxRules"][0]["condition"] == {"threshold": 11000000}

    assert len(formatted["dependentRules"]) == 1
    assert formatted["dependentRules"][0]["dependentType"] == "CHILD"
    assert formatted["dependentRules"][0]["maxAge"] == 18
    assert formatted["dependentRules"][0]["conditions"] == ["Chưa đi làm"]


# ==============================================================================
# 3. Test build_tax_rule_models()
# ==============================================================================
def test_build_tax_rule_models_basic():
    extracted_data = {
        "taxRuleSet": {
            "name": "Luật Thuế TNCN 2026",
            "effectiveFrom": "2026-01-01",
            "effectiveTo": "2026-12-31"
        },
        "taxRules": [
            {
                "ruleCode": "PIT_BRACKET_01",
                "ruleName": "Bậc 1",
                "ruleType": "TAX_BRACKET",
                "value": "5.0",
                "condition": {"from": 0, "to": 5000000},
                "article": 1,
                "clause": 2,
                "point": "a"
            }
        ]
    }

    rs, rules, deps = build_tax_rule_models(
        extracted_data=extracted_data,
        tax_year=2026,
        filename="luat_2026.pdf",
        source_url="https://chinhphu.vn/luat.pdf"
    )

    assert rs.name == "Luật Thuế TNCN 2026"
    assert rs.tax_year == 2026
    assert rs.status == TaxRuleStatus.DRAFT.value

    assert len(rules) == 1
    assert rules[0].rule_code == "PIT_BRACKET_01"
    assert rules[0].value == 5.0
    assert rules[0].article == "1"
    assert rules[0].clause == "2"
    assert rules[0].point == "a"
    assert rules[0].source_url == "https://chinhphu.vn/luat.pdf"
    assert len(deps) == 0


def test_build_tax_rule_models_with_eligibility_dict():
    """Trường hợp condition là dict và có chứa eligibility của người phụ thuộc."""
    eligibility_data = {
        "eligibility": [
            {
                "type": "CHILD",
                "name": "Con nhỏ",
                "maxAge": 18,
                "maxMonthlyIncome": 1000000,
                "isStudying": True,
                "isDisabled": False,
                "conditions": ["Dưới 18 tuổi"],
                "requiredDocuments": ["Khai sinh"]
            }
        ]
    }

    extracted_data = {
        "taxRuleSet": {"name": "Luật 2026"},
        "taxRules": [
            {
                "ruleCode": "DEP_RULE_01",
                "ruleName": "Người phụ thuộc",
                "ruleType": "DEPENDENT",
                "condition": eligibility_data
            }
        ]
    }

    rs, rules, deps = build_tax_rule_models(
        extracted_data=extracted_data,
        tax_year=2026,
        filename="dep.pdf"
    )

    assert len(rules) == 1
    assert len(deps) == 1
    dep = deps[0]
    assert dep.dependent_type == "CHILD"
    assert dep.name == "Con nhỏ"
    assert dep.max_age == 18
    assert dep.max_monthly_income == 1000000.0
    assert dep.is_studying is True
    assert dep.is_disabled is False
    assert dep.required_documents == ["Khai sinh"]


def test_build_tax_rule_models_with_eligibility_string_slice():
    """Trường hợp condition là chuỗi có nhúng JSON eligibility dạng string."""
    raw_str = 'Chú thích: {"eligibility": [{"type": "PARENT", "name": "Bố mẹ", "maxAge": 60}]}'
    extracted_data = {
        "taxRuleSet": {"name": "Luật 2026"},
        "taxRules": [
            {
                "ruleCode": "DEP_RULE_02",
                "ruleName": "Bố mẹ già",
                "ruleType": "DEPENDENT",
                "condition": raw_str
            }
        ]
    }

    rs, rules, deps = build_tax_rule_models(
        extracted_data=extracted_data,
        tax_year=2026,
        filename="dep.pdf"
    )

    assert len(deps) == 1
    assert deps[0].dependent_type == "PARENT"
    assert deps[0].max_age == 60


def test_build_tax_rule_models_with_invalid_string_slice():
    """Trường hợp condition là chuỗi có { và } nhưng nội dung không phải JSON hợp lệ."""
    raw_str = "Prefix {invalid json inside} Suffix"
    extracted_data = {
        "taxRuleSet": {"name": "Luật 2026"},
        "taxRules": [
            {
                "ruleCode": "RULE_03",
                "ruleName": "Luật test",
                "ruleType": "OTHER",
                "condition": raw_str
            }
        ]
    }

    rs, rules, deps = build_tax_rule_models(
        extracted_data=extracted_data,
        tax_year=2026,
        filename="test.pdf"
    )

    assert len(rules) == 1
    assert len(deps) == 0

