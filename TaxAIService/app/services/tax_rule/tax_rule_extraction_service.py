import json
import logging
import uuid
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from fastapi import HTTPException, status
from app.core.config import settings
from app.enum import TaxRuleStatus
from app.prompts.tax_rule import build_tax_rule_extraction_prompt
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleExtractionError

logger = logging.getLogger(__name__)


class TaxRuleExtractionService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def extract_tax_rules(
        self,
        document_text: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        tax_year: int = 2026,
        rule_set_name: Optional[str] = None,
        source_url: Optional[str] = None,
        legal_doc_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sử dụng Gemini LLM với Structured JSON Output để trích xuất các quy tắc thuế
        (TaxRuleSet và danh sách TaxRule).
        """
        if not document_text and not pdf_bytes:
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)

        default_set_name = rule_set_name or f"Personal Income Tax Rules {tax_year}"

        prompt = build_tax_rule_extraction_prompt(
            tax_year=tax_year,
            default_set_name=default_set_name,
            source_url=source_url,
            legal_doc_name=legal_doc_name,
            document_text=document_text,
        )

        contents = []
        if pdf_bytes:
            pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            contents.append(pdf_part)
        contents.append(prompt)

        raw_text = ""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw_text = (response.text or "").strip()
            # Làm sạch markdown code fences nếu LLM có kèm ```json ... ```
            clean_text = raw_text
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

            try:
                data = json.loads(clean_text)
            except Exception:
                start_idx = clean_text.find("{")
                end_idx = clean_text.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    data = json.loads(clean_text[start_idx:end_idx + 1])
                else:
                    raise
        except Exception as e:
            logger.error(f"Error calling Gemini or parsing JSON: {e}\nRaw output: {raw_text}", exc_info=True)
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)
        
        if not isinstance(data, dict):
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)

        # Kiểm tra verification đối soát năm tính thuế
        verification = data.get("verification")
        warning_msg = None
        if isinstance(verification, dict):
            is_matched = verification.get("isTaxYearMatched")
            extracted_year = verification.get("extractedTaxYear")
            mismatch_reason = verification.get("mismatchReason")

            extracted_year_int = None
            if extracted_year is not None:
                try:
                    extracted_year_int = int(str(extracted_year).strip())
                except (ValueError, TypeError):
                    pass

            # Nếu AI xác định không khớp hoặc năm bóc tách khác với tax_year nhập vào
            if is_matched is False or (extracted_year_int is not None and extracted_year_int != tax_year):
                warning_msg = TaxRuleErrorMessages.tax_year_mismatch(
                    doc_year=extracted_year_int if extracted_year_int is not None else extracted_year,
                    input_year=tax_year,
                    reason=mismatch_reason
                )
                verification["isTaxYearMatched"] = False
                verification["warningMessage"] = warning_msg
            else:
                verification["isTaxYearMatched"] = True
                verification["warningMessage"] = None
        else:
            verification = {
                "inputTaxYear": tax_year,
                "extractedTaxYear": tax_year,
                "isTaxYearMatched": True,
                "mismatchReason": None,
                "warningMessage": None
            }
        data["verification"] = verification
        if warning_msg:
            data["warning"] = warning_msg

        tax_rules = data.get("taxRules", [])
        if not isinstance(tax_rules, list):
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)

        valid_rules = [r for r in tax_rules if isinstance(r, dict)]
        data["taxRules"] = valid_rules

        # Nếu không trích xuất được rules nào:
        # Nếu có cảnh báo lệch năm (hoặc verification xác định không khớp), KHÔNG ném lỗi để hệ thống vẫn lưu Draft kèm cảnh báo cho Admin
        if not valid_rules:
            if not warning_msg and verification.get("isTaxYearMatched") is not False:
                raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)

        for rule in valid_rules:
            if not rule.get("ruleCode"):
                rule["ruleCode"] = f"PIT_RULE_{uuid.uuid4().hex[:8].upper()}"
            if not rule.get("ruleName"):
                rule["ruleName"] = rule["ruleCode"]
            if not rule.get("ruleType"):
                rule["ruleType"] = "DEDUCTION"

        rule_set = data.get("taxRuleSet", {})
        if not isinstance(rule_set, dict):
            rule_set = {}
        if not rule_set.get("name"):
            rule_set["name"] = default_set_name
        rule_set["taxYear"] = tax_year
        rule_set["status"] = TaxRuleStatus.DRAFT.value
        data["taxRuleSet"] = rule_set

        return data


tax_rule_extraction_service = TaxRuleExtractionService()
