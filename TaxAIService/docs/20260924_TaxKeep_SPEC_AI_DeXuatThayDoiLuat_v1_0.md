# SPEC AI SERVICE: Đề xuất thay đổi luật từ văn bản mới (Law Changeset Extraction)

- **Dự án:** TaxKeep VN (FA26SE179)
- **Repo:** `TaxKeepVNAIService`, thư mục `AI/TaxAIService` (FastAPI, Gemini qua `google-genai`, RabbitMQ qua `aio_pika`, Pydantic v2, pytest)
- **Phiên bản:** v1.0, ngày 24/09/2026
- **Người đọc:** người phụ trách AI service và agent code (Claude Code, Cursor…) của người đó
- **Đi kèm:** `SPEC BE: Luật hệ thống` (bên BE .NET). Hai bản dùng chung hợp đồng ở §5

---

## 0. Cách dùng tài liệu này (dành cho agent)

1. Đọc hết tài liệu một lượt rồi mới sửa code. Làm theo thứ tự ở §14.
2. Chỉ làm trong phạm vi §2. Nếu thấy tài liệu mâu thuẫn với code thực tế thì dừng lại hỏi người phụ trách, không tự đoán.
3. Không đọc, không sửa file `.env`. Cấu hình mới khai báo trong `app/core/config.py`, có giá trị mặc định.
4. Hợp đồng RabbitMQ ở §5 là thoả thuận với bên BE. Không tự đổi tên trường, tên hàng đợi hay giá trị enum.

---

## 1. Bối cảnh

**Mô hình mới.** Hệ thống chuyển sang mô hình **luật hệ thống**:
- BE .NET giữ một bộ luật duy nhất, cộng dồn mọi văn bản cũ và mới.
- Mỗi lần admin duyệt một văn bản, hệ thống tạo một revision mới, giống commit trong git. Nhờ đó vẫn hỏi được luật áp dụng cho các năm cũ (2019, 2020–2025) lẫn năm mới (2026).

**Luồng xử lý:**
1. Admin upload văn bản lên BE.
2. BE gửi sang AI qua RabbitMQ: file, luật hệ thống hiện tại và danh mục mã luật.
3. AI đọc văn bản, trả về một **bản đề xuất thay đổi**:
   - văn bản này thay thế, sửa đổi, bãi bỏ hoặc hợp nhất văn bản nào;
   - văn bản này thêm, sửa, kết thúc hoặc đổi căn cứ cho những mã luật nào, từ ngày nào, kèm trích dẫn và số trang.
4. Admin duyệt từng dòng trên web, rồi BE merge.

**AI không ghi DB cho tính năng này.**

**Vì sao không dùng lại module `tax_rule` hiện có:**
- Mỗi năm chỉ có 1 bộ (`tax_rule_sets.tax_year` unique). `rule_code` unique trên toàn bảng, nên upload năm thứ hai là lỗi 409.
- Prompt ép phải đủ bậc thuế và 2 mức giảm trừ. Với văn bản chỉ sửa vài điều, AI buộc phải tự điền.
- Không có khái niệm thay thế, sửa đổi, bãi bỏ. `legalDocument` mặc định là tên file.
- Bản scan chỉ gửi 30 trang đầu, bản chữ cắt ở 45.000 ký tự. Các điều khoản thi hành nằm ở cuối văn bản nên không bao giờ được đọc (NĐ 253/2026 có 61 trang, điều khoản thi hành nằm ở trang 56–57).

---

## 2. Phạm vi

**Làm:**
1. Hai hàng đợi mới `law.changeset.request.queue` và `law.changeset.response.queue`, kèm consumer và producer mới.
2. Service mới gọi Gemini, trả kết quả đúng hợp đồng §5.
3. Chuẩn bị PDF sao cho đọc đủ trang (§8).
4. Hậu kiểm kết quả trước khi trả (§9).
5. Một endpoint đồng bộ để test, mặc định **tắt** (§11).
6. Unit test và bộ kiểm thử bằng văn bản thật (§13).

**Không làm:**
- Không đổi hành vi module `tax_rule` cũ: route `/api/tax-rules/*`, hàng đợi `tax.ai.*`, các bảng `tax_rule_sets`, `tax_rules`, `dependent_rules`. BE còn dùng các phần này tới khi chuyển xong.
- Không thêm migration, không đụng DB.
- Không sửa module OCR (người phụ thuộc, chi phí), system config, url rule.
- Không đụng 2 file đang có thay đổi chưa commit trong repo: `alembic/versions/4b7e28a09f3a_add_ai_extractions_and_system_configs.py` và `app/services/interfaces/itax_rule_service.py`.

---

## 3. Hiện trạng code liên quan

| File | Điều cần biết |
|---|---|
| `app/core/config.py` | `Settings(BaseSettings)` của `pydantic_settings`. `GEMINI_MODEL = "gemini-2.5-flash"`. Các hàng đợi `RABBITMQ_*` khai báo ở đây |
| `app/messaging/consumer.py` | `start_rabbitmq_consumer()` khai báo queue rồi gọi `queue.consume(handler)`. Thêm hàng đợi mới vào đây |
| `app/messaging/rabbitmq_client.py` | Có `rabbitmq_client.publish_json(routing_key, message_data)` |
| `app/messaging/tax_rule/consumer.py` | Mẫu tham khảo: `_resolve_file_bytes` (tải file bằng `httpx` từ `fileUrl`), dùng `message.process(requeue=False, ignore_processed=True)` |
| `app/services/tax_rule/pdf_service.py` | `prepare_pdf_for_ai(..., max_scan_pages=30)` cắt 30 trang. **Không sửa**, viết hàm mới ở §8 |
| `app/services/tax_rule/tax_rule_extraction_service.py` | Gọi `client.models.generate_content` (đồng bộ) ngay trong hàm async, và parse JSON tự do. Tính năng mới không làm như vậy (§7) |
| `app/services/ocr/dependent_ocr_service.py` | Mẫu dùng `response_schema=<Pydantic model>` với Gemini |
| `app/main.py` | `include_router(...)` cho các route. Consumer chạy nền khi khởi động |

---

## 4. File tạo mới và file sửa

Tạo mới (được phép đổi tên cho hợp phong cách repo, miễn giữ đúng cách chia lớp):

```
app/schemas/law_changeset/__init__.py
app/schemas/law_changeset/contract.py            # Pydantic cho message §5 (alias camelCase, populate_by_name)
app/schemas/law_changeset/gemini_output.py       # Pydantic dùng làm response_schema cho Gemini (§7)
app/prompts/law_changeset/__init__.py
app/prompts/law_changeset/law_changeset_prompt.py
app/services/law_changeset/__init__.py
app/services/law_changeset/pdf_preparer.py       # §8
app/services/law_changeset/law_changeset_service.py  # tải file → chuẩn bị PDF → gọi Gemini → ánh xạ → hậu kiểm
app/services/law_changeset/mapper.py             # gemini_output → contract (§7)
app/services/law_changeset/post_validator.py     # §9
app/messaging/law_changeset/__init__.py
app/messaging/law_changeset/consumer.py
app/messaging/law_changeset/producer.py
app/api/routes/law_changeset/__init__.py
app/api/routes/law_changeset/law_changeset_routes.py   # §11
app/errors/law_changeset_errors.py
tests/test_law_changeset_pdf_preparer.py
tests/test_law_changeset_mapper_validator.py
tests/test_law_changeset_messaging.py
tests/fixtures/law_changeset/nd253_request_context.json   # §13.3
```

Sửa:
- **`app/core/config.py`**, thêm các cấu hình sau:

  | Tên | Mặc định | Ghi chú |
  |---|---|---|
  | `RABBITMQ_LAW_CHANGESET_REQUEST_QUEUE` | `"law.changeset.request.queue"` | |
  | `RABBITMQ_LAW_CHANGESET_RESPONSE_QUEUE` | `"law.changeset.response.queue"` | |
  | `LAW_CHANGESET_MODEL` | `None` | `None` thì dùng `GEMINI_MODEL` |
  | `LAW_CHANGESET_MAX_FILE_MB` | `50` | |
  | `LAW_CHANGESET_INLINE_MAX_MB` | `18` | |
  | `LAW_CHANGESET_MAX_PAGES_PER_CALL` | `900` | |
  | `LAW_CHANGESET_TEXT_MAX_CHARS_PER_CALL` | `600000` | |
  | `LAW_CHANGESET_CALL_TIMEOUT_SECONDS` | `240` | Giới hạn cho một lần gọi Gemini |
  | `LAW_CHANGESET_TOTAL_DEADLINE_SECONDS` | `720` | Giới hạn cho cả request, kể cả thử lại và chia file |
  | `LAW_CHANGESET_SYNC_ENDPOINT_ENABLED` | `False` | |

