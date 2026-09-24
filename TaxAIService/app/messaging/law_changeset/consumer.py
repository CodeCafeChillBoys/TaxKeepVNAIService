from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Optional
import aio_pika

from app.core.config import settings
from app.errors.law_changeset_errors import (
    LawChangesetBadRequestError,
    LawChangesetFileDownloadError,
    LawChangesetModelError,
    LawChangesetPdfUnreadableError,
    LawChangesetSchemaInvalidError,
    LawChangesetTooLargeError,
)
from app.messaging.law_changeset.producer import publish_law_changeset_response
from app.schemas.law_changeset.contract import (
    LawChangesetExtractRequest,
    LawChangesetExtractResponse,
    MinimalRequestHeader,
)
from app.services.law_changeset.law_changeset_service import law_changeset_service

logger = logging.getLogger(__name__)


async def handle_law_changeset_message(message: aio_pika.IncomingMessage) -> None:
    """
    Xử lý message từ hàng đợi law.changeset.request.queue theo đặc tả §10:
    - Luôn trả đúng một message response cho mỗi request đọc được taskId và changesetId.
    - Thiếu taskId hoặc changesetId: chỉ ghi log và ack.
    - Bọc toàn bộ trong deadline LAW_CHANGESET_TOTAL_DEADLINE_SECONDS.
    - Xử lý mã lỗi tương ứng theo đặc tả.
    """
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        logger.info(f"Received LawChangeset request: {raw_body[:200]}...")

        # 1. Parse sơ bộ để lấy taskId, changesetId, baseRevision
        try:
            body_dict = json.loads(raw_body)
            header = MinimalRequestHeader.model_validate(body_dict)
        except Exception as json_err:
            logger.error(f"Cannot parse message body or header: {json_err}. Message discarded.")
            return

        if not header.task_id or not header.changeset_id:
            logger.error(
                f"Missing taskId ({header.task_id}) or changesetId ({header.changeset_id}) "
                f"in request header. Cannot send response. Message discarded."
            )
            return


        task_id = header.task_id
        changeset_id = header.changeset_id
        base_revision = header.base_revision if header.base_revision is not None else 0

        # Helper tạo response thất bại
        def _make_failed_response(error_code: str, error_message: str) -> LawChangesetExtractResponse:
            return LawChangesetExtractResponse(
                schema_version=1,
                task_id=task_id,
                changeset_id=changeset_id,
                base_revision=base_revision,
                status="FAILED",
                error_code=error_code,  # type: ignore
                error_message=error_message,
                model=settings.LAW_CHANGESET_MODEL or settings.GEMINI_MODEL,
                processed_at=datetime.now(timezone.utc).isoformat(),
                result=None,
            )

        # 2. Kiểm tra schema version và các trường bắt buộc
        request_obj: Optional[LawChangesetExtractRequest] = None
        if header.schema_version != 1:
            err_resp = _make_failed_response(
                "E-AI_BAD_REQUEST",
                f"schemaVersion ({header.schema_version}) không được hỗ trợ. Chỉ hỗ trợ schemaVersion=1.",
            )
            await publish_law_changeset_response(err_resp)
            return

        try:
            request_obj = LawChangesetExtractRequest.model_validate(body_dict)
        except Exception as val_err:
            logger.warning(f"Request schema validation failed: {val_err}")
            err_resp = _make_failed_response(
                "E-AI_BAD_REQUEST",
                f"Dữ liệu request không hợp lệ: {val_err}",
            )
            await publish_law_changeset_response(err_resp)
            return

        # 3. Thực thi nghiệp vụ bọc trong deadline LAW_CHANGESET_TOTAL_DEADLINE_SECONDS
        total_deadline = float(settings.LAW_CHANGESET_TOTAL_DEADLINE_SECONDS)
        try:
            async def _execute_task():
                # a. Tải file tài liệu
                file_bytes = await law_changeset_service.download_file(request_obj.file_url)

                # b. Gọi service xử lý
                return await law_changeset_service.extract_law_changeset(
                    file_bytes=file_bytes,
                    file_name=request_obj.file_name,
                    current_rules=request_obj.current_rules,
                    rule_catalog=request_obj.rule_catalog,
                    known_documents=request_obj.known_documents,
                    document_number_hint=request_obj.document_number_hint,
                    source_url=request_obj.source_url,
                )

            exec_coro = _execute_task()
            try:
                changeset_result = await asyncio.wait_for(exec_coro, timeout=total_deadline)
            except asyncio.TimeoutError:
                try:
                    exec_coro.close()
                except Exception:
                    pass
                raise

            # Thành công
            success_resp = LawChangesetExtractResponse(
                schema_version=1,
                task_id=task_id,
                changeset_id=changeset_id,
                base_revision=base_revision,
                status="SUCCESS",
                error_code=None,
                error_message=None,
                model=settings.LAW_CHANGESET_MODEL or settings.GEMINI_MODEL,
                processed_at=datetime.now(timezone.utc).isoformat(),
                result=changeset_result,
            )
            logger.info(
                f"LawChangeset extraction successful: taskId={task_id}, "
                f"operations={len(changeset_result.operations)}, "
                f"relations={len(changeset_result.relations)}"
            )
            await publish_law_changeset_response(success_resp)

        except asyncio.TimeoutError:
            logger.error(f"LawChangeset task {task_id} timed out after {total_deadline}s")
            err_resp = _make_failed_response("E-AI_MODEL_ERROR", "Quá thời gian xử lý.")
            await publish_law_changeset_response(err_resp)

        except LawChangesetFileDownloadError as de:
            err_resp = _make_failed_response("E-AI_FILE_DOWNLOAD", str(de.message))
            await publish_law_changeset_response(err_resp)

        except LawChangesetPdfUnreadableError as pe:
            err_resp = _make_failed_response("E-AI_PDF_UNREADABLE", str(pe.message))
            await publish_law_changeset_response(err_resp)

        except LawChangesetTooLargeError as te:
            err_resp = _make_failed_response("E-AI_TOO_LARGE", str(te.message))
            await publish_law_changeset_response(err_resp)

        except LawChangesetSchemaInvalidError as se:
            err_resp = _make_failed_response("E-AI_SCHEMA_INVALID", str(se.message))
            await publish_law_changeset_response(err_resp)

        except LawChangesetModelError as me:
            err_resp = _make_failed_response("E-AI_MODEL_ERROR", str(me.message))
            await publish_law_changeset_response(err_resp)

        except Exception as ex:
            logger.error(f"Internal error processing LawChangeset task {task_id}: {ex}", exc_info=True)
            err_resp = _make_failed_response("E-AI_INTERNAL", f"Lỗi nội bộ AI service: {ex}")
            await publish_law_changeset_response(err_resp)
