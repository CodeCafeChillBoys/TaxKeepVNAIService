# TÀI LIỆU ĐẶC TẢ KỸ THUẬT & KIẾN TRÚC PHÂN HỆ
## MODULE: OCR HÓA ĐƠN CHI PHÍ & HỆ THỐNG QUẢN TRỊ CẤU HÌNH ĐỘNG (EXPENSE OCR PIPELINE & DYNAMIC SYSTEM CONFIGURATIONS)
**Nhánh phát triển:** `feature/implementation_expenseOcrAndSystemConfigs`  
**Dự án:** TaxKeep VN - Dịch vụ Trí tuệ Nhân tạo Hỗ trợ Thuế TNCN (TaxAIService)  
**Ngày hoàn thiện đặc tả:** 20/09/2026  
**Trạng thái:** Sẵn sàng nghiệm thu / Đã kiểm thử & tích hợp hoàn chỉnh với Backend .NET  

---

### MỤC LỤC
1. [TỔNG QUAN BÀI TOÁN & BỐI CẢNH NGHIỆP VỤ (PROBLEM STATEMENT)](#1-tổng-quan-bài-toán--bối-cảnh-nghiệp-vụ)
2. [KIẾN TRÚC TỔNG THỂ & LUỒNG TÍCH HỢP HỆ THỐNG (SYSTEM ARCHITECTURE)](#2-kiến-trúc-tổng-thể--luồng-tích-hợp-hệ-thống)
3. [ĐẶC TẢ PHÂN HỆ OCR HÓA ĐƠN CHI PHÍ (EXPENSE OCR PIPELINE)](#3-đặc-tả-phân-hệ-ocr-hóa-đơn-chi-phí)
4. [CƠ CHẾ BÓC TÁCH BẢNG HÀNG HÓA & BOUNDING BOX (LINE ITEMS & VISUAL BOXES)](#4-cơ-chế-bóc-tách-bảng-hàng-hóa--bounding-box)
5. [HỆ THỐNG QUẢN TRỊ CẤU HÌNH ĐỘNG (DYNAMIC SYSTEM CONFIG SUBSYSTEM)](#5-hệ-thống-quản-trị-cấu-hình-động)
6. [CƠ CHẾ ĐỐI SOÁT NGƯỠNG 3 TẦNG & KIỂM TRA TRƯỜNG CỐT LÕI (CRUCIAL FIELDS)](#6-cơ-chế-đối-soát-ngưỡng-3-tầng--kiểm-tra-trường-cốt-lõi)
7. [THIẾT KẾ CƠ SỞ DỮ LIỆU & LƯU TRỮ VẾT BÓC TÁCH (AUDIT TRAIL PERSISTENCE)](#7-thiết-kế-cơ-sở-dữ-liệu--lưu-trữ-vết-bóc-tách)
8. [ĐẶC TẢ GIAO DIỆN HÀNG ĐỢI RABBITMQ & REST API](#8-đặc-tả-giao-diện-hàng-đợi-rabbitmq--rest-api)
9. [MA TRẬN ĐỐI SOÁT 13 KỊCH BẢN VALIDATION & ĐẶC TẢ LỖI (VALIDATION MATRIX)](#9-ma-trận-đối-soát-13-kịch-bản-validation--đặc-tả-lỗi)
10. [KẾT LUẬN & GIÁ TRỊ ĐÓNG GÓP CHO ĐỒ ÁN CAPSTONE](#10-kết-luận--giá-trị-đóng-góp-cho-đồ-án-capstone)


---

### 1. TỔNG QUAN BÀI TOÁN & BỐI CẢNH NGHIỆP VỤ

#### 1.1. Bối cảnh Nghiệp vụ Kê khai Chi phí Hợp lý
Trong hệ thống Thuế Thu nhập Cá nhân và quản trị tài chính cá nhân TaxKeep VN, người nộp thuế có quyền kê khai các khoản chi phí hợp lý được trừ (hoặc phục vụ quản lý chi tiêu tài chính) như:
* Hóa đơn viện phí, thuốc men, điều trị y tế (`MEDICAL_EXPENSE_INVOICE`).
* Biên lai, hóa đơn học phí của con em hoặc bản thân (`EDUCATION_FEE_INVOICE`).
* Chứng từ đóng góp từ thiện, nhân đạo, khuyến học (`CHARITY_DONATION_RECEIPT`).
* Phí bảo hiểm nhân thọ, bảo hiểm hưu trí tự nguyện (`INSURANCE_PREMIUM_RECEIPT`).

#### 1.2. Những Thách thức Kỹ thuật
1. **Tính đa dạng & không đồng nhất của chứng từ:** Hóa đơn tại Việt Nam lưu hành dưới dạng hóa đơn điện tử (PDF/ảnh), hóa đơn tự in có bảng chi tiết hàng chục dòng thuốc hoặc viện phí, phiếu thu viết tay.
2. **Nguy cơ tài liệu không hợp lệ / rác:** Người dùng có thể vô tình hoặc cố ý tải lên hóa đơn ăn uống, cà phê, vé xem phim, ảnh rác không liên quan đến chi phí được khấu trừ thuế.
3. **Bài toán bảng chi tiết (Line Items):** Cần bóc tách chính xác danh sách chi tiết hàng hóa/dịch vụ (STT, tên mặt hàng, số lượng, đơn vị, đơn giá, thành tiền) thay vì chỉ đọc mỗi tổng số tiền.
4. **Cấu hình tĩnh (Hardcoded Configurations):** Việc quy định ngưỡng tin cậy (threshold) hay danh sách các trường bắt buộc nếu fix cứng trong mã nguồn sẽ khiến hệ thống thiếu linh hoạt khi chính sách hoặc môi trường kiểm soát rủi ro thay đổi.

#### 1.3. Mục tiêu Triển khai trên nhánh `feature/implementation_expenseOcrAndSystemConfigs`
* Xây dựng pipeline OCR tự động phân loại chứng từ theo danh mục động của Admin, bóc tách đầy đủ thông tin hóa đơn và bảng danh mục hàng hóa chi tiết.
* Xây dựng phân hệ quản trị cấu hình hệ thống động (`system_configs`) với khả năng tự suy đoán kiểu dữ liệu, hỗ trợ Soft Delete và API quản trị thời gian thực.
* Thiết lập cơ chế thẩm định ngưỡng tin cậy 3 tầng linh hoạt kết hợp cơ chế bảo vệ trường cốt lõi (`crucial_fields`).
* Lưu trữ toàn vẹn vết bóc tách (Audit Trail) xuống CSDL gồm bảng cha `ai_extractions` và bảng con `ai_extractions_value` phục vụ đối soát và hiệu chỉnh Human-in-the-loop.

---

### 2. KIẾN TRÚC TỔNG THỂ & LUỒNG TÍCH HỢP HỆ THỐNG

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TaxKeepVN Core (.NET BE)                         │
│                                                                         │
│  [Expense Controller] ──► [RabbitMQ Publisher]                         │
│                           - Queue: `expense.ocr.ai.request.queue`       │
│                           - Đính kèm: Categories, targetYear, fileUrl   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TaxAIService (Python)                           │
│                                                                         │
│  [Expense Consumer Worker]                                              │
│  - Tải file từ Cloud/Base64 qua httpx                                   │
│  - Phân tích định dạng MIME                                             │
│                                    │                                    │
│                                    ▼                                    │
│  [ExpenseOcrService] ◄──── [SystemConfigRepository]                     │
│  - Dynamic Prompt Generation       - Đọc THRESHOLD_<CATEGORY>           │
│  - Gemini Multimodal Vision        - Đọc AI_CONFIDENCE_THRESHOLD        │
│  - Structured JSON Output          - Đọc CRUCIAL_FIELDS_<CATEGORY>      │
│                                    │                                    │
│                                    ▼                                    │
│  [Validation & Threshold Engine]                                        │
│  - Kiểm tra docTypeCode vs Categories (Reject if UNSUPPORTED)           │
│  - Kiểm tra extractedYear == targetYear                                 │
│  - Tính overall_confidence & rà soát crucial_fields                     │
│                                    │                                    │
│                                    ▼                                    │
│  [ExpenseOcrRepository] ──► [PostgreSQL: ai_extractions & value]        │
│  - Lưu toàn bộ kết quả bóc tách, bounding box, confidence scores        │
│                                    │                                    │
│                                    ▼                                    │
│  [RabbitMQ Producer] ──────► `expense.ocr.ai.response.queue`            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 3. ĐẶC TẢ PHÂN HỆ OCR HÓA ĐƠN CHI PHÍ

#### 3.1. Phân loại Động theo Danh mục của Admin (Dynamic Classification)
Không giới hạn cố định loại chứng từ, Backend .NET truyền danh sách danh mục hiện hành (`AdminCategoryItem`) sang AI:
```python
def build_expense_ocr_prompt(categories: list[AdminCategoryItem]) -> str:
    cat_text = "\n".join([
        f"- Mã '{c.code}': {c.name}. Đặc điểm nhận diện: {c.description}"
        for c in categories
    ])
```
* **Mã `UNSUPPORTED`:** Nếu tài liệu là hóa đơn ăn uống, cà phê, vé xem phim hoặc ảnh rác, AI tự động gán `docTypeCode = "UNSUPPORTED"` kèm lý do chi tiết tại `classificationReason`.

#### 3.2. Cấu trúc Dữ liệu Bóc tách Tổng quát (`GeminiOcrOutput`)
1. **Thông tin Bên bán (Bệnh viện / Cơ sở đào tạo / Nhà cung cấp):**
   * `sellerName`: Tên đơn vị phát hành hóa đơn.
   * `sellerTaxCode`: Mã số thuế bên bán (rất quan trọng để tra cứu tính hợp lệ).
   * `sellerAddress`, `sellerPhone`.
2. **Thông tin Hóa đơn & Tra cứu:**
   * `invoiceSeries`: Ký hiệu mẫu hóa đơn (ví dụ: `2C26TBH`).
   * `invoiceNumber`: Số hóa đơn (ví dụ: `82621`).
   * `invoiceDate`: Ngày lập hóa đơn dạng `YYYY-MM-DD`.
   * `extractedYear`: Năm trích xuất từ ngày lập (dùng để đối soát với năm quyết toán).
   * `lookupUrl`, `lookupCode`: Đường dẫn và mã tra cứu hóa đơn điện tử.
3. **Thông tin Bên mua (Bệnh nhân / Học sinh / Người nộp thuế):**
   * `buyerName`: Họ tên người mua / bệnh nhân / học sinh.
   * `buyerIdCard`: Số CCCD/CMND.
   * `buyerAddress`, `buyerTaxCode`, `paymentMethod`.
4. **Thông tin Tài chính:**
   * `totalAmount`: Tổng số tiền thanh toán dạng số thực (`float`).
   * `totalAmountInWords`: Số tiền viết bằng chữ.

---

### 4. CƠ CHẾ BÓC TÁCH BẢNG HÀNG HÓA & BOUNDING BOX

#### 4.1. Bóc tách Bảng Chi tiết Hàng hóa / Viện phí (`InvoiceLineItem`)
Phân hệ trích xuất toàn bộ bảng dịch vụ vào mảng `items`:
```json
{
  "items": [
    {
      "itemOrder": 1,
      "itemName": "Khám chuyên khoa Nhi",
      "unit": "Lần",
      "quantity": 1.0,
      "unitPrice": 250000.0,
      "totalPrice": 250000.0
    },
    {
      "itemOrder": 2,
      "itemName": "Thuốc Amoxicillin 500mg",
      "unit": "Hộp",
      "quantity": 2.0,
      "unitPrice": 85000.0,
      "totalPrice": 170000.0
    }
  ]
}
```

#### 4.2. Tọa độ Trực quan (Bounding Box) & Điểm Tin cậy Trường
Để hỗ trợ giao diện Frontend vẽ khung sáng làm nổi bật vị trí chữ được đọc trên hóa đơn, mỗi trường trong danh sách `fields` trả về:
* `fieldName`: Tên trường dữ liệu.
* `extractedValue`: Giá trị văn bản đọc được.
* `confidenceScore`: Độ tin cậy ($0.0 \rightarrow 1.0$).
* `boundingBox`: Tọa độ hình chữ nhật `{"x": int, "y": int, "w": int, "h": int}` trên ảnh gốc.

---

### 5. HỆ THỐNG QUẢN TRỊ CẤU HÌNH ĐỘNG (DYNAMIC SYSTEM CONFIG SUBSYSTEM)

#### 5.1. Mô hình Dữ liệu Bảng `system_configs`
```mermaid
classDiagram
    class SystemConfig {
        +string config_key PK
        +string config_value
        +string data_type
        +string description
        +UUID admin_id
        +boolean is_active
        +boolean is_deleted
        +datetime deleted_at
        +datetime created_at
        +datetime updated_at
    }
```

#### 5.2. Thuật toán Tự động Suy đoán Kiểu Dữ liệu (`_detect_data_type`)
Admin có thể tạo cấu hình mới mà không cần chọn thủ công kiểu dữ liệu; hệ thống tự động suy đoán:
* `true`, `false` $\rightarrow$ `ConfigDataType.BOOLEAN`.
* Số nguyên nguyên thủy $\rightarrow$ `ConfigDataType.INT`.
* Số có phần thập phân (`0.85` hoặc `0,85`) $\rightarrow$ `ConfigDataType.FLOAT` (tự động chuẩn hóa dấu phẩy thành dấu chấm).
* Chuỗi bắt đầu và kết thúc bằng `{...}` hoặc `[...]` $\rightarrow$ `ConfigDataType.JSON`.
* Chuỗi chứa dấu phẩy $\rightarrow$ `ConfigDataType.LIST_STRING`.
* Còn lại $\rightarrow$ `ConfigDataType.STRING`.

#### 5.3. Cơ chế Xóa mềm (Soft Delete)
Khi Admin xóa cấu hình qua `DELETE /api/system-configs/{key}`, hệ thống không xóa vật lý mà cập nhật `is_deleted = True` và `deleted_at = func.now()`. Điều này đảm bảo tính toàn vẹn dữ liệu cho các lần bóc tách lịch sử.

---

### 6. CƠ CHẾ ĐỐI SOÁT NGƯỠNG 3 TẦNG & KIỂM TRA TRƯỜNG CỐT LÕI

#### 6.1. Quy trình Phân giải Ngưỡng Tin cậy (Threshold Resolution)
Ngưỡng tin cậy áp dụng (`applied_threshold`) được phân giải tự động theo 3 tầng:
1. **Tầng 1 (Ngưỡng riêng theo danh mục):** Ví dụ Admin cấu hình `THRESHOLD_MEDICAL_EXPENSE_INVOICE = 0.85`. Khi xử lý hóa đơn y tế, hệ thống ưu tiên áp dụng ngưỡng này.
2. **Tầng 2 (Ngưỡng chung toàn hệ thống):** Nếu danh mục không có ngưỡng riêng, hệ thống đọc khóa `AI_CONFIDENCE_THRESHOLD`.
3. **Tầng 3 (Mặc định dự phòng):** Nếu không tìm thấy khóa nào trong CSDL, hệ thống sử dụng giá trị an toàn `0.80`.

#### 6.2. Thuật toán Tính Điểm Tin cậy Tổng thể (`overall_confidence`)
$$\text{Overall Confidence} = \text{round}\left(\frac{\sum_{i=1}^{M} \text{FieldConfidence}_i}{M}, 2\right)$$
*(Với $M$ là tổng số lượng các trường dữ liệu bóc tách được trong mảng `fields`).*

#### 6.3. Cơ chế Bảo vệ Trường Cốt lõi (Crucial Fields Enforcement)
* Hệ thống truy vấn danh sách trường cốt lõi từ khóa `CRUCIAL_FIELDS_<CATEGORY>` hoặc `CRUCIAL_EXTRACTION_FIELDS` (mặc định gồm: `total_amount`, `seller_tax_code`, `buyer_id_card`, `invoice_number`).
* **Quy tắc an toàn nghiêm ngặt:** Kể cả khi `overall_confidence >= applied_threshold`, nhưng nếu **chỉ cần 1 trường cốt lõi** có `confidenceScore < applied_threshold`:
  $$\text{has\_crucial\_low\_confidence} = \text{True} \implies \text{is\_passed\_threshold} = \text{False}$$
* Hệ thống lập tức đánh dấu không đạt ngưỡng và yêu cầu xác nhận thủ công (Human-in-the-loop) để ngăn chặn rủi ro gian lận tiền thuế hoặc sai lệch mã số thuế.

---

### 7. THIẾT KẾ CƠ SỞ DỮ LIỆU & LƯU TRỮ VẾT BÓC TÁCH

#### 7.1. Sơ đồ Thực thể Quan hệ (ERD)

```mermaid
erDiagram
    SYSTEM_CONFIGS
    AI_EXTRACTIONS ||--o{ AI_EXTRACTIONS_VALUE : "chứa chi tiết (cascade delete)"

    SYSTEM_CONFIGS {
        string config_key PK
        string config_value
        string data_type
        string description
        uuid admin_id
        boolean is_active
        boolean is_deleted
        datetime deleted_at
        datetime created_at
        datetime updated_at
    }

    AI_EXTRACTIONS {
        uuid id PK
        uuid document_id
        numeric overall_confidence
        numeric applied_threshold
        boolean is_passed_threshold
        jsonb raw_payload
        datetime created_at
    }

    AI_EXTRACTIONS_VALUE {
        bigint id PK
        uuid extraction_id FK
        string field_name
        text extracted_value
        text user_corrected_value
        numeric confidence_score
        jsonb bounding_box
    }
```

#### 7.2. Ý nghĩa Kiến trúc của 2 Bảng `ai_extractions` & `ai_extractions_value`
* **`ai_extractions` (Bảng cha):** Lưu vết tổng thể của phiên bóc tách: ID tài liệu, điểm tổng quan, ngưỡng áp dụng, cờ đạt ngưỡng và toàn bộ JSON thô do Gemini sinh ra (`raw_payload`).
* **`ai_extractions_value` (Bảng con):** Lưu chi tiết từng trường bóc tách, tọa độ Bounding Box, điểm tin cậy và đặc biệt là cột `user_corrected_value`. Khi người dùng sửa lại thông tin sai trên giao diện, giá trị mới được lưu vào cột này, tạo tập dữ liệu quý giá phục vụ đánh giá mô hình và fine-tuning trong tương lai.

---

### 8. ĐẶC TẢ GIAO DIỆN HÀNG ĐỢI RABBITMQ & REST API

#### 8.1. Hàng đợi RabbitMQ (`expense.ocr.ai.request.queue` & `response.queue`)

##### Request Message từ Backend .NET:
```json
{
  "taskId": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "periodId": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
  "userId": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
  "targetYear": 2026,
  "fileUrl": "https://storage.taxkeep.vn/expenses/vienphi_2026.jpg",
  "originalFilename": "vienphi_2026.jpg",
  "categories": [
    {
      "code": "MEDICAL_EXPENSE_INVOICE",
      "name": "Hóa đơn viện phí y tế",
      "description": "Hóa đơn khám chữa bệnh, viện phí, tiền thuốc tại bệnh viện/phòng khám"
    }
  ],
  "appliedThreshold": 0.85
}
```

##### Response Message trả về Backend .NET:
```json
{
  "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "periodId": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
  "userId": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
  "docTypeCode": "MEDICAL_EXPENSE_INVOICE",
  "fileUrl": "https://storage.taxkeep.vn/expenses/vienphi_2026.jpg",
  "originalFilename": "vienphi_2026.jpg",
  "invoiceSeries": "2C26TBH",
  "invoiceNumber": "0082621",
  "invoiceDate": "2026-03-15",
  "extractedYear": 2026,
  "sellerName": "BỆNH VIỆN ĐẠI HỌC Y DƯỢC TP.HCM",
  "sellerTaxCode": "0302221111",
  "buyerName": "NGUYỄN VĂN AN",
  "totalAmount": 1250000.0,
  "totalAmountInWords": "Một triệu hai trăm năm mươi nghìn đồng",
  "items": [
    {
      "itemOrder": 1,
      "itemName": "Khám bệnh chuyên khoa",
      "unit": "Lần",
      "quantity": 1.0,
      "unitPrice": 250000.0,
      "totalPrice": 250000.0
    }
  ],
  "validationStatus": {
    "isYearValid": true,
    "isDocTypeValid": true,
    "isIdentityValid": true
  },
  "validationErrors": [],
  "status": "EXTRACTED",
  "createdAt": "2026-09-20T15:30:00Z"
}
```

#### 8.2. RESTful API Quản trị Cấu hình Hệ thống (`/api/system-configs`)

| STT | Phương thức | Endpoint | Mô tả | Quyền |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `GET` | `/api/system-configs` | Lấy danh sách cấu hình hệ thống (hỗ trợ lọc `active_only`) | Admin |
| 2 | `POST` | `/api/system-configs` | Tạo cấu hình / ngưỡng mới (tự suy đoán kiểu dữ liệu) | Admin |
| 3 | `GET` | `/api/system-configs/{key}` | Xem chi tiết cấu hình theo khóa | Admin |
| 4 | `PUT` | `/api/system-configs/{key}` | Cập nhật giá trị, kiểu dữ liệu hoặc bật/tắt cấu hình | Admin |
| 5 | `DELETE` | `/api/system-configs/{key}` | Xóa mềm cấu hình hệ thống | Admin |
| 6 | `GET` | `/api/system-configs/threshold/test-resolve` | Kiểm tra trực quan xem danh mục cụ thể sẽ áp dụng ngưỡng nào | Admin/Tester |

---

### 9. MA TRẬN ĐỐI SOÁT 13 KỊCH BẢN VALIDATION & ĐẶC TẢ LỖI (VALIDATION MATRIX)

Phân hệ xử lý dữ liệu và phân loại chứng từ thuế tích hợp chặt chẽ giữa **AI Service (Python/Gemini)** và **Backend Core (.NET)**. Dưới đây là bảng ma trận đối soát chi tiết 13 kịch bản lỗi, phân định rõ trách nhiệm xử lý và hiện trạng hoàn thành tính đến thời điểm hiện tại:

| STT | Mã HTTP & Tên Kịch bản Nghiệp vụ | Phân tầng Phụ trách | Trạng thái Triển khai | Mã Lỗi (Error Code) |
| :---: | :--- | :---: | :---: | :---: |
| **1** | **404:** Document không tồn tại hoặc không thuộc user | **Backend .NET** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_DOCUMENT_NOT_FOUND` |
| **2** | **400:** Document không ở trạng thái hợp lệ (`UPLOADED`) | **Backend .NET** | ❌ **CÒN THIẾU (PENDING)** | `ERR_INVALID_STATUS` |
| **3** | **422:** File hỏng / AI không thể mở hoặc parse dữ liệu | **AI Service** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_CORRUPTED_FILE` / `ERR_UNREADABLE_IMAGE` |
| **4** | **401:** Token không hợp lệ, thiếu hoặc hết hạn | **Backend .NET** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_UNAUTHORIZED` |
| **5** | **422:** Năm trên hóa đơn không khớp năm kê khai thuế | **AI Service & BE** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_YEAR_MISMATCH` |
| **6** | **422:** Loại chứng từ không đủ điều kiện giảm trừ thuế | **AI Service & BE** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_INVALID_DOC_TYPE` |
| **7** | **422:** Danh tính người mua không khớp NNT hoặc thân nhân | **BE .NET & AI** | ❌ **CÒN THIẾU (PENDING)** | `ERR_IDENTITY_MISMATCH` |
| **8** | **403:** Kỳ kê khai thuế đã nộp và bị khóa (`SUBMITTED`) | **Backend .NET** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_TAX_PERIOD_LOCKED` |
| **9** | **422:** Chất lượng ảnh thấp dưới ngưỡng quy định | **AI Service** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_IMAGE_QUALITY_TOO_LOW` |
| **10** | **422:** Tệp tin không phải là chứng từ thuế hợp lệ | **AI Service** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_NOT_TAX_DOCUMENT` |
| **11** | **409:** Trùng số hóa đơn & MST người bán trong cùng kỳ | **Backend .NET** | ❌ **CÒN THIẾU (PENDING)** | `ERR_DUPLICATE_DOCUMENT` |
| **12** | **422:** Ngày lập hóa đơn không được ở tương lai | **AI Service & BE** | ✅ **ĐÃ HOÀN THÀNH** | `ERR_FUTURE_DATE` |
| **13** | **409:** Trùng mã băm SHA-256 nội dung file nhị phân | **Backend .NET** | ❌ **CÒN THIẾU (PENDING)** | `ERR_DUPLICATE_FILE_HASH` |

---

#### 9.1. Chi tiết các Kịch bản ĐÃ HOÀN THÀNH (100% Implemented)

##### 1. Kịch bản 3: Tệp tin bị hỏng hoặc AI không thể đọc dữ liệu (HTTP 422)
* **Vị trí xử lý:** `app/errors/expense_ocr_errors.py` & `app/services/expense_ocr/expense_ocr_service.py`.
* **Cơ chế:** Phân tách tách bạch giữa lỗi tệp tin hỏng (`CorruptedFileError`) khi giải mã Base64/tải URL thất bại hoặc rỗng bytes, với lỗi ảnh mờ/lóa sáng không nhận diện được chữ (`UnreadableDocumentError`).
* **Response Payload:**
```json
{
  "statusCode": 422,
  "message": "AI Engine could not parse the document. The image quality may be too blurry or illegible.",
  "errors": [
    {
      "code": "ERR_UNREADABLE_IMAGE",
      "field": "file",
      "message": "AI Engine could not parse the document. The image quality may be too blurry or illegible."
    }
  ]
}
```

##### 2. Kịch bản 5: Năm trên hóa đơn không khớp năm kê khai thuế (HTTP 422)
* **Vị trí xử lý:** `app/services/expense_ocr/expense_ocr_service.py` & `expense_consumer.py`.
* **Cơ chế:** AI trích xuất `extractedYear` từ `invoiceDate` và so sánh với `targetYear`. Nếu lệch, gán mã lỗi chuẩn `ERR_YEAR_MISMATCH`.
* **Response Payload:**
```json
{
  "statusCode": 422,
  "message": "Validation failed: Document date does not match the active filing tax year.",
  "errors": [
    {
      "code": "ERR_YEAR_MISMATCH",
      "field": "extractedYear",
      "message": "Document is dated in 2025 but filing year is 2026."
    }
  ]
}
```

##### 3. Kịch bản 6: Loại chứng từ không thuộc danh mục giảm trừ thuế (HTTP 422)
* **Vị trí xử lý:** `app/services/expense_ocr/expense_ocr_service.py`.
* **Cơ chế:** Khi hóa đơn là hóa đơn tài chính thật nhưng thuộc mục cà phê, ăn uống, xem phim... AI gán `isTaxDocument = True` và `docTypeCode = 'UNSUPPORTED'`, sinh mã lỗi chuẩn `ERR_INVALID_DOC_TYPE`.
* **Response Payload:**
```json
{
  "statusCode": 422,
  "message": "Validation failed: Document type is not eligible for Personal Income Tax deductions.",
  "errors": [
    {
      "code": "ERR_INVALID_DOC_TYPE",
      "field": "docTypeCode",
      "message": "This document category does not qualify for tax relief or deductions."
    }
  ]
}
```

##### 4. Kịch bản 9: Điểm chất lượng ảnh thấp hơn ngưỡng (HTTP 422)
* **Vị trí xử lý:** `app/schemas/expense_ocr/expense_ocr_schema.py` & `app/prompts/expense_ocr/expense_orc_promt.py`.
* **Cơ chế:** AI trực tiếp quan sát và đánh giá khuyết tật quang học trên ảnh (`qualityIssues`), trả về danh sách lý do cụ thể (`IMAGE_BLURRY`, `EXCESSIVE_GLARE`, `CROPPED_EDGES`, `LOW_RESOLUTION`).
* **Response Payload:**
```json
{
  "statusCode": 422,
  "message": "Image quality is too low for accurate tax document extraction. Please capture or upload a clearer document.",
  "errors": [
    {
      "code": "ERR_IMAGE_QUALITY_TOO_LOW",
      "field": "file",
      "qualityScore": 0.52,
      "requiredThreshold": 0.75,
      "reasons": ["IMAGE_BLURRY", "EXCESSIVE_GLARE"]
    }
  ]
}
```

##### 5. Kịch bản 10: Tệp tin không phải chứng từ thuế hợp lệ (HTTP 422)
* **Vị trí xử lý:** `app/prompts/expense_ocr/expense_orc_promt.py` & `expense_ocr_service.py`.
* **Cơ chế:** Phân định dứt khoát giữa hóa đơn không giảm trừ với tệp tin rác (ảnh selfie, phong cảnh, động vật, meme). Khi phát hiện tệp tin rác, AI gán `isTaxDocument = False` và ném mã lỗi `ERR_NOT_TAX_DOCUMENT`.
* **Response Payload:**
```json
{
  "statusCode": 422,
  "message": "Uploaded file is not recognized as a valid tax document.",
  "errors": [
    {
      "code": "ERR_NOT_TAX_DOCUMENT",
      "field": "file",
      "message": "Uploaded file is not recognized as a valid tax document."
    }
  ]
}
```

##### 6. Kịch bản 12: Ngày hóa đơn không được ở tương lai (HTTP 422)
* **Vị trí xử lý:** `app/services/expense_ocr/expense_ocr_service.py`.
* **Cơ chế:** So sánh `inv_date = datetime.strptime(invoiceDate, "%Y-%m-%d").date()` với `today_utc = datetime.now(timezone.utc).date()`. Nếu `inv_date > today_utc`, sinh mã lỗi `ERR_FUTURE_DATE`.
* **Response Payload:**
```json
{
  "statusCode": 422,
  "message": "Invoice date cannot be greater than the current date.",
  "errors": [
    {
      "code": "ERR_FUTURE_DATE",
      "field": "invoiceDate",
      "message": "Invoice date cannot be greater than the current date."
    }
  ]
}
```

##### 7. Kịch bản 1, 4, 8: Các ràng buộc bảo mật & kỳ tính thuế phía Backend .NET
* **404 Document not found:** Đã có trong `TaxPeriodService.ConfirmDocumentReviewAsync` (kiểm tra `document == null || document.Period.UserId != userId`).
* **401 Unauthorized:** Đã có qua JWT Bearer Middleware (`[Authorize]`).
* **403 Tax Period Locked:** Đã có trong `TaxPeriodService.InitOrGetPeriodAsync` và `BatchUploadDocumentsAsync` (kiểm tra `TaxPeriodStatus.SUBMITTED`).

---

#### 9.2. Chi tiết các Kịch bản CÒN THIẾU (Pending Implementation)

##### 1. Kịch bản 2: Document không ở trạng thái hợp lệ (HTTP 400)
* **Phân tầng:** Backend Core (.NET API).
* **Mô tả:** Khi một chứng từ đã được AI bóc tách xong (`Status = EXTRACTED`) hoặc người dùng đã xác nhận (`Status = CONFIRMED`), nếu người dùng hoặc client gửi lệnh trigger bóc tách lại hoặc tải đè, hệ thống phải chặn lại.
* **Cần bổ sung tại .NET:** Trong `DocumentService` hoặc `TaxPeriodService`, kiểm tra:
  ```csharp
  if (document.Status != "UPLOADED")
  {
      throw new BadRequestException(ErrorCodes.InvalidDocumentStatus, 
          "Document has already been extracted or verified.");
  }
  ```

##### 2. Kịch bản 7: Danh tính người mua không khớp NNT hoặc người phụ thuộc (HTTP 422)
* **Phân tầng:** Tích hợp giữa BE .NET & AI Service.
* **Mô tả:** Trên hóa đơn viện phí / học phí, thông tin người mua / bệnh nhân (`buyerIdCard` hoặc `buyerName`) bắt buộc phải trùng khớp với Căn cước công dân / Họ tên của chính người nộp thuế HOẶC một trong các người phụ thuộc đã đăng ký trong kỳ.
* **Hiện trạng & Cần bổ sung:** 
  * Hiện tại trong `expense_consumer.py`, cờ `isIdentityValid` đang được gán mặc định `True`.
  * **Cần bổ sung:** Phía .NET Backend khi gửi message vào `expense.ocr.ai.request.queue` cần đính kèm thông tin: `taxpayerProfile: { idCard, fullName }` và danh sách `dependents: [{ idCard, fullName }]`. Sau đó AI Service hoặc BE .NET thực hiện so khớp chéo chuỗi định danh.

##### 3. Kịch bản 11: Trùng số hóa đơn & MST người bán trong cùng kỳ tính thuế (HTTP 409)
* **Phân tầng:** Backend Core (.NET API & Database).
* **Mô tả:** Trong cùng một kỳ tính thuế (`periodId`), không được phép tồn tại 2 chứng từ có cùng cặp `(sellerTaxCode, invoiceNumber)`.
* **Cần bổ sung tại .NET:** Trong `ConfirmDocumentReviewAsync`:
  ```csharp
  var duplicate = await docRepo.FindAsync(d => 
      d.PeriodId == periodId &&
      d.Id != documentId &&
      d.SellerTaxCode == dto.SellerTaxCode && 
      d.InvoiceNumber == dto.InvoiceNumber);
  if (duplicate.Any())
  {
      throw new ConflictException(ErrorCodes.DuplicateDocument, 
          $"Duplicate document: Invoice number {dto.InvoiceNumber} from seller {dto.SellerTaxCode} already exists.");
  }
  ```

##### 4. Kịch bản 13: Trùng mã băm SHA-256 nội dung file nhị phân (HTTP 409)
* **Phân tầng:** Backend Core (.NET API - Tầng Upload).
* **Mô tả:** Khi người nộp thuế upload nhiều hóa đơn, nếu vô tình chọn lại đúng file ảnh/PDF đã upload trước đó trong cùng kỳ, hệ thống phát hiện trùng mã băm SHA-256 nhị phân và từ chối ngay lập tức tại cổng upload.
* **Cần bổ sung tại .NET:** Thêm cột `FileHash` (String 64) vào bảng `documents`. Khi xử lý `IFormFile`:
  ```csharp
  using var sha256 = SHA256.Create();
  using var stream = file.OpenReadStream();
  var hashBytes = await sha256.ComputeHashAsync(stream);
  var fileHash = Convert.ToHexString(hashBytes).ToLowerInvariant();

  var isDuplicate = (await docRepo.FindAsync(d => d.PeriodId == periodId && d.FileHash == fileHash)).Any();
  if (isDuplicate)
  {
      throw new ConflictException("ERR_DUPLICATE_FILE_HASH",
          "Duplicate file detected: An identical file has already been uploaded in this tax filing period.");
  }
  ```

---

### 10. KẾT LUẬN & GIÁ TRỊ ĐÓNG GÓP CHO ĐỒ ÁN CAPSTONE

1. **Khả năng thương mại hóa cao:** Phân hệ xử lý trọn vẹn bài toán bóc tách hóa đơn tài chính phức tạp, bao gồm cả các bảng kê hàng hóa nhiều dòng, tự động phân định rạch ròi giữa hóa đơn không đủ điều kiện thuế (`UNSUPPORTED`) và ảnh rác không phải chứng từ thuế (`NOT_TAX_DOCUMENT`).
2. **Kiến trúc phần mềm linh hoạt (Zero Hardcode):** Toàn bộ ngưỡng tin cậy, quy tắc trường cốt lõi và danh mục chứng từ đều được điều khiển động từ CSDL qua hệ thống `system_configs`.
3. **Quản trị rủi ro & An toàn dữ liệu tài chính:** Mô hình kết hợp giữa điểm tin cậy tổng thể, kiểm soát trường cốt lõi và phát hiện lỗi quang học trực quan (`IMAGE_BLURRY`, `EXCESSIVE_GLARE`) tạo tiền đề vững chắc cho quy trình kiểm toán và hậu kiểm của cơ quan thuế.