- **`requirements.txt`:** đổi `google-genai>=1.0.0` thành `google-genai>=1.12.0`. Các bản từ 1.11.0 trở về trước báo lỗi "Default value is not supported in the response schema" khi schema có giá trị mặc định. Bản đang cài trong `.venv` là 2.24.0, dùng được.

- **`app/messaging/consumer.py`:** khai báo 2 hàng đợi mới (durable) và `consume` hàng đợi request bằng handler mới. Đặt cùng vòng lặp kết nối lại đang có.
- **`app/main.py`:** chỉ `include_router` của §11 khi `LAW_CHANGESET_SYNC_ENDPOINT_ENABLED` là `True`.

---

## 5. Hợp đồng RabbitMQ BE ↔ AI

> Mục này giống hệt nhau trong spec AI và spec BE. Sửa ở bên nào thì phải báo bên kia sửa cùng lúc.

### Hàng đợi

| Hàng đợi | Chiều | Ghi chú |
|---|---|---|
| `law.changeset.request.queue` | BE → AI | Durable, message persistent, JSON UTF-8 |
| `law.changeset.response.queue` | AI → BE | Durable, message persistent. Mỗi request đọc được `taskId` và `changesetId`, AI trả **đúng một** message, kể cả khi lỗi |

Hai hàng đợi cũ `tax.ai.request.queue` và `tax.ai.response.queue` giữ nguyên, không dùng cho tính năng này.

### Quy ước chung

- **Định dạng:** tên trường viết camelCase. Ngày dạng `YYYY-MM-DD`. Thời điểm dạng ISO 8601 UTC.
- **Khoảng áp dụng** là nửa mở `[applyFrom, applyTo)`:
  - `applyTo` là ngày đầu tiên rule **không còn** áp dụng.
  - `null` nghĩa là chưa có ngày kết thúc.
- **Số liệu:**
  - Số tiền là số VND, kiểu number, không có dấu phân cách.
  - Thuế suất là số thập phân từ 0 đến 1 (5% ghi là `0.05`).
- **Căn cứ:**
  - `article`, `clause`, `point` chỉ ghi số hoặc chữ cái, ví dụ `"49"`, `"2"`, `"a"`. Không kèm chữ "Điều", "khoản", "điểm".
  - `page` đánh số từ 1 theo thứ tự trang trong file PDF, không phải số in trên trang.
- **Số hiệu văn bản:** `documentNumber` ghi đúng như in trên văn bản, ví dụ `253/2026/NĐ-CP`, `109/2025/QH15`, `112/VBHN-VPQH`. Việc so khớp giữa các văn bản do BE làm (chuẩn hoá: bỏ khoảng trắng, viết hoa, bỏ dấu, `Đ` thành `D`).
- **Phiên bản hợp đồng:** `schemaVersion` hiện là `1`.
- **Trường chứa JSON tự do** gồm `valueJson`, `condition`, `proposedDefinition` và `targetScope`. Trên dây, chúng là mảng, object hoặc `null`, **không** phải chuỗi JSON.
  - Bên .NET khai báo các trường này là `JsonElement?` hoặc `JsonNode?`.
  - Bên Python khai báo là `Any`, `dict` hoặc `list`.

### Giá trị enum

| Trường | Giá trị |
|---|---|
| `documentType` | `LUAT`, `NGHI_QUYET`, `NGHI_DINH`, `THONG_TU`, `VBHN`, `QUYET_DINH`, `KHAC` |
| `relations[].type` | `REPLACES` (thay thế), `AMENDS` (sửa đổi, bổ sung), `REPEALS` (bãi bỏ), `BASED_ON` (căn cứ ban hành), `CONSOLIDATES` (văn bản hợp nhất này gộp văn bản đích) |
| `operations[].op` | `ADD`, `UPDATE`, `END`, `RECITE` |
| `valueKind` | `AMOUNT`, `RATE`, `SCHEDULE`, `JSON`, `FLAG`, `TEXT` |
| `ruleGroup` | `SCHEDULE`, `DEDUCTION`, `DEPENDENT`, `SETTLEMENT`, `WITHHOLDING`, `RATE`, `EXEMPTION` |
| `unit` | `VND/month`, `VND/year`, `VND/person/month`, `VND/payment`, hoặc `null` |
| `legalStatus` | `CON_HIEU_LUC`, `HET_HIEU_LUC_MOT_PHAN`, `HET_HIEU_LUC`, `CHUA_RO` |
| `status` (response) | `SUCCESS`, `FAILED` |
| `errorCode` (response) | `E-AI_BAD_REQUEST`, `E-AI_FILE_DOWNLOAD`, `E-AI_PDF_UNREADABLE`, `E-AI_TOO_LARGE`, `E-AI_MODEL_ERROR`, `E-AI_SCHEMA_INVALID`, `E-AI_INTERNAL`. (`E-AI_TIMEOUT` do BE tự ghi khi chờ quá giờ, AI không gửi mã này) |
| `coverage.mode` | `TEXT` (gửi lớp chữ), `PDF` (gửi file PDF cho Gemini đọc ảnh) |

### Bốn loại dòng thay đổi

| op | Nghĩa | Trường bắt buộc |
|---|---|---|
| `ADD` | Thêm một mã luật mà tại ngày `applyFrom` chưa có phiên bản nào | `after`, `applyFrom` |
| `UPDATE` | Kể từ `applyFrom`, giá trị của mã luật đổi thành `after` | `after`, `applyFrom` |
| `END` | Mã luật thôi áp dụng kể từ `applyTo`. Chỉ dùng khi văn bản viết rõ việc bãi bỏ hoặc chấm dứt | `applyTo` |
| `RECITE` | Giá trị giữ nguyên, nhưng kể từ `applyFrom` căn cứ chuyển sang văn bản này (văn bản mới nhắc lại quy định cũ) | `applyFrom` (`after` được phép null) |

`citation` của mỗi dòng luôn trỏ vào **văn bản đang được đọc**, nên không có `documentNumber`.

### Kiểu giá trị theo `valueKind`

| valueKind | Trường dùng trong `after` và `currentRules` | Ví dụ |
|---|---|---|
| `AMOUNT` | `valueNumber`, `unit` | `23000000` và `"VND/year"` |
| `RATE` | `valueNumber` | `0.1` |
| `SCHEDULE` | `valueJson`: mảng bậc, `toAnnual` tăng dần, bậc cuối có `toAnnual` là `null` | `[{"toAnnual":120000000,"rate":0.05},{"toAnnual":360000000,"rate":0.1},{"toAnnual":720000000,"rate":0.2},{"toAnnual":1200000000,"rate":0.3},{"toAnnual":null,"rate":0.35}]` |
| `JSON` | `valueJson` theo mô tả của mã đó trong danh mục (ví dụ `PIT_DEPENDENT_GROUPS`) | Xem danh mục mã |
| `FLAG` | `valueText`: mô tả điều kiện hoặc nghĩa vụ | `"Có đề nghị giảm trừ y tế, giáo dục thì người nộp thuế phải tự quyết toán"` |
| `TEXT` | `valueText` | |

Ngoài ra có hai trường tuỳ chọn:
- `condition` (object): điều kiện dạng khoá và giá trị, ví dụ `{"domesticFacility": true, "tuitionOnly": true}`.
- `conditionText` (string): điều kiện mô tả bằng lời.

### Request `LawChangesetExtractRequest` (BE → AI)

```json
{
  "schemaVersion": 1,
  "taskId": "2f0c5b0e-6a55-4f4e-9d1c-7a3f3b2a9c10",
  "changesetId": "6b9d3f2e-1c4a-4b7e-8f0d-2a1b3c4d5e6f",
  "fileUrl": "https://<storage>/law-documents/nd-253-2026.pdf",
  "fileName": "nd-253-2026.pdf",
  "sourceUrl": null,
  "documentNumberHint": null,
  "baseRevision": 4,
  "currentRules": [
    {
      "versionId": "0f6c1a52-8a0e-4c1e-9a55-3f0c2b1d7e11",
      "ruleCode": "PIT_WITHHOLD_CASUAL_MIN_PAYMENT",
      "valueKind": "AMOUNT",
      "valueNumber": 2000000,
      "valueJson": null,
      "valueText": null,
      "unit": "VND/payment",
      "condition": null,
      "conditionText": null,
      "applyFrom": "2013-07-01",
      "applyTo": null,
      "citation": { "documentNumber": "111/2013/TT-BTC", "article": "25", "clause": "1", "point": "i", "page": null }
    }
  ],
  "ruleCatalog": [
    {
      "ruleCode": "PIT_DEDUCTION_MEDICAL",
      "ruleGroup": "DEDUCTION",
      "valueKind": "AMOUNT",
      "defaultUnit": "VND/year",
      "displayName": "Giảm trừ chi phí y tế",
      "description": "Mức trần giảm trừ chi phí khám, chữa bệnh của người nộp thuế và người phụ thuộc trong một năm"
    }
  ],
  "knownDocuments": [
    { "documentNumber": "111/2013/TT-BTC", "documentType": "THONG_TU", "title": "Thông tư hướng dẫn thực hiện Luật Thuế thu nhập cá nhân …", "legalStatus": "CON_HIEU_LUC" }
  ]
}
```

