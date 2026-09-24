import pytest
from app.schemas.law_changeset.gemini_output import (
    GeminiChangesetOutput,
    GDocument,
    GRelation,
    GOperation,
    GValue,
    GBracket,
    GConditionItem,
    GCitation,
)
from app.schemas.law_changeset.contract import (
    RuleCatalogItem,
    CurrentRuleItem,
    CitationModel,
)
from app.services.law_changeset.mapper import map_gemini_output_to_result
from app.services.law_changeset.post_validator import (
    post_validate_changeset_result,
    normalize_doc_number,
    clean_citation_part,
)


def test_normalize_doc_number():
    assert normalize_doc_number("253/2026/NĐ-CP") == "253/2026/ND-CP"
    assert normalize_doc_number("  109 / 2025 / QH15 ") == "109/2025/QH15"


def test_clean_citation_part():
    assert clean_citation_part("Điều 49") == "49"
    assert clean_citation_part("khoản 2") == "2"
    assert clean_citation_part("Điểm a") == "a"
    assert clean_citation_part("  57 ") == "57"


def test_mapper_schedule_and_condition_items():
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="253/2026/NĐ-CP", documentType="NGHI_DINH"),
        operations=[
            GOperation(
                op="ADD",
                ruleCode="PIT_TAX_SCHEDULE",
                after=GValue(
                    schedule=[
                        GBracket(toAnnual=120000000, rate=0.05),
                        GBracket(toAnnual=None, rate=0.1),
                    ],
                    conditionItems=[
                        GConditionItem(key="domesticFacility", value="true"),
                        GConditionItem(key="incomeCap", value="3000000"),
                    ],
                ),
                citation=GCitation(article="Điều 49", clause="khoản 2", page=34),
                evidence="Quy dinh ve bieu thue",
                confidence=0.95,
            )
        ],
    )

    res = map_gemini_output_to_result(
        output=output,
        total_pages=61,
        pages_read=61,
        mode="PDF",
    )

    assert len(res.operations) == 1
    op = res.operations[0]
    assert op.after.value_json == [
        {"toAnnual": 120000000.0, "rate": 0.05},
        {"toAnnual": None, "rate": 0.1},
    ]
    assert op.after.condition == {
        "domesticFacility": True,
        "incomeCap": 3000000,
    }
    assert op.citation.page == 34


def test_mapper_target_scope():
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="253/2026/NĐ-CP"),
        relations=[
            GRelation(
                type="REPEALS",
                targetDocumentNumber="91/2014/NĐ-CP",
                targetArticle="3",
                citation=GCitation(page=57),
                evidence="Bai bo Dieu 3",
            ),
            GRelation(
                type="REPLACES",
                targetDocumentNumber="65/2013/NĐ-CP",
                citation=GCitation(page=57),
                evidence="Thay the Nghi dinh 65",
            ),
        ],
    )
    res = map_gemini_output_to_result(output, 61, 61, "PDF")
    assert len(res.relations) == 2
    assert res.relations[0].target_scope is not None
    assert res.relations[0].target_scope.article == "3"
    assert res.relations[1].target_scope is None


def test_post_validator_rate_scaling():
    catalog = [
        RuleCatalogItem(
            rule_code="PIT_WITHHOLD_CASUAL_RATE",
            rule_group="WITHHOLDING",
            value_kind="RATE",
            display_name="Thue suat vang lai",
        )
    ]
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="253/2026/NĐ-CP"),
        operations=[
            GOperation(
                op="UPDATE",
                ruleCode="PIT_WITHHOLD_CASUAL_RATE",
                after=GValue(valueNumber=10.0),  # 10% -> 0.1
                citation=GCitation(page=35),
                evidence="Khau tru 10%",
                confidence=0.9,
            )
        ],
    )
    res = map_gemini_output_to_result(output, 61, 61, "PDF")
    validated = post_validate_changeset_result(res, catalog, [])
    assert len(validated.operations) == 1
    assert validated.operations[0].after.value_number == 0.1
    assert any("10.0%" in w for w in validated.warnings)


