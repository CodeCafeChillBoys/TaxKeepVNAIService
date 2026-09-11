import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from fastapi import HTTPException, status
from app.core.config import settings
from app.prompts.tax_rule_prompts import build_tax_rule_extraction_prompt
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleExtractionError


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

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
        except Exception:
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)
        
        if not isinstance(data, dict) or "taxRules" not in data or not data["taxRules"]:
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)

        tax_rules = data.get("taxRules", [])
        if not isinstance(tax_rules, list) or len(tax_rules) == 0:
            raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED)

        for rule in tax_rules:
            if not rule.get("ruleCode") or not rule.get("ruleName") or not rule.get("ruleType"):
                raise TaxRuleExtractionError(detail=TaxRuleErrorMessages.REQUIRED_FIELDS_MISSING)

        rule_set = data.get("taxRuleSet", {})
        if not rule_set.get("name"):
            rule_set["name"] = default_set_name
        rule_set["taxYear"] = tax_year
        rule_set["status"] = "Draft"
        data["taxRuleSet"] = rule_set

        return data


tax_rule_extraction_service = TaxRuleExtractionService()