| Trường | Bắt buộc | Ghi chú |
|---|---|---|
| `taskId`, `changesetId` | Có | UUID do BE sinh. AI trả lại y nguyên |
| `fileUrl`, `fileName` | Có | AI tải file qua HTTP GET, cho theo redirect |
| `sourceUrl`, `documentNumberHint` | Không | Gợi ý của admin. AI chỉ dùng để đối chiếu, không tin mù quáng |
| `baseRevision` | Có | Số revision của luật hệ thống lúc BE gửi (luật rỗng thì là 0). AI trả lại y nguyên |
| `currentRules` | Có (được phép rỗng) | **Toàn bộ** phiên bản đang hiệu lực của mọi mã, kể cả phiên bản của năm cũ, sắp theo `ruleCode` rồi `applyFrom` |
| `ruleCatalog` | Có | Danh mục mã luật đang bật. AI chỉ được dùng mã trong danh mục, trừ khi đề xuất mã mới (`newCode`) |
| `knownDocuments` | Có (được phép rỗng) | Các văn bản hệ thống đã biết, kể cả văn bản chỉ được nhắc tới |

### Response `LawChangesetExtractResponse` (AI → BE)

```json
{
  "schemaVersion": 1,
  "taskId": "2f0c5b0e-6a55-4f4e-9d1c-7a3f3b2a9c10",
  "changesetId": "6b9d3f2e-1c4a-4b7e-8f0d-2a1b3c4d5e6f",
  "baseRevision": 4,
  "status": "SUCCESS",
  "errorCode": null,
  "errorMessage": null,
  "model": "gemini-2.5-flash",
  "processedAt": "2026-09-24T08:00:00Z",
  "result": {
    "coverage": { "totalPages": 61, "pagesRead": 61, "mode": "PDF", "chunks": 1 },
    "document": {
      "documentNumber": "253/2026/NĐ-CP",
      "documentType": "NGHI_DINH",
      "issuer": "Chính phủ",
      "title": "Quy định chi tiết một số điều và biện pháp để tổ chức, hướng dẫn thi hành Luật Thuế thu nhập cá nhân",
      "issuedDate": "2026-06-30",
      "effectiveDate": "2026-07-01",
      "evidencePage": 1
    },
    "relations": [
      {
        "relationKey": "rel-1",
        "type": "REPLACES",
        "targetDocumentNumber": "65/2013/NĐ-CP",
        "targetScope": null,
        "effectiveDate": "2026-07-01",
        "citation": { "article": "69", "clause": "2", "point": null, "page": 57 },
        "evidence": "Nghị định này thay thế Nghị định số 65/2013/NĐ-CP …",
        "note": null
      }
    ],
    "operations": [
      {
        "opKey": "op-1",
        "op": "ADD",
        "ruleCode": "PIT_DEDUCTION_MEDICAL",
        "newCode": false,
        "proposedDefinition": null,
        "after": {
          "valueNumber": 23000000,
          "valueJson": null,
          "valueText": null,
          "unit": "VND/year",
          "condition": { "domesticFacility": true, "withinHealthInsuranceList": true, "requiresMedicalCostStatement": true },
          "conditionText": "Khám, chữa bệnh tại cơ sở trong nước, thuộc danh mục bảo hiểm y tế chi trả; có bảng kê chi phí"
        },
        "applyFrom": "2026-01-01",
        "applyTo": null,
        "applyBasis": { "article": "69", "clause": "1", "point": "a", "page": 57 },
        "citation": { "article": "49", "clause": "2", "point": "a", "page": 34 },
        "evidence": "… tổng không quá 23 triệu đồng/năm",
        "confidence": 0.95,
        "rationale": "Chưa có mã này trong currentRules"
      }
    ],
    "references": [
      {
        "text": "Biểu thuế lũy tiến từng phần quy định tại Điều 9 của Luật Thuế thu nhập cá nhân",
        "targetDocumentNumber": "109/2025/QH15",
        "article": "9", "clause": null, "point": null, "page": 29
      }
    ],
    "warnings": []
  }
}
```

| Trường | Ghi chú |
|---|---|
| `status`, `errorCode`, `errorMessage` | Với `FAILED`: `result` là `null`, `errorCode` thuộc enum, `errorMessage` ngắn gọn bằng tiếng Việt |
| `result.coverage` | `pagesRead` là số trang **thực sự** đã gửi cho model. `chunks` lớn hơn 1 nếu phải chia file |
| `result.document` | Trường nào không đọc được thì để `null`. Không tự đoán |
| `relations[].targetScope` | `null` nghĩa là cả văn bản. Còn lại là `{ "article": "3", "clause": null, "point": null }` |
| `relations[].effectiveDate` | Ngày quan hệ có hiệu lực, thường là ngày hiệu lực của văn bản đang đọc |
| `relations[].note` | Với `CONSOLIDATES`: văn bản **gốc** được hợp nhất (luật, nghị định hay thông tư gốc, không phải văn bản sửa đổi) có `note` = `"BASE"`. Mỗi văn bản hợp nhất có đúng một quan hệ `BASE` |
| `operations[].newCode`, `proposedDefinition` | Chỉ khi không có mã phù hợp trong danh mục. Khi đó `proposedDefinition` gồm `{ ruleCode, ruleGroup, valueKind, defaultUnit, displayName, description }` |
| `operations[].applyBasis` | Căn cứ cho ngày `applyFrom` (thường là điều hiệu lực hoặc điều chuyển tiếp) |
| `operations[].evidence` | Trích nguyên văn, tối đa 300 ký tự |
| `operations[].confidence` | Số từ 0 đến 1 |
| `references[]` | Chỗ văn bản dẫn chiếu văn bản khác mà không tự đặt ra số liệu. **Không** sinh dòng thay đổi |
| `warnings[]` | Cảnh báo dạng câu ngắn, ví dụ "Mức thu nhập tối đa của người phụ thuộc do Bộ trưởng Bộ Tài chính quy định, văn bản này không nêu số" |

---

## 6. Nghiệp vụ AI phải làm

### 6.1. Phạm vi nội dung
- **Chỉ lấy:** quy định về thu nhập từ **tiền lương, tiền công**, của cả cá nhân cư trú lẫn không cư trú.
- **Bỏ qua:** thu nhập từ kinh doanh, đầu tư vốn, chuyển nhượng vốn, chuyển nhượng bất động sản, trúng thưởng, bản quyền, nhượng quyền thương mại, thừa kế, quà tặng.

### 6.2. Thông tin văn bản (`result.document`)
- **Số hiệu, loại văn bản, cơ quan ban hành, ngày ký:** lấy ở trang đầu.
- **Ngày hiệu lực:** lấy ở điều hiệu lực thi hành.
- Trường nào không đọc được thì để `null`, không suy đoán.

### 6.3. Quan hệ văn bản (`result.relations`)
- **Điều khoản thi hành** (hiệu lực thi hành, điều khoản chuyển tiếp, trách nhiệm thi hành):
  - "thay thế văn bản X" → `REPLACES` X, `targetScope` là `null`.
  - "bãi bỏ Điều/khoản… của văn bản X" → `REPEALS` X, có `targetScope`. Bãi bỏ cả văn bản thì `targetScope` là `null`.
- **Tên văn bản** dạng "… sửa đổi, bổ sung một số điều của X", hoặc nghị quyết "điều chỉnh mức … quy định tại khoản … Điều … của Luật X" → `AMENDS` X, `targetScope` là điều hoặc khoản bị sửa. Mỗi điều bị sửa là một quan hệ riêng.
- **Văn bản hợp nhất (VBHN):** phần đầu liệt kê văn bản gốc và các văn bản sửa đổi → `CONSOLIDATES` từng văn bản được hợp nhất. Văn bản gốc (ví dụ Luật 04/2007/QH12 trong VBHN 103) đặt `note = "BASE"`, và mỗi VBHN có đúng một quan hệ `BASE`.
- **Đoạn "Căn cứ …" ở đầu văn bản** → `BASED_ON`, chỉ với các văn bản về thuế thu nhập cá nhân. Bỏ qua các luật tổ chức bộ máy.
- **`effectiveDate`:** ngày quan hệ có hiệu lực. Mặc định là ngày hiệu lực của văn bản đang đọc, trừ khi điều khoản ghi ngày khác.
- Mỗi quan hệ bắt buộc có `citation` (điều, khoản, trang) và `evidence`.

### 6.4. Dòng thay đổi (`result.operations`)

Làm theo các bước sau cho **từng quy định do chính văn bản này đặt ra** trong phạm vi §6.1. Quy định loại này gồm: mức tiền, thuế suất, ngưỡng, biểu thuế, nhóm người phụ thuộc, nghĩa vụ tự quyết toán…

