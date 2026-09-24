from __future__ import annotations
import asyncio
import io
import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from google import genai
from google.genai import types

from app.core.config import settings
from app.errors.law_changeset_errors import (
    LawChangesetFileDownloadError,
    LawChangesetModelError,
    LawChangesetSchemaInvalidError,
)
from app.prompts.law_changeset.law_changeset_prompt import build_law_changeset_prompt
from app.schemas.law_changeset.contract import (
    CurrentRuleItem,
    LawChangesetExtractRequest,
    LawChangesetResult,
    RuleCatalogItem,
)
from app.schemas.law_changeset.gemini_output import GeminiChangesetOutput
from app.services.law_changeset.mapper import map_gemini_output_to_result
from app.services.law_changeset.pdf_preparer import (
    LawPdfPreparer,
    PreparedChunk,
    PreparedPdfResult,
    pdf_preparer,
)
from app.services.law_changeset.post_validator import post_validate_changeset_result

logger = logging.getLogger(__name__)


class LawChangesetService:
    def __init__(self, preparer: Optional[LawPdfPreparer] = None):
        self.preparer = preparer or pdf_preparer
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.LAW_CHANGESET_MODEL or settings.GEMINI_MODEL

    async def download_file(self, file_url: str) -> bytes:
        logger.info(f"Downloading law document from: {file_url}")
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(file_url)
                if resp.status_code != 200:
                    raise LawChangesetFileDownloadError(
                        f"Tải tệp thất bại, máy chủ trả về mã HTTP {resp.status_code}."
                    )
                return resp.content
        except LawChangesetFileDownloadError:
            raise
        except Exception as e:
            logger.error(f"Error downloading file from {file_url}: {e}")
            raise LawChangesetFileDownloadError(f"Lỗi khi kết nối tải tệp: {e}")

    async def _call_gemini_with_retry(
        self,
        contents: List[Any],
        schema_retry: bool = False,
    ) -> GeminiChangesetOutput:
        """
        Gọi Gemini với cơ chế thử lại theo đặc tả §10:
        - Gemini lỗi hoặc timeout: thử lại 2 lần (cách 2s, 5s).
        - Schema không khớp: thử lại 1 lần (kèm lời nhắc chỉ trả đúng JSON schema).
        """
        delays = [2, 5]
        attempt = 0
        last_error = None

        while attempt <= 2:
            try:
                coro = self.client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeminiChangesetOutput,
                        temperature=0,
                    ),
                )
                response = await asyncio.wait_for(
                    coro,
                    timeout=float(settings.LAW_CHANGESET_CALL_TIMEOUT_SECONDS),
                )

                # Đọc kết quả
                parsed = response.parsed
                if parsed and isinstance(parsed, GeminiChangesetOutput):
                    return parsed

                # Fallback parse từ response.text nếu parsed là None
                raw_text = response.text or ""
                try:
                    return GeminiChangesetOutput.model_validate_json(raw_text)
                except Exception as schema_err:
                    if not schema_retry:
                        logger.warning(f"Schema mismatch, retrying with schema reminder: {schema_err}")
                        reminder_prompt = "\nLƯU Ý QUAN TRỌNG: Chỉ trả về JSON thuần đúng cấu trúc schema quy định."
                        retry_contents = [*contents, reminder_prompt]
                        return await self._call_gemini_with_retry(retry_contents, schema_retry=True)
                    raise LawChangesetSchemaInvalidError(f"Phản hồi từ Gemini không khớp schema: {schema_err}")

            except (LawChangesetSchemaInvalidError, asyncio.TimeoutError) as te:
                last_error = te
            except Exception as e:
                last_error = e

            if attempt < 2:
                delay = delays[attempt]
                logger.warning(
                    f"Gemini call failed (attempt {attempt + 1}/3): {last_error}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            attempt += 1

        logger.error(f"Gemini call failed after retries: {last_error}")
        if isinstance(last_error, asyncio.TimeoutError):
            raise LawChangesetModelError("Quá thời gian xử lý khi gọi mô hình AI.")
        raise LawChangesetModelError(f"Lỗi khi gọi mô hình Gemini: {last_error}")

    async def _process_chunk(
        self,
        chunk: PreparedChunk,
        prompt_text: str,
    ) -> GeminiChangesetOutput:
        document_parts: List[Any] = []

        if chunk.mode == "TEXT":
            document_parts.append(chunk.text_content)
        else:
            inline_limit = settings.LAW_CHANGESET_INLINE_MAX_MB * 1024 * 1024
            if chunk.pdf_bytes and len(chunk.pdf_bytes) <= inline_limit:
                document_parts.append(
                    types.Part.from_bytes(
                        data=chunk.pdf_bytes,
                        mime_type="application/pdf",
                    )
                )
            elif chunk.pdf_bytes:
                # File scan lớn > 18MB, upload qua Files API
                logger.info(f"Chunk {chunk.chunk_index} > 18MB, uploading via Files API...")
                uploaded_file = await self.client.aio.files.upload(
                    file=io.BytesIO(chunk.pdf_bytes),
                    mime_type="application/pdf",
                )
                document_parts.append(uploaded_file)

        contents = [*document_parts, prompt_text]
        return await self._call_gemini_with_retry(contents)

    async def extract_law_changeset(
        self,
        file_bytes: bytes,
        file_name: str,
        current_rules: List[CurrentRuleItem],
        rule_catalog: List[RuleCatalogItem],
        known_documents: List[Any],
        document_number_hint: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> LawChangesetResult:
        """
        Luồng nghiệp vụ đầy đủ:
        1. Chuẩn bị PDF (nhận diện mode TEXT/PDF scan, chia cụm nếu quá ngưỡng).
        2. Tạo prompt bám sát quy tắc nghiệp vụ §6.
        3. Gọi Gemini async cho từng chunk.
        4. Ánh xạ và gộp kết quả từ các chunk.
        5. Hậu kiểm bằng post_validator.
        """
        # 1. Chuẩn bị PDF
        prep_result = self.preparer.prepare(file_bytes, file_name)

        # 2. Xây dựng prompt
        prompt_text = build_law_changeset_prompt(
            current_rules=[r.model_dump(by_alias=True) for r in current_rules],
            rule_catalog=[c.model_dump(by_alias=True) for c in rule_catalog],
            known_documents=[d.model_dump(by_alias=True) if hasattr(d, "model_dump") else d for d in known_documents],
            document_number_hint=document_number_hint,
            source_url=source_url,
        )

        # 3. Xử lý các chunk
        if len(prep_result.chunks) == 1:
            chunk = prep_result.chunks[0]
            gemini_output = await self._process_chunk(chunk, prompt_text)
            mapped = map_gemini_output_to_result(
                output=gemini_output,
                total_pages=prep_result.total_pages,
                pages_read=prep_result.pages_read,
                mode=prep_result.mode,
                chunks_count=1,
                page_offset=0,
            )
            return post_validate_changeset_result(
                result=mapped,
                rule_catalog=rule_catalog,
                current_rules=current_rules,
                current_doc_number=mapped.document.document_number or document_number_hint,
            )

        # Nhiều chunks: gọi song song hoặc tuần tự
        chunk_outputs: List[tuple[PreparedChunk, GeminiChangesetOutput]] = []
        for ch in prep_result.chunks:
            out = await self._process_chunk(ch, prompt_text)
            chunk_outputs.append((ch, out))

        # 4. Gộp kết quả theo quy định §8
        # - document lấy từ chunk đầu tiên (start_page == 1)
        # - relations và căn cứ ngày áp dụng lấy từ chunk 5 trang cuối
        first_chunk_out = next(out for ch, out in chunk_outputs if ch.start_page == 1)
        last_chunk_tuple = next((ch, out) for ch, out in chunk_outputs if ch.is_last_5_pages)
        last_chunk, last_chunk_out = last_chunk_tuple

        # Căn cứ ngày áp dụng chung từ điều khoản thi hành ở chunk cuối
        fallback_apply_from = last_chunk_out.document.effectiveDate
        fallback_apply_basis = None
        if last_chunk_out.operations:
            fallback_apply_basis = last_chunk_out.operations[-1].applyBasis

        all_mapped_results: List[LawChangesetResult] = []
        for ch, out in chunk_outputs:
            page_offset = ch.start_page - 1
            res = map_gemini_output_to_result(
                output=out,
                total_pages=prep_result.total_pages,
                pages_read=prep_result.pages_read,
                mode=prep_result.mode,
                chunks_count=len(prep_result.chunks),
                page_offset=page_offset,
            )
            all_mapped_results.append(res)

        # Document từ chunk 1
        merged_document = all_mapped_results[0].document
        if not merged_document.effective_date and last_chunk_out.document.effectiveDate:
            merged_document.effective_date = last_chunk_out.document.effectiveDate

        # Relations: lấy từ chunk cuối và bỏ trùng
        merged_relations = list(all_mapped_results[-1].relations)

        # Operations: gộp và bù đắp applyFrom bị null ở các cụm giữa
        merged_operations = []
        for idx, res in enumerate(all_mapped_results):
            for op in res.operations:
                if not op.apply_from and fallback_apply_from:
                    op.apply_from = fallback_apply_from
                    if not op.apply_basis and fallback_apply_basis:
                        op.apply_basis = all_mapped_results[-1].operations[0].apply_basis
                merged_operations.append(op)

        all_references = []
        for res in all_mapped_results:
            all_references.extend(res.references)

        all_warnings = []
        for res in all_mapped_results:
            all_warnings.extend(res.warnings)

        combined_result = LawChangesetResult(
            coverage=all_mapped_results[0].coverage,
            document=merged_document,
            relations=merged_relations,
            operations=merged_operations,
            references=all_references,
            warnings=all_warnings,
        )

        return post_validate_changeset_result(
            result=combined_result,
            rule_catalog=rule_catalog,
            current_rules=current_rules,
            current_doc_number=merged_document.document_number or document_number_hint,
        )


law_changeset_service = LawChangesetService()