def test_post_validator_unknown_rule_code_removed():
    catalog = [
        RuleCatalogItem(
            rule_code="PIT_DEDUCTION_MEDICAL",
            rule_group="DEDUCTION",
            value_kind="AMOUNT",
            display_name="Y te",
        )
    ]
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="253/2026/NĐ-CP"),
        operations=[
            GOperation(
                op="ADD",
                ruleCode="UNKNOWN_RULE_CODE",
                newCode=False,
                citation=GCitation(page=10),
                evidence="Evidence text",
                confidence=0.9,
            )
        ],
    )
    res = map_gemini_output_to_result(output, 61, 61, "PDF")
    validated = post_validate_changeset_result(res, catalog, [])
    assert len(validated.operations) == 0
    assert any("UNKNOWN_RULE_CODE" in w for w in validated.warnings)


def test_post_validator_deduplication_keeps_higher_confidence():
    catalog = [
        RuleCatalogItem(
            rule_code="PIT_DEDUCTION_MEDICAL",
            rule_group="DEDUCTION",
            value_kind="AMOUNT",
            display_name="Y te",
        )
    ]
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="253/2026/NĐ-CP"),
        operations=[
            GOperation(
                op="ADD",
                ruleCode="PIT_DEDUCTION_MEDICAL",
                applyFrom="2026-01-01",
                after=GValue(valueNumber=23000000),
                citation=GCitation(page=34),
                evidence="23 trieu",
                confidence=0.7,
            ),
            GOperation(
                op="ADD",
                ruleCode="PIT_DEDUCTION_MEDICAL",
                applyFrom="2026-01-01",
                after=GValue(valueNumber=23000000),
                citation=GCitation(page=34),
                evidence="23 trieu",
                confidence=0.95,
            ),
        ],
    )
    res = map_gemini_output_to_result(output, 61, 61, "PDF")
    validated = post_validate_changeset_result(res, catalog, [])
    assert len(validated.operations) == 1
    assert validated.operations[0].confidence == 0.95


def test_post_validator_end_key_by_apply_to():
    catalog = [
        RuleCatalogItem(
            rule_code="PIT_DEDUCTION_MEDICAL",
            rule_group="DEDUCTION",
            value_kind="AMOUNT",
            display_name="Y te",
        )
    ]
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="253/2026/NĐ-CP"),
        operations=[
            GOperation(
                op="END",
                ruleCode="PIT_DEDUCTION_MEDICAL",
                applyFrom="2020-01-01",
                applyTo="2026-07-01",
                citation=GCitation(page=57),
                evidence="Cham dut",
                confidence=0.8,
            ),
            GOperation(
                op="END",
                ruleCode="PIT_DEDUCTION_MEDICAL",
                applyFrom="2022-01-01",
                applyTo="2026-07-01",
                citation=GCitation(page=57),
                evidence="Cham dut",
                confidence=0.9,
            ),
        ],
    )
    res = map_gemini_output_to_result(output, 61, 61, "PDF")
    validated = post_validate_changeset_result(res, catalog, [])
    assert len(validated.operations) == 1
    assert validated.operations[0].confidence == 0.9


def test_post_validator_removes_identical_to_current_rules():
    catalog = [
        RuleCatalogItem(
            rule_code="PIT_DEDUCTION_PERSONAL",
            rule_group="DEDUCTION",
            value_kind="AMOUNT",
            display_name="Ban than",
        )
    ]
    current_rules = [
        CurrentRuleItem(
            rule_code="PIT_DEDUCTION_PERSONAL",
            value_kind="AMOUNT",
            value_number=15500000,
            unit="VND/month",
            apply_from="2026-01-01",
            apply_to=None,
            citation=CitationModel(document_number="112/VBHN-VPQH"),
        )
    ]
    output = GeminiChangesetOutput(
        document=GDocument(documentNumber="112/VBHN-VPQH"),
        operations=[
            GOperation(
                op="UPDATE",
                ruleCode="PIT_DEDUCTION_PERSONAL",
                applyFrom="2026-01-01",
                after=GValue(valueNumber=15500000, unit="VND/month"),
                citation=GCitation(page=10),
                evidence="Muc giam tru 15.5 trieu",
                confidence=0.95,
            )
        ],
    )
    res = map_gemini_output_to_result(output, 30, 30, "TEXT")
    validated = post_validate_changeset_result(
        res,
        catalog,
        current_rules,
        current_doc_number="112/VBHN-VPQH",
    )
    assert len(validated.operations) == 0
    assert any("giá trị và văn bản căn cứ giống hệt" in w for w in validated.warnings)