1. **Ghép mã.** Ghép quy định vào một `ruleCode` trong `ruleCatalog`, dựa theo `description`. Không ghép được thì đề xuất mã mới: `newCode: true` kèm `proposedDefinition`. Mã mới phải có tiền tố `PIT_`, viết IN HOA dạng SNAKE_CASE.
2. **Ngày áp dụng.** Xác định `applyFrom` theo §6.5.
3. **So với `currentRules`.** Lấy phiên bản của mã đó đang phủ ngày `applyFrom`, rồi xét:

   | Tình huống | Loại dòng |
   |---|---|
   | Không có phiên bản nào phủ ngày đó | `ADD` |
   | Có phiên bản, giá trị khác | `UPDATE` |
   | Giá trị giống hệt, văn bản căn cứ khác, và văn bản đang đọc **cùng cấp hoặc cao hơn** văn bản căn cứ hiện tại (§6.6) | `RECITE` |
   | Giá trị giống hệt, văn bản đang đọc **thấp hơn** văn bản căn cứ hiện tại | Không sinh dòng |
   | Giá trị và căn cứ giống hệt | Không sinh dòng |

4. **Kết thúc hiệu lực.** Chỉ sinh `END` khi văn bản **viết rõ** việc bãi bỏ hoặc chấm dứt một quy định đang có trong `currentRules`, và phải kèm trích dẫn. Rule chỉ "không được nhắc lại" trong văn bản thay thế thì **không** sinh `END`: BE tự phát hiện trường hợp này và để admin quyết.
5. **Dẫn chiếu, giao việc.** Số liệu văn bản chỉ dẫn chiếu văn bản khác (ví dụ "theo Điều 9 của Luật", "theo điểm a khoản 1 Điều 10 của Luật") thì **không** sinh dòng, ghi vào `references`. Quy định dạng giao việc (ví dụ "do Bộ trưởng Bộ Tài chính quy định") thì ghi vào `warnings`.
6. **Bằng chứng.** Mỗi dòng bắt buộc có:
   - `citation`: điều, khoản, điểm nếu có, và trang;
   - `evidence`: trích nguyên văn, tối đa 300 ký tự;
   - `confidence`: từ 0 đến 1;
   - `rationale`: một câu giải thích vì sao chọn loại dòng đó.
7. **Không gộp.** Mỗi mã luật chỉ có một dòng cho mỗi `applyFrom`.

### 6.5. Ngày áp dụng
- **Hai loại ngày khác nhau.** Luôn phân biệt **ngày hiệu lực của văn bản** với **kỳ tính thuế bắt đầu áp dụng**. Ví dụ: NĐ 253/2026/NĐ-CP có hiệu lực từ 01/7/2026, nhưng Điều 69 khoản 1 điểm a cho các quy định về tiền lương, tiền công áp dụng từ kỳ tính thuế 2026. Khi đó `applyFrom` là `2026-01-01`, còn `applyBasis` là Điều 69 khoản 1 điểm a.
- **Cách chọn `applyFrom`:**

  | Văn bản ghi | `applyFrom` |
  |---|---|
  | "áp dụng từ kỳ tính thuế năm Y" | `Y-01-01` |
  | Không có quy định riêng | Ngày hiệu lực của văn bản |
  | Văn bản hợp nhất, có chú thích ngày hiệu lực của từng điều sửa đổi | Ngày trong chú thích |
  | Không xác định được | `null`, kèm cảnh báo trong `warnings`. BE sẽ bắt admin nhập |

- **`applyTo`:** chỉ điền khi chính văn bản giới hạn thời gian áp dụng.

### 6.6. Thứ bậc văn bản (dùng cho bước 3 ở §6.4)
Theo thứ tự từ cao xuống thấp:
1. `LUAT`
2. `NGHI_QUYET` của Ủy ban Thường vụ Quốc hội
3. `NGHI_DINH`
4. `QUYET_DINH`
5. `THONG_TU`
6. `KHAC`

**VBHN** lấy cấp của văn bản gốc mà nó hợp nhất (quan hệ `CONSOLIDATES` có `note = "BASE"`, tra trong `knownDocuments` hoặc trong chính văn bản). Chưa biết văn bản gốc thì: số hiệu có `VBHN-VPQH` là cấp 1, còn lại coi là cấp 3.

Ví dụ: Thông tư nhắc lại mức 15,5 triệu đã có trong Luật thì không sinh dòng. Nghị định nhắc lại thuế suất 10% đang lấy căn cứ ở Thông tư thì sinh `RECITE`.

### 6.7. Không bịa
- Không điền số liệu không có trong văn bản đang đọc.
- Không thêm quan hệ với văn bản mà văn bản đang đọc không nêu.
- Không dùng kiến thức bên ngoài để "hoàn thiện" bộ luật.

---

## 7. Schema nội bộ cho Gemini và ánh xạ ra hợp đồng

`response_schema` của Gemini không hợp với object tự do (`dict`), nên model gửi cho Gemini dùng kiểu cụ thể như sau, rồi `mapper.py` chuyển sang hợp đồng §5:

```python
# app/schemas/law_changeset/gemini_output.py  (tên field ví dụ, giữ đúng ý nghĩa)
class GCitation(BaseModel):
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None

class GBracket(BaseModel):
    toAnnual: Optional[float] = None   # null cho bậc cuối
    rate: float                        # 0..1

class GDependentGroup(BaseModel):
    group: Literal["CHILD", "ADULT_CHILD", "SPOUSE", "PARENT", "OTHER"]
    name: str
    maxAge: Optional[int] = None
    requiresStudying: bool = False
    requiresDisability: bool = False
    incomeLimitApplies: bool = False
    conditions: List[str] = []

class GConditionItem(BaseModel):
    key: str
    value: str                          # mapper đổi "true"/"false"/số sang kiểu tương ứng

class GValue(BaseModel):
    valueNumber: Optional[float] = None
    valueText: Optional[str] = None
    unit: Optional[Literal["VND/month", "VND/year", "VND/person/month", "VND/payment"]] = None
    schedule: Optional[List[GBracket]] = None
    dependentGroups: Optional[List[GDependentGroup]] = None
    conditionItems: Optional[List[GConditionItem]] = None
    conditionText: Optional[str] = None

class GOperation(BaseModel):
    op: Literal["ADD", "UPDATE", "END", "RECITE"]
    ruleCode: str
    newCode: bool = False
    proposedRuleGroup: Optional[str] = None
    proposedValueKind: Optional[str] = None
    proposedDefaultUnit: Optional[str] = None
    proposedDisplayName: Optional[str] = None
    proposedDescription: Optional[str] = None
    after: Optional[GValue] = None
    applyFrom: Optional[str] = None      # YYYY-MM-DD
    applyTo: Optional[str] = None
    applyBasis: Optional[GCitation] = None
    citation: GCitation
    evidence: str
    confidence: float
    rationale: Optional[str] = None

class GRelation(BaseModel):
    type: Literal["REPLACES", "AMENDS", "REPEALS", "BASED_ON", "CONSOLIDATES"]
    targetDocumentNumber: str
    targetArticle: Optional[str] = None
    targetClause: Optional[str] = None
    targetPoint: Optional[str] = None
    effectiveDate: Optional[str] = None
    citation: GCitation
    evidence: str
    note: Optional[str] = None

class GDocument(BaseModel):
    documentNumber: Optional[str] = None
    documentType: Optional[Literal["LUAT", "NGHI_QUYET", "NGHI_DINH", "THONG_TU", "VBHN", "QUYET_DINH", "KHAC"]] = None
    issuer: Optional[str] = None
    title: Optional[str] = None
    issuedDate: Optional[str] = None
    effectiveDate: Optional[str] = None
    evidencePage: Optional[int] = None

class GReference(BaseModel):
    text: str
    targetDocumentNumber: Optional[str] = None
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None

class GeminiChangesetOutput(BaseModel):
    document: GDocument
    relations: List[GRelation] = []
    operations: List[GOperation] = []
    references: List[GReference] = []
    warnings: List[str] = []
```

Ánh xạ sang hợp đồng:

| Nguồn trong `gemini_output` | Đích trong hợp đồng |
|---|---|
| `schedule` | `after.valueJson` (mảng `{toAnnual, rate}`) |
| `dependentGroups` | `after.valueJson` |
| `conditionItems` | `after.condition`: object, đổi `"true"`, `"false"` sang boolean và chuỗi số sang number |
| `targetArticle`, `targetClause`, `targetPoint` | `targetScope`. Nếu cả ba đều `null` thì `targetScope` là `null` |
| `proposed*` | `proposedDefinition`, chỉ khi `newCode` là `true` |

`opKey` (`op-1`, `op-2`…) và `relationKey` (`rel-1`…) do mapper tự đánh số.

**Cách gọi Gemini:**
- Không gọi hàm đồng bộ trong handler async, vì sẽ chặn event loop và làm chậm các consumer khác. Dùng bản async:
  ```python
  response = await client.aio.models.generate_content(
      model=settings.LAW_CHANGESET_MODEL or settings.GEMINI_MODEL,
      contents=[*document_parts, prompt_text],
      config=types.GenerateContentConfig(
          response_mime_type="application/json",
          response_schema=GeminiChangesetOutput,
          temperature=0,
      ),
  )
  ```
  Nếu phiên bản SDK trong repo chưa có `client.aio` thì bọc lời gọi đồng bộ bằng `asyncio.to_thread`.
- Đọc kết quả bằng `response.parsed`. Nếu giá trị này là `None` thì dùng `GeminiChangesetOutput.model_validate_json(response.text)`.
- Đặt timeout `LAW_CHANGESET_CALL_TIMEOUT_SECONDS` bằng `asyncio.wait_for`.

---

## 8. Đọc PDF đủ trang (`pdf_preparer.py`)

Theo tài liệu của Gemini API, model nhận file PDF tới 50 MB hoặc 1000 trang, mỗi trang khoảng 258 token. NĐ 253/2026 dài 61 trang, nặng 2,9 MB, tức chỉ khoảng 16.000 token. Không có lý do gì để cắt 30 trang.

**Mở file và kiểm tra:**
- Mở bằng `pymupdf` để lấy `total_pages`.
- File lớn hơn `LAW_CHANGESET_MAX_FILE_MB` thì trả `FAILED` với mã `E-AI_TOO_LARGE`.
- Không mở được file thì trả `FAILED` với mã `E-AI_PDF_UNREADABLE`.

**Chọn cách gửi:**

| Điều kiện | `mode` | Cách gửi |
|---|---|---|
| Mọi trang đều có từ 15 ký tự chữ trở lên | `TEXT` | Gửi toàn văn, chèn dấu `--- [Trang i] ---` trước mỗi trang. Không cắt 45.000 ký tự |
| Có ít nhất một trang scan hoặc trống | `PDF` | Gửi file PDF: file ≤ `LAW_CHANGESET_INLINE_MAX_MB` thì dùng `types.Part.from_bytes(mime_type="application/pdf")`; lớn hơn thì upload qua Files API (`client.files.upload`) rồi đưa tham chiếu file vào `contents` |

**Chia file khi quá giới hạn** (hiếm gặp):
- Giới hạn của một lần gọi là `LAW_CHANGESET_MAX_PAGES_PER_CALL` trang, hoặc `LAW_CHANGESET_TEXT_MAX_CHARS_PER_CALL` ký tự với `mode = TEXT`.
- Chia theo cụm trang. **Luôn** có thêm một lượt riêng cho 5 trang cuối, là chỗ chứa điều khoản thi hành.
- **Số trang:** file con khi tách sẽ đánh số lại từ 1. Phải cộng thêm vị trí trang bắt đầu của cụm vào mọi `page` trong kết quả, để `page` vẫn đúng theo file gốc.
- **Các cụm giữa** không thấy trang đầu (số hiệu, ngày ký) và điều hiệu lực. Vì vậy:
  - `document` lấy từ lượt có trang 1;
  - `relations` và căn cứ ngày áp dụng lấy từ lượt 5 trang cuối;
  - dòng nào ở cụm giữa có `applyFrom` null thì điền theo lượt cuối, và gắn `applyBasis` tương ứng.
- **Gộp kết quả:**
  - `operations` trùng khoá (`ruleCode`, ngày của dòng) thì giữ bản có `confidence` cao hơn. Ngày của dòng là `applyFrom`, riêng `END` dùng `applyTo`.
  - `relations` bỏ trùng.
- Ghi `coverage.chunks` là số lượt đã gọi.

**`coverage.pagesRead`** phải là số trang **thực sự** đã gửi cho model. BE dùng số này để cảnh báo admin khi AI đọc thiếu.

---

## 9. Hậu kiểm trước khi trả (`post_validator.py`)

BE sẽ kiểm lại một lần nữa. AI vẫn phải lọc các lỗi dưới đây để kết quả sạch; mỗi chỗ phải sửa hoặc bỏ thì ghi thêm một câu vào `warnings`.

| Kiểm | Xử lý |
|---|---|
| Ngày sai định dạng `YYYY-MM-DD` | Đặt thành `null` |
| `RATE` hoặc `rate` của bậc nằm ngoài khoảng 0–1 (ví dụ 5 thay cho 0.05) | Nếu nằm trong khoảng 1–100 thì chia cho 100 và ghi cảnh báo. Còn lại thì bỏ dòng |
| `SCHEDULE` có `toAnnual` không tăng dần, hoặc bậc cuối không phải `null` | Giữ nguyên dòng, ghi cảnh báo |
| `ruleCode` không có trong danh mục mà `newCode` là `false` | Bỏ dòng |
| Trùng khoá (`ruleCode`, ngày của dòng); ngày của dòng là `applyFrom`, riêng `END` dùng `applyTo` | Giữ dòng có `confidence` cao hơn |
| Dòng có giá trị giống và văn bản căn cứ giống phiên bản hiện tại (xem cách so sánh bên dưới) | Bỏ dòng |
| `evidence` dài hơn 300 ký tự | Cắt, thêm dấu `…` |
| `article`, `clause`, `point` còn chữ "Điều", "khoản", "điểm" | Bỏ phần chữ, chỉ giữ số hoặc chữ cái |
| `unit` không thuộc enum | Đặt thành `null`, ghi cảnh báo |

**Cách so sánh "giống", dùng chung quy tắc với BE:**

| Thứ so sánh | Giống khi |
|---|---|
| AMOUNT, RATE | Cùng số, cùng `unit` |
| SCHEDULE | Cùng số bậc, từng bậc cùng `toAnnual` và `rate` |
| JSON | Bằng nhau sau khi sắp khoá và bỏ khoảng trắng |
| FLAG, TEXT | Bằng nhau sau khi bỏ khoảng trắng ở hai đầu và gộp khoảng trắng giữa các chữ |
| `condition` | Chỉ so khi cả hai bên cùng khác `null` |
| `conditionText` | Không so |
| Văn bản căn cứ | So bằng số hiệu đã chuẩn hoá: bỏ khoảng trắng, bỏ dấu, `Đ` thành `D`, viết hoa |

---

## 10. Lỗi và độ bền

- **Luôn trả đúng một message response cho mỗi request đọc được `taskId` và `changesetId`.**
  - Message trả về giữ nguyên `taskId`, `changesetId` và `baseRevision` (nếu có).
  - Không đọc được JSON, hoặc thiếu `taskId` hay `changesetId`: không có địa chỉ để trả, nên chỉ ghi log rồi ack.
  - Cách parse: đọc 2 trường này trước bằng một model tối giản. Sau đó mới kiểm phần còn lại (`schemaVersion`, các trường bắt buộc). Lỗi ở bước sau thì trả `FAILED` với `E-AI_BAD_REQUEST`. **Không** khai báo `schemaVersion` kiểu `Literal[1]` ở bước parse đầu, vì như vậy request `schemaVersion = 2` sẽ không nhận được phản hồi.
- **Giới hạn thời gian cho cả request:** `LAW_CHANGESET_TOTAL_DEADLINE_SECONDS` (mặc định 12 phút), tính cả thử lại và chia file. Quá hạn thì trả `FAILED` với `E-AI_MODEL_ERROR`, message "Quá thời gian xử lý". Mốc này phải nhỏ hơn:
  - thời gian chờ của BE (20 phút);
  - `consumer_timeout` mặc định của RabbitMQ (30 phút). Vượt mốc này, message chưa ack sẽ bị giao lại và xử lý lần hai.
- **Bảng mã lỗi:**

  | Tình huống | `errorCode` |
  |---|---|
  | `schemaVersion` khác 1, hoặc thiếu trường bắt buộc | `E-AI_BAD_REQUEST` |
  | Tải file lỗi, hoặc HTTP khác 200 | `E-AI_FILE_DOWNLOAD` |
  | Không mở được PDF | `E-AI_PDF_UNREADABLE` |
  | Vượt giới hạn dung lượng | `E-AI_TOO_LARGE` |
  | Gemini lỗi hoặc timeout (đã thử lại 2 lần, cách 2 giây rồi 5 giây) | `E-AI_MODEL_ERROR` |
  | Kết quả không khớp schema (đã thử lại 1 lần, thêm câu nhắc "chỉ trả JSON đúng schema") | `E-AI_SCHEMA_INVALID` |
  | Lỗi khác | `E-AI_INTERNAL` |

- **Ack:** dùng `message.process(requeue=False, ignore_processed=True)` như consumer cũ. Publish response xong rồi mới ack.
- **Log:** ghi `taskId`, `changesetId`, `mode`, `pagesRead`, số dòng thay đổi và thời gian xử lý. Không log toàn văn văn bản.

---

## 11. Endpoint đồng bộ để test

- **Route:** `POST /api/law-changesets/extract`, chỉ bật khi `LAW_CHANGESET_SYNC_ENDPOINT_ENABLED` là `True`.
  - Lý do: gateway có route `/ai/{**catch-all}` chuyển mọi đường dẫn vào AI service. Để endpoint này mở mặc định thì ai cũng gọi được.
- **Input** (multipart):
  - `file`: file PDF.
  - `context`: chuỗi JSON gồm `baseRevision`, `currentRules`, `ruleCatalog`, `knownDocuments`, `documentNumberHint`, `sourceUrl`. Cấu trúc giống request §5 nhưng không có `fileUrl`.
- **Output:** đúng `LawChangesetExtractResponse`. Endpoint tự sinh `taskId` và `changesetId` ngẫu nhiên.
- **Không ghi DB.** Dùng chung `law_changeset_service` với consumer.

---

## 12. Danh mục mã luật ban đầu (để test)

Nguồn chuẩn của danh mục nằm ở BE. BE gửi danh mục kèm mỗi request, nên AI **không** được viết cứng danh sách mã trong code. Bảng dưới đây chỉ dùng để dựng fixture test.

| ruleCode | ruleGroup | valueKind | defaultUnit | Mô tả |
|---|---|---|---|---|
| `PIT_TAX_SCHEDULE` | SCHEDULE | SCHEDULE | VND/year | Biểu thuế lũy tiến từng phần cho thu nhập từ tiền lương, tiền công của cá nhân cư trú, ngưỡng tính theo năm |
| `PIT_DEDUCTION_PERSONAL` | DEDUCTION | AMOUNT | VND/month | Mức giảm trừ gia cảnh cho bản thân người nộp thuế |
| `PIT_DEDUCTION_DEPENDENT` | DEDUCTION | AMOUNT | VND/person/month | Mức giảm trừ cho mỗi người phụ thuộc |
| `PIT_DEPENDENT_GROUPS` | DEPENDENT | JSON | — | Các nhóm người phụ thuộc và điều kiện. `valueJson` là mảng `GDependentGroup` |
| `PIT_DEPENDENT_MAX_MONTHLY_INCOME` | DEPENDENT | AMOUNT | VND/month | Thu nhập bình quân tháng tối đa của người phụ thuộc |
| `PIT_DEDUCTION_MANDATORY_INSURANCE` | DEDUCTION | FLAG | — | Được trừ các khoản bảo hiểm bắt buộc theo số thực đóng |
| `PIT_DEDUCTION_VOLUNTARY_INSURANCE_CAP` | DEDUCTION | AMOUNT | VND/month | Mức trần được trừ cho bảo hiểm hưu trí bổ sung, hưu trí tự nguyện, nhân thọ |
| `PIT_DEDUCTION_CHARITY` | DEDUCTION | FLAG | — | Được trừ các khoản đóng góp từ thiện, nhân đạo, khuyến học theo chứng từ |
| `PIT_DEDUCTION_MEDICAL` | DEDUCTION | AMOUNT | VND/year | Mức trần giảm trừ chi phí khám, chữa bệnh của người nộp thuế và người phụ thuộc |
| `PIT_DEDUCTION_EDUCATION` | DEDUCTION | AMOUNT | VND/year | Mức trần giảm trừ chi phí giáo dục, đào tạo (học phí) của người nộp thuế và người phụ thuộc |
| `PIT_SETTLEMENT_SELF_REQUIRED_IF_MED_EDU` | SETTLEMENT | FLAG | — | Có đề nghị giảm trừ y tế, giáo dục thì người nộp thuế phải tự quyết toán |
| `PIT_WITHHOLD_CASUAL_RATE` | WITHHOLDING | RATE | — | Tỷ lệ khấu trừ với cá nhân cư trú không ký hợp đồng lao động hoặc ký hợp đồng dưới 3 tháng |
| `PIT_WITHHOLD_CASUAL_MIN_PAYMENT` | WITHHOLDING | AMOUNT | VND/payment | Mức chi trả mỗi lần, từ mức này trở lên thì phải khấu trừ theo `PIT_WITHHOLD_CASUAL_RATE` |
| `PIT_RATE_NON_RESIDENT_SALARY` | RATE | RATE | — | Thuế suất với tiền lương, tiền công của cá nhân không cư trú |
| `PIT_EXEMPTION_OVERTIME` | EXEMPTION | TEXT | — | Miễn thuế phần tiền lương làm đêm, làm thêm giờ được trả cao hơn |
| `PIT_EXEMPTION_RETIREMENT_PENSION` | EXEMPTION | TEXT | — | Miễn thuế tiền lương hưu do Quỹ bảo hiểm xã hội chi trả |
| `PIT_EXEMPTION_INSURANCE_COMPENSATION` | EXEMPTION | TEXT | — | Miễn thuế tiền bồi thường bảo hiểm, trợ cấp tai nạn lao động, bệnh nghề nghiệp |

---

## 13. Kiểm thử

### 13.1. Unit test (mock Gemini, không cần API key)

| Test | Kỳ vọng |
|---|---|
| `pdf_preparer`, file có chữ 61 trang (tạo bằng `pymupdf`) | `mode = TEXT`, `pagesRead = 61`, có dấu của trang 61 trong nội dung gửi đi |
| `pdf_preparer`, file 61 trang chỉ có ảnh hoặc trống | `mode = PDF`, `pagesRead = 61`, bytes gửi đi đủ 61 trang |
| `pdf_preparer`, file vượt giới hạn trang (hạ tạm cấu hình xuống để test) | Chia file, có lượt riêng cho 5 trang cuối, `chunks` lớn hơn 1 |
| `mapper`, dòng có `schedule` | `valueJson` đúng mảng bậc |
| `mapper`, dòng có `conditionItems` | `condition` là object, `"true"` thành `true`, `"3000000"` thành `3000000` |
| `mapper`, quan hệ có đủ `targetArticle`, `targetClause`, `targetPoint` | `targetScope` đúng. Cả 3 là `null` thì `targetScope` là `null` |
| `post_validator`, `rate = 5` | Đổi thành `0.05`, có cảnh báo |
| `post_validator`, `ruleCode` lạ mà `newCode` là `false` | Bỏ dòng, có cảnh báo |
| `post_validator`, dòng trùng | Giữ dòng `confidence` cao hơn |
| `post_validator`, hai dòng `END` cùng mã, cùng `applyTo`, khác `applyFrom` | Coi là trùng, vì khoá của `END` là `applyTo` |
| `pdf_preparer`, chia file | `page` trong kết quả đã được cộng vị trí trang bắt đầu của cụm |
| Consumer, request thiếu `changesetId` | Không publish gì, chỉ ghi log và ack |
| Consumer, quá `LAW_CHANGESET_TOTAL_DEADLINE_SECONDS` (hạ tạm cấu hình để test) | `FAILED` với `E-AI_MODEL_ERROR` |
| `post_validator`, dòng giống hệt phiên bản hiện tại | Bỏ dòng |
| Consumer, tải file lỗi | Publish đúng 1 message `FAILED` với `E-AI_FILE_DOWNLOAD`, đúng `taskId` và `changesetId`, vào `law.changeset.response.queue` |
| Consumer, `schemaVersion = 2` | `FAILED` với `E-AI_BAD_REQUEST` |
| Consumer, thành công (service bị mock) | 1 message `SUCCESS`, `result` đúng schema hợp đồng |
| Endpoint đồng bộ khi flag tắt | 404 |
| Test cũ của repo | Vẫn pass, không sửa |

### 13.2. Bộ văn bản thật (chạy tay qua endpoint đồng bộ, cần API key)

Chạy lần lượt theo đúng thứ tự demo của hệ thống. Input `currentRules` của mỗi bước là trạng thái sau khi đã merge các bước trước. Người test lấy file PDF chính thức từ vbpl.vn, congbao.chinhphu.vn hoặc vanban.chinhphu.vn.

Cột "Kỳ vọng tối thiểu" là giá trị phải có. Riêng số điều, khoản thì người test đối chiếu với văn bản gốc.

| Bước | Văn bản | Kỳ vọng tối thiểu |
|---|---|---|
| 1 | VBHN 103/VBHN-VPQH (27/8/2025), hợp nhất Luật Thuế TNCN cũ. Base rỗng | `ADD PIT_TAX_SCHEDULE` 7 bậc với ngưỡng năm 60, 120, 216, 384, 624, 960 triệu và thuế suất 5%, 10%, 15%, 20%, 25%, 30%, 35% (Điều 22). `ADD PIT_DEDUCTION_PERSONAL` 9.000.000 (Điều 19). `ADD PIT_DEDUCTION_DEPENDENT` 3.600.000 (Điều 19). `CONSOLIDATES` các luật được hợp nhất nêu ở đầu văn bản, gồm 04/2007/QH12 (`note = "BASE"`), 26/2012/QH13, 71/2014/QH13. `applyFrom` theo chú thích hiệu lực trong văn bản |
| 2 | NQ 954/2020/UBTVQH14 | `UPDATE` bản thân 11.000.000 và người phụ thuộc 4.400.000 (Điều 1), `applyFrom = 2020-01-01` (áp dụng từ kỳ tính thuế 2020). `AMENDS 04/2007/QH12`, phạm vi Điều 19 |
| 3 | TT 111/2013/TT-BTC | `ADD PIT_DEPENDENT_MAX_MONTHLY_INCOME` 1.000.000. `ADD PIT_WITHHOLD_CASUAL_RATE` 0.1 và `ADD PIT_WITHHOLD_CASUAL_MIN_PAYMENT` 2.000.000. **Không** sinh dòng cho mức 9 triệu và 3,6 triệu, vì Thông tư thấp hơn Luật (§6.6) |
| 4 | VBHN 112/VBHN-VPQH (20/5/2026), hợp nhất Luật 109/2025/QH15 và Luật 09/2026/QH16 | `UPDATE PIT_TAX_SCHEDULE` 5 bậc: 120, 360, 720, 1.200 triệu; 5%, 10%, 20%, 30%, 35% (Điều 9). `UPDATE` bản thân 15.500.000 (Điều 10 khoản 1 điểm a) và người phụ thuộc 6.200.000 (điểm b). `applyFrom = 2026-01-01`, `applyBasis` là điều hiệu lực của Luật. `CONSOLIDATES 109/2025/QH15`, `09/2026/QH16`. `REPLACES` luật cũ theo điều hiệu lực |
| 5 | NĐ 253/2026/NĐ-CP (61 trang, bản scan) | Xem §13.3 |
| 6 | TT 87/2026/TT-BTC (30/6/2026) | `UPDATE PIT_DEPENDENT_MAX_MONTHLY_INCOME` 3.000.000, `applyFrom = 2026-01-01`. `REPLACES 111/2013/TT-BTC`. Các quan hệ với 119/2014, 151/2014, 92/2015, 25/2018, 79/2022 đúng như điều khoản thi hành. Không sinh dòng cho mức 15,5 triệu và 6,2 triệu |
| 7 | Luật 09/2026/QH16 (chạy riêng, dùng trạng thái sau bước 4) | 0 dòng thay đổi, vì luật này chỉ sửa khoản 1 Điều 7 về cá nhân kinh doanh. `AMENDS 109/2025/QH15`, phạm vi Điều 7 |

### 13.3. Fixture bước 5: NĐ 253/2026/NĐ-CP

Lưu vào `tests/fixtures/law_changeset/nd253_request_context.json`. `ruleCatalog` lấy toàn bộ bảng §12.

```json
{
  "baseRevision": 4,
  "documentNumberHint": null,
  "sourceUrl": null,
  "currentRules": [
    { "versionId": "00000000-0000-0000-0000-000000000101", "ruleCode": "PIT_TAX_SCHEDULE", "valueKind": "SCHEDULE",
      "valueNumber": null, "valueText": null, "unit": "VND/year", "condition": null, "conditionText": null,
      "valueJson": [ {"toAnnual":60000000,"rate":0.05}, {"toAnnual":120000000,"rate":0.1}, {"toAnnual":216000000,"rate":0.15},
                     {"toAnnual":384000000,"rate":0.2}, {"toAnnual":624000000,"rate":0.25}, {"toAnnual":960000000,"rate":0.3},
                     {"toAnnual":null,"rate":0.35} ],
      "applyFrom": "2009-01-01", "applyTo": "2026-01-01",
      "citation": { "documentNumber": "103/VBHN-VPQH", "article": "22", "clause": null, "point": null, "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000102", "ruleCode": "PIT_TAX_SCHEDULE", "valueKind": "SCHEDULE",
      "valueNumber": null, "valueText": null, "unit": "VND/year", "condition": null, "conditionText": null,
      "valueJson": [ {"toAnnual":120000000,"rate":0.05}, {"toAnnual":360000000,"rate":0.1}, {"toAnnual":720000000,"rate":0.2},
                     {"toAnnual":1200000000,"rate":0.3}, {"toAnnual":null,"rate":0.35} ],
      "applyFrom": "2026-01-01", "applyTo": null,
      "citation": { "documentNumber": "112/VBHN-VPQH", "article": "9", "clause": null, "point": null, "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000201", "ruleCode": "PIT_DEDUCTION_PERSONAL", "valueKind": "AMOUNT",
      "valueNumber": 9000000, "valueJson": null, "valueText": null, "unit": "VND/month", "condition": null, "conditionText": null,
      "applyFrom": "2013-07-01", "applyTo": "2020-01-01",
      "citation": { "documentNumber": "103/VBHN-VPQH", "article": "19", "clause": "1", "point": "a", "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000202", "ruleCode": "PIT_DEDUCTION_PERSONAL", "valueKind": "AMOUNT",
      "valueNumber": 11000000, "valueJson": null, "valueText": null, "unit": "VND/month", "condition": null, "conditionText": null,
      "applyFrom": "2020-01-01", "applyTo": "2026-01-01",
      "citation": { "documentNumber": "954/2020/UBTVQH14", "article": "1", "clause": "1", "point": null, "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000203", "ruleCode": "PIT_DEDUCTION_PERSONAL", "valueKind": "AMOUNT",
      "valueNumber": 15500000, "valueJson": null, "valueText": null, "unit": "VND/month", "condition": null, "conditionText": null,
      "applyFrom": "2026-01-01", "applyTo": null,
      "citation": { "documentNumber": "112/VBHN-VPQH", "article": "10", "clause": "1", "point": "a", "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000301", "ruleCode": "PIT_DEDUCTION_DEPENDENT", "valueKind": "AMOUNT",
      "valueNumber": 3600000, "valueJson": null, "valueText": null, "unit": "VND/person/month", "condition": null, "conditionText": null,
      "applyFrom": "2013-07-01", "applyTo": "2020-01-01",
      "citation": { "documentNumber": "103/VBHN-VPQH", "article": "19", "clause": "1", "point": "b", "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000302", "ruleCode": "PIT_DEDUCTION_DEPENDENT", "valueKind": "AMOUNT",
      "valueNumber": 4400000, "valueJson": null, "valueText": null, "unit": "VND/person/month", "condition": null, "conditionText": null,
      "applyFrom": "2020-01-01", "applyTo": "2026-01-01",
      "citation": { "documentNumber": "954/2020/UBTVQH14", "article": "1", "clause": "2", "point": null, "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000303", "ruleCode": "PIT_DEDUCTION_DEPENDENT", "valueKind": "AMOUNT",
      "valueNumber": 6200000, "valueJson": null, "valueText": null, "unit": "VND/person/month", "condition": null, "conditionText": null,
      "applyFrom": "2026-01-01", "applyTo": null,
      "citation": { "documentNumber": "112/VBHN-VPQH", "article": "10", "clause": "1", "point": "b", "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000401", "ruleCode": "PIT_DEPENDENT_MAX_MONTHLY_INCOME", "valueKind": "AMOUNT",
      "valueNumber": 1000000, "valueJson": null, "valueText": null, "unit": "VND/month", "condition": null, "conditionText": null,
      "applyFrom": "2013-07-01", "applyTo": null,
      "citation": { "documentNumber": "111/2013/TT-BTC", "article": "9", "clause": "1", "point": null, "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000501", "ruleCode": "PIT_WITHHOLD_CASUAL_RATE", "valueKind": "RATE",
      "valueNumber": 0.1, "valueJson": null, "valueText": null, "unit": null, "condition": null, "conditionText": null,
      "applyFrom": "2013-07-01", "applyTo": null,
      "citation": { "documentNumber": "111/2013/TT-BTC", "article": "25", "clause": "1", "point": "i", "page": null } },
    { "versionId": "00000000-0000-0000-0000-000000000502", "ruleCode": "PIT_WITHHOLD_CASUAL_MIN_PAYMENT", "valueKind": "AMOUNT",
      "valueNumber": 2000000, "valueJson": null, "valueText": null, "unit": "VND/payment", "condition": null, "conditionText": null,
      "applyFrom": "2013-07-01", "applyTo": null,
      "citation": { "documentNumber": "111/2013/TT-BTC", "article": "25", "clause": "1", "point": "i", "page": null } }
  ],
  "knownDocuments": [
    { "documentNumber": "103/VBHN-VPQH", "documentType": "VBHN", "title": "Văn bản hợp nhất Luật Thuế thu nhập cá nhân (cũ)", "legalStatus": "HET_HIEU_LUC" },
    { "documentNumber": "04/2007/QH12", "documentType": "LUAT", "title": null, "legalStatus": "HET_HIEU_LUC" },
    { "documentNumber": "954/2020/UBTVQH14", "documentType": "NGHI_QUYET", "title": "Nghị quyết điều chỉnh mức giảm trừ gia cảnh", "legalStatus": "CON_HIEU_LUC" },
    { "documentNumber": "111/2013/TT-BTC", "documentType": "THONG_TU", "title": "Thông tư hướng dẫn Luật Thuế thu nhập cá nhân", "legalStatus": "CON_HIEU_LUC" },
    { "documentNumber": "112/VBHN-VPQH", "documentType": "VBHN", "title": "Văn bản hợp nhất Luật Thuế thu nhập cá nhân", "legalStatus": "CON_HIEU_LUC" },
    { "documentNumber": "109/2025/QH15", "documentType": "LUAT", "title": "Luật Thuế thu nhập cá nhân", "legalStatus": "CON_HIEU_LUC" }
  ]
}
```

Kết quả kỳ vọng khi chạy với file NĐ 253 (61 trang):

**Phải có:**
- `document`:
  - `documentNumber = "253/2026/NĐ-CP"`, `documentType = "NGHI_DINH"`
  - `issuedDate = "2026-06-30"`, `effectiveDate = "2026-07-01"`
- `coverage`: `pagesRead = totalPages = 61`.
- `relations`:
  - `REPLACES 65/2013/NĐ-CP` (Điều 69 khoản 2, trang 57)
  - `REPEALS 91/2014/NĐ-CP`, phạm vi Điều 3 (Điều 69 khoản 3 điểm a)
  - `REPEALS 12/2015/NĐ-CP`, phạm vi Điều 2 (Điều 69 khoản 3 điểm b)
- `operations`:

  | op | ruleCode | Giá trị | Căn cứ (trang) |
  |---|---|---|---|
  | `ADD` | `PIT_DEDUCTION_MEDICAL` | 23.000.000 `VND/year` | 49/2/a (34) |
  | `ADD` | `PIT_DEDUCTION_EDUCATION` | 24.000.000 `VND/year` | 49/2/b (34) |
  | `ADD` | `PIT_DEDUCTION_VOLUNTARY_INSURANCE_CAP` | 3.000.000 `VND/month` | 46/2/a (29) |
  | `UPDATE` | `PIT_WITHHOLD_CASUAL_MIN_PAYMENT` | 5.000.000 `VND/payment` | 50/2 (35) |
  | `RECITE` | `PIT_WITHHOLD_CASUAL_RATE` | giữ 0.1 | 50/2 (35) |
  | `ADD` | `PIT_SETTLEMENT_SELF_REQUIRED_IF_MED_EDU` | FLAG | 51/3 (39) |

  - Y tế và giáo dục có `applyFrom = 2026-01-01` và `applyBasis = 69/1/a`.
  - Hai dòng khấu trừ vãng lai có `applyFrom` là `2026-01-01` hoặc `2026-07-01`, nhưng **bắt buộc** có `applyBasis`.

**Không được có:**
- Dòng nào cho `PIT_TAX_SCHEDULE`, `PIT_DEDUCTION_PERSONAL`, `PIT_DEDUCTION_DEPENDENT`, vì NĐ 253 chỉ dẫn chiếu Điều 9 và Điều 10 của Luật. Những chỗ này nằm ở `references`.
- Dòng nào cho `PIT_DEPENDENT_MAX_MONTHLY_INCOME`, vì NĐ 253 giao Bộ trưởng Bộ Tài chính quy định. Chỗ này nằm ở `warnings`.
- Dòng nào lấy từ phần kinh doanh, đầu tư vốn, chuyển nhượng.

**Có hay không đều được:**
- `ADD PIT_DEPENDENT_GROUPS` (Điều 47 khoản 2–4).
- `ADD` các mã miễn thuế (Điều 26, 27, 29).
- `BASED_ON 109/2025/QH15` và `BASED_ON 09/2026/QH16` (trang 1).

---

## 14. Thứ tự làm và điều kiện hoàn thành

**Thứ tự làm:**
1. `contract.py` và `gemini_output.py`, kèm test cho schema.
2. `pdf_preparer.py`, kèm test.
3. `mapper.py` và `post_validator.py`, kèm test.
4. `law_changeset_prompt.py` (khung ở Phụ lục) và `law_changeset_service.py`.
5. Consumer, producer, cấu hình, đăng ký trong `app/messaging/consumer.py`, kèm test messaging.
6. Endpoint đồng bộ gắn cờ bật tắt. Chạy tay §13.2 và §13.3.

**Điều kiện hoàn thành:**
- **Test:** `pytest` pass toàn bộ, cả test cũ lẫn test mới.
- **Kiểm tay:** chạy fixture §13.3 với file NĐ 253 thật thì đạt đủ mục "Phải có" và không vi phạm mục "Không được có".
- **Hàng đợi:** publish tay một message vào `law.changeset.request.queue` thì nhận đúng một message ở `law.changeset.response.queue`.
- **Không làm hỏng phần cũ:** không thay đổi hành vi của các route và hàng đợi cũ, không có migration mới.
- **Báo cho bên BE** khi xong: commit hoặc nhánh, cách bật endpoint test, và kết quả chạy 7 bước ở §13.2.

---

## Phụ lục: khung prompt (`law_changeset_prompt.py`)

```text
Bạn là chuyên gia pháp chế thuế thu nhập cá nhân Việt Nam. Nhiệm vụ: đọc VĂN BẢN ĐÍNH KÈM và so với LUẬT HỆ THỐNG HIỆN TẠI để
lập BẢN ĐỀ XUẤT THAY ĐỔI. Chỉ trả JSON đúng schema được cấu hình, không kèm lời giải thích.

PHẠM VI: chỉ quy định về thu nhập từ tiền lương, tiền công (cá nhân cư trú và không cư trú). Bỏ qua kinh doanh, đầu tư vốn,
chuyển nhượng vốn, bất động sản, trúng thưởng, bản quyền, nhượng quyền thương mại, thừa kế, quà tặng.

DỮ LIỆU ĐẦU VÀO (JSON):
- currentRules: các phiên bản đang hiệu lực của luật hệ thống, mỗi phiên bản có khoảng áp dụng [applyFrom, applyTo).
- ruleCatalog: danh mục mã luật được phép dùng.
- knownDocuments: các văn bản hệ thống đã biết.
{context_json}

VIỆC PHẢI LÀM:
1. document: số hiệu, loại, cơ quan ban hành, ngày ký (trang đầu), ngày hiệu lực (điều hiệu lực thi hành). Không đọc được thì null.
2. relations: đọc kỹ các ĐIỀU CUỐI (hiệu lực thi hành, điều khoản chuyển tiếp) để lấy REPLACES, REPEALS (kèm phạm vi điều/khoản),
   AMENDS; phần đầu văn bản hợp nhất để lấy CONSOLIDATES (văn bản gốc được hợp nhất ghi note = "BASE");
   đoạn "Căn cứ" để lấy BASED_ON (chỉ văn bản về thuế TNCN).
3. operations: với mỗi quy định do CHÍNH văn bản này đặt ra (mức tiền, thuế suất, ngưỡng, biểu thuế, nhóm người phụ thuộc,
   nghĩa vụ quyết toán):
   a. Ghép vào một ruleCode trong ruleCatalog. Không có mã phù hợp thì newCode=true và điền các trường proposed*.
   b. Xác định applyFrom: văn bản ghi "áp dụng từ kỳ tính thuế năm Y" thì Y-01-01; không có thì ngày hiệu lực của văn bản.
      Luôn điền applyBasis là điều, khoản làm căn cứ cho ngày đó.
   c. So với phiên bản của mã đó đang phủ ngày applyFrom trong currentRules:
      - không có phiên bản: ADD
      - có, giá trị khác: UPDATE
      - giá trị giống, văn bản căn cứ khác, và văn bản này cùng cấp hoặc cao hơn: RECITE
      - các trường hợp còn lại: không sinh dòng.
      Thứ bậc: LUAT > NGHI_QUYET (UBTVQH) > NGHI_DINH > QUYET_DINH > THONG_TU > KHAC. VBHN lấy cấp của văn bản gốc mà nó
      hợp nhất.
   d. END chỉ khi văn bản VIẾT RÕ việc bãi bỏ hoặc chấm dứt một quy định đang có trong currentRules.
4. Số liệu mà văn bản chỉ dẫn chiếu văn bản khác ("theo Điều 9 của Luật …") thì ghi vào references, KHÔNG sinh dòng thay đổi.
   Quy định giao cho cơ quan khác ("do Bộ trưởng Bộ Tài chính quy định") thì ghi vào warnings.
5. Mỗi dòng phải có citation (article, clause, point, page, với page đánh số từ 1 theo file), evidence trích nguyên văn
   tối đa 300 ký tự, confidence từ 0 đến 1, rationale một câu.
6. Số tiền ghi bằng VND (số). Thuế suất ghi số thập phân từ 0 đến 1. Biểu thuế ghi ngưỡng THEO NĂM (toAnnual), bậc cuối null.
7. KHÔNG bịa số liệu, KHÔNG dùng kiến thức bên ngoài để bổ sung những gì văn bản không viết.
```
