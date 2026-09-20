# TÀI LIỆU ĐẶC TẢ KỸ THUẬT & KIẾN TRÚC PHÂN HỆ
## MODULE: OCR GIẤY TỜ NGƯỜI PHỤ THUỘC & CƠ CHẾ ĐỐI SOÁT NGƯỠNG ĐỘNG (DEPENDENT DOCUMENT OCR & DYNAMIC THRESHOLD VALIDATION)
**Nhánh phát triển:** `feature/implementation_DependentDocumentOcr`  
**Dự án:** TaxKeep VN - Dịch vụ Trí tuệ Nhân tạo Hỗ trợ Thuế TNCN (TaxAIService)  
**Ngày Bắt Đầu đặc tả:** 15/09/2026  
**Ngày hoàn thiện đặc tả:** 20/09/2026  
**Trạng thái:** Sẵn sàng nghiệm thu / Đã kiểm thử & tích hợp với Backend .NET  

---

### MỤC LỤC
1. [TỔNG QUAN BÀI TOÁN & BỐI CẢNH (PROBLEM STATEMENT)](#1-tổng-quan-bài-toán--bối-cảnh)
2. [KIẾN TRÚC TÍCH HỢP HỆ THỐNG (SYSTEM INTEGRATION ARCHITECTURE)](#2-kiến-trúc-tích-hợp-hệ-thống)
3. [ĐẶC TẢ CHI TIẾT TÍNH NĂNG OCR GIẤY TỜ (OCR ENGINE SPECIFICATION)](#3-đặc-tả-chi-tiết-tính-năng-ocr-giấy-tờ)
4. [CƠ CHẾ BÓC TÁCH & ĐỐI SOÁT NGƯỠNG ĐỘNG (DYNAMIC THRESHOLD VALIDATION)](#4-cơ-chế-bóc-tách--đối-soát-ngưỡng-động)
5. [CƠ CHẾ THẨM ĐỊNH QUY TẮC ĐỘNG TỪ ADMIN (DYNAMIC RULE COMPLIANCE)](#5-cơ-chế-thẩm-định-quy-tắc-động-từ-admin)
6. [HỆ THỐNG QUẢN LÝ CẤU HÌNH HỆ THỐNG ĐỘNG (SYSTEM CONFIG SUBSYSTEM)](#6-hệ-thống-quản-lý-cấu-hình-hệ-thống-động)
7. [ĐẶC TẢ GIAO DIỆN HÀNG ĐỢI RABBITMQ & REST API](#7-đặc-tả-giao-diện-hàng-đợi-rabbitmq--rest-api)
8. [QUY TRÌNH KIỂM SOÁT ẢO GIÁC & AN TOÀN DỮ LIỆU (ANTI-HALLUCINATION)](#8-quy-trình-kiểm-soát-ảo-giác--an-toàn-dữ-liệu)
9. [KẾT LUẬN & Ý NGHĨA KỸ THUẬT ĐỐI VỚI ĐỒ ÁN](#9-kết-luận--ý-nghĩa-kỹ-thuật)

---

### 1. TỔNG QUAN BÀI TOÁN & BỐI CẢNH

#### 1.1. Thách thức trong Đăng ký Giảm trừ Gia cảnh Thuế TNCN
Khi người nộp thuế (Taxpayer) đăng ký người phụ thuộc để được giảm trừ thuế TNCN, họ bắt buộc phải cung cấp hồ sơ chứng minh quan hệ và điều kiện hợp pháp theo Thông tư 111/2013/TT-BTC:
* **Con chưa thành niên / thành niên:** Căn cước công dân (CCCD), Giấy khai sinh, Thẻ sinh viên hoặc Giấy xác nhận của trường đại học.
* **Người thân khuyết tật / không có khả năng lao động:** Giấy xác nhận khuyết tật, Giấy ra viện/hồ sơ bệnh án.
* **Cha mẹ / Vợ chồng:** CCCD, Giấy chứng nhận kết hôn, Giấy xác nhận cư trú CT07, Bản cam kết nghĩa vụ nuôi dưỡng Mẫu 07/XN-NPT.

#### 1.2. Hạn chế của phương pháp truyền thống
1. **OCR truyền thống (Tesseract / EasyOCR):** Nhận diện ký tự quang học thô thường xuyên bị lỗi khi ảnh chụp xiên, bóng đổ, lóa đèn flash trên thẻ nhựa CCCD; không có khả năng hiểu ngữ nghĩa của văn bản hành chính Việt Nam.
2. **Hardcode ngưỡng phê duyệt:** Đa phần hệ thống lập trình cứng một con số (ví dụ: confidence > 0.8 thì nhận, dưới thì từ chối). Điều này khiến hệ thống mất linh hoạt khi chính sách hoặc môi trường thực tế thay đổi.
3. **Thiếu đánh giá chi tiết từng trường (Field-level Confidence):** Nếu một ảnh chụp rất nét toàn bộ nhưng duy nhất số CCCD bị lóa sáng, nếu chỉ có điểm tổng quan (Overall Score) thì hệ thống có thể bỏ lọt lỗi nghiêm trọng này.

#### 1.3. Mục tiêu phân hệ trên nhánh `feature/implementation_DependentDocumentOcr`
Xây dựng pipeline OCR thông minh sử dụng **Gemini Multimodal Vision** kết hợp với **Hệ thống đối soát ngưỡng động (Dynamic Threshold Evaluation)** lấy trực tiếp từ Database, cho phép:
* Phía Backend Core (.NET) gửi ảnh (1 ảnh hoặc 2 ảnh mặt trước/mặt sau) sang qua RabbitMQ / REST API.
* AI bóc tách toàn bộ thông tin định danh và đánh giá độ tin cậy độc lập cho từng trường dữ liệu.
* Tính toán tự động điểm trung bình trên các trường hiện có và so khớp với ngưỡng quy định của Admin trong CSDL (`system_configs`).
* Tự động cảnh báo và chỉ đích danh các trường không đạt chuẩn để người dùng chụp lại hoặc chuyển sang luồng hậu kiểm của cán bộ thuế (Human-in-the-loop).

---

### 2. KIẾN TRÚC TÍCH HỢP HỆ THỐNG

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TaxKeepVN Core (.NET BE)                        │
│                                                                        │
│  [Taxpayer Service]      [Rule Repository]      [RabbitMQ Publisher]   │
│  Hồ sơ người phụ thuộc   dependent_document_rules  Gửi ảnh & TaskID    │
└─────────────────────────────────────┬──────────────────────────────────┘
                                      │
              RabbitMQ Queue: `ocr.ai.request.queue`
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         TaxAIService (Python)                          │
│                                                                        │
│  [RabbitMQ Consumer]                                                   │
│  - Giải mã ảnh (Base64 / URL httpx / Local path)                       │
│  - Hỗ trợ nạp 2 mặt ảnh (CCCD trước + sau)                             │
│                                      │                                 │
│                                      ▼                                 │
│  [DependentOcrService] ◄──── [SystemConfigRepository]                  │
│  - Tạo Dynamic Prompt từ rules       - Đọc AI_CONFIDENCE_THRESHOLD     │
│  - Gọi Gemini Vision (temp=0.0)      - Đọc THRESHOLD_<CATEGORY>        │
│  - Structured JSON Schema            - Quản lý cấu hình kiểu dữ liệu   │
│                                      │                                 │
│                                      ▼                                 │
│  [Dynamic Threshold Engine]                                            │
│  - Tính trung bình: sum(fields) / len(fields)                          │
│  - Lọc trường < applied_threshold (lowConfidenceFields)                │
│  - Tạo warningMessage chi tiết                                         │
│                                      │                                 │
│                                      ▼                                 │
│  [RabbitMQ Producer] ──────► `ocr.ai.response.queue`                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 3. ĐẶC TẢ CHI TIẾT TÍNH NĂNG OCR GIẤY TỜ

#### 3.1. Hỗ trợ đa dạng thể thức giấy tờ và đầu vào
* **Cấu hình xử lý đa ảnh:** Hỗ trợ tiếp nhận đồng thời 2 mặt giấy tờ (ví dụ: Mặt trước và Mặt sau của thẻ CCCD gắn chip).
* **Định danh giấy tờ (Document Taxonomy):**
  * `CITIZEN_ID`: Căn cước công dân / CMND (CCCD_FRONT, CCCD_BACK, CCCD_BOTH).
  * `BIRTH_CERTIFICATE`: Giấy khai sinh (Bản chính hoặc trích lục).
  * `STUDENT_CARD`: Thẻ học sinh, sinh viên, giấy xác nhận của cơ sở đào tạo.
  * `DISABILITY_CERTIFICATE`: Giấy xác nhận mức độ khuyết tật.
  * `MARRIAGE_CERTIFICATE`: Giấy chứng nhận kết hôn.
  * `RELATIONSHIP_CERTIFICATE`: Giấy tờ chứng minh quan hệ thân nhân.
  * `SUPPORT_COMMITMENT_FORM`: Bản cam kết nghĩa vụ nuôi dưỡng (Mẫu 07/XN-NPT).
  * `RESIDENCE_CT07`: Giấy xác nhận thông tin về cư trú (Mẫu CT07).
  * `OTHER`: Giấy tờ hợp lệ khác.

#### 3.2. Cấu trúc dữ liệu bóc tách (`ExtractedDependentData`)
1. **Thông tin định danh cá nhân:**
   * `citizenId`: Số CCCD/CMND (chuẩn hóa 12 hoặc 9 chữ số dạng chuỗi, bảo toàn số 0 ở đầu).
   * `fullName`: Họ và tên viết IN HOA CÓ DẤU (ví dụ: NGUYỄN VĂN AN).
   * `birthDate`: Ngày tháng năm sinh định dạng chuẩn quốc tế `YYYY-MM-DD`.
   * `gender`: Giới tính (`MALE` / `FEMALE`).
   * `nationality`: Quốc tịch (mặc định "Việt Nam").
   * `originPlace`: Quê quán ghi trên thẻ.
   * `residencePlace`: Nơi thường trú ghi trên thẻ.
   * `issueDate`: Ngày cấp giấy tờ (`YYYY-MM-DD`).
   * `expiryDate`: Ngày hết hạn thẻ CCCD (`YYYY-MM-DD`).
2. **Thông tin nhân thân (Hỗ trợ giấy khai sinh, kết hôn, CT07):**
   * `fatherFullName`, `fatherIdNumber`: Thông tin người cha.
   * `motherFullName`, `motherIdNumber`: Thông tin người mẹ.
   * `spouseFullName`: Thông tin người phối ngẫu (vợ/chồng).
3. **Thông tin văn bản hành chính:**
   * `documentType`: Mã phân loại giấy tờ nhận diện được.
   * `documentNumber`: Số hiệu văn bản / số vào sổ hộ tịch.
   * `issuingAuthority`: Cơ quan cấp (ví dụ: Cục Cảnh sát QLHC về TTXH, UBND...).

---

### 4. CƠ CHẾ BÓC TÁCH & ĐỐI SOÁT NGƯỠNG ĐỘNG (DYNAMIC THRESHOLD VALIDATION)

Đây là điểm cải tiến kỹ thuật trọng tâm của nhánh phát triển này.

#### 4.1. Đánh giá độ tin cậy từng trường (Field-level Confidence Scores)
Mô hình Gemini đánh giá độc lập xác suất chính xác từ $0.0$ đến $1.0$ cho từng trường dữ liệu bóc tách được:
```json
{
  "confidenceScores": {
    "citizenId": 0.98,
    "fullName": 0.95,
    "birthDate": 0.99,
    "gender": 1.0,
    "nationality": 1.0,
    "originPlace": 0.90,
    "residencePlace": 0.92,
    "expiryDate": 0.95,
    "issueDate": 0.88,
    "documentType": 0.95
  }
}
```
*Trường hợp một trường dữ liệu không xuất hiện trên tài liệu (ví dụ: CCCD không có thông tin cha/mẹ), trường đó nhận giá trị `null` và điểm tin cậy tương ứng là `null`.*

#### 4.2. Thuật toán tính toán điểm tin cậy trung bình tự động
Hàm `evaluate_dynamic_threshold(confidence_scores, applied_threshold)` thực hiện tính toán:
1. **Lọc dữ liệu:** Loại bỏ toàn bộ các trường có giá trị `None` (chỉ xét các trường thực tế có trên giấy tờ).
2. **Loại trừ trường `overall`:** Ngăn chặn việc trường tổng thể tính trùng vào mẫu số.
3. **Công thức toán học:**
   $$\text{Overall Confidence} = \text{round}\left(\frac{\sum_{i=1}^{N} \text{Score}_i}{N}, 2\right)$$
   *(Trong đó $N$ là tổng số lượng các trường dữ liệu hiện diện trên ảnh).*

#### 4.3. Quy trình đối soát ngưỡng 3 tầng (3-Tier Applied Threshold)
Hệ thống tuyệt đối không dùng số cứng (hardcode) trong code. Ngưỡng được truy xuất tự động từ bảng `system_configs` theo thứ tự ưu tiên:
1. **Tầng 1 (Danh mục cụ thể):** Truy vấn `THRESHOLD_<CATEGORY_CODE>` (ví dụ: `THRESHOLD_CITIZEN_ID`, `THRESHOLD_BIRTH_CERTIFICATE`).
2. **Tầng 2 (Toàn hệ thống):** Truy vấn khóa `AI_CONFIDENCE_THRESHOLD` (ví dụ Admin cấu hình `0.85`).
3. **Tầng 3 (Fallback an toàn):** Giá trị mặc định `0.80`.

#### 4.4. Phân tích kết quả kiểm tra ngưỡng (`ThresholdValidationResult`)
* `appliedThreshold`: Ngưỡng tin cậy áp dụng thực tế (ví dụ: 0.85).
* `overallConfidence`: Điểm tin cậy trung bình tính toán được (ví dụ: 0.82).
* `isPassedThreshold`: `true` nếu $\text{overallConfidence} \ge \text{appliedThreshold}$, ngược lại `false`.
* `lowConfidenceFields`: Tự động duyệt và trả về danh sách tên các trường có điểm nhỏ hơn ngưỡng:
  $$\text{LowFields} = \{ \text{field}_i \mid \text{Score}_i < \text{appliedThreshold} \}$$
* `warningMessage`: Tự động tổng hợp thông điệp cảnh báo rõ ràng gửi về client:
  > *"Độ tin cậy trích xuất (0.82) thấp hơn ngưỡng quy định (0.85). Các trường không đạt yêu cầu: [issueDate, residencePlace]. Vui lòng kiểm tra lại hoặc chụp ảnh rõ nét hơn."*

---

### 5. CƠ CHẾ THẨM ĐỊNH QUY TẮC ĐỘNG TỪ ADMIN (DYNAMIC RULE COMPLIANCE)

Khi Backend .NET gửi yêu cầu OCR, có thể đính kèm danh sách quy tắc kiểm tra từ bảng `dependent_document_rules`.

#### 5.1. Cấu trúc Rule đính kèm
```json
[
  {
    "docType": "CITIZEN_ID",
    "isMandatory": true,
    "description": "CCCD còn hạn sử dụng, không mờ số, đầy đủ 2 mặt"
  },
  {
    "docType": "STUDENT_CARD",
    "isMandatory": false,
    "description": "Thẻ sinh viên có niên khóa còn hiệu lực trong năm tính thuế"
  }
]
```

#### 5.2. Kết quả AI đối soát (`RuleValidationResult`)
AI đóng vai trò chuyên gia pháp lý rà soát tài liệu theo mô tả của Admin:
* `isMatchedRule`: `true` nếu loại giấy tờ trong ảnh thuộc danh mục Admin yêu cầu.
* `matchedDocType`: Trả về chính xác mã `docType` được khớp.
* `isCompliantWithDescription`: `true` nếu tài liệu thỏa mãn các điều kiện ghi trong `description` (ví dụ: còn hạn, có mộc đỏ...).
* `notes`: Lời nhận xét khách quan của AI hỗ trợ cán bộ thuế duyệt hồ sơ.

---

### 6. HỆ THỐNG QUẢN LÝ CẤU HÌNH HỆ THỐNG ĐỘNG (SYSTEM CONFIG SUBSYSTEM)

Để phục vụ bài toán ngưỡng động và các tham số vận hành AI, nhánh này bổ sung hệ thống cấu hình động hoàn chỉnh:

#### 6.1. Bảng cơ sở dữ liệu `system_configs`
* `config_id` (UUID PK): Khóa chính.
* `config_key` (String 100 UNIQUE): Khóa định danh (ví dụ: `AI_CONFIDENCE_THRESHOLD`, `CRUCIAL_EXTRACTION_FIELDS`).
* `config_value` (Text): Giá trị cấu hình lưu dưới dạng chuỗi.
* `data_type` (Enum): Kiểu dữ liệu (`STRING`, `INT`, `FLOAT`, `BOOLEAN`, `JSON`, `LIST_STRING`).
* `description` (Text): Diễn giải ý nghĩa cấu hình.
* `is_active` (Boolean): Trạng thái kích hoạt.
* `is_deleted` (Boolean): Hỗ trợ Xóa mềm (Soft Delete).
* `created_at`, `updated_at`: Dấu vết thời gian.

#### 6.2. Cơ chế tự động nhận diện & kiểm tra kiểu dữ liệu (`system_config_service.py`)
* Hệ thống tự động suy đoán kiểu dữ liệu khi Admin nhập giá trị:
  * `0.85` hoặc `0,85` $\rightarrow$ Tự động chuẩn hóa và lưu kiểu `FLOAT`.
  * `true`/`false` $\rightarrow$ Lưu kiểu `BOOLEAN`.
  * Chuỗi JSON hợp lệ $\rightarrow$ Lưu kiểu `JSON`.
* Bắt lỗi chặt chẽ: Ngăn chặn Admin nhập chuỗi văn bản vào cấu hình số float hoặc nhập sai cú pháp JSON.

---

### 7. ĐẶC TẢ GIAO DIỆN HÀNG ĐỢI RABBITMQ & REST API

#### 7.1. Message Queue Interface (RabbitMQ)
* **Hàng đợi tiếp nhận:** `ocr.ai.request.queue` (Durable = True)
* **Hàng đợi phản hồi:** `ocr.ai.response.queue` (Durable = True)

##### Cấu trúc Request Message từ .NET BE:
```json
{
  "taskId": "7b8e19c0-9d8a-4c22-b5e1-8f3b20e11892",
  "userId": "93a1f812-78d1-419b-a012-38d7120a1e05",
  "fileName": "cccd_mat_truoc.jpg",
  "fileBase64": null,
  "fileUrl": "https://storage.taxkeep.vn/dependents/cccd_front.jpg",
  "filePath": null,
  "backFileBase64": null,
  "backFileUrl": "https://storage.taxkeep.vn/dependents/cccd_back.jpg",
  "targetGroup": "CHILD",
  "appliedThreshold": 0.85,
  "rules": [
    {
      "docType": "CITIZEN_ID",
      "isMandatory": true,
      "description": "CCCD còn hạn sử dụng, rõ số"
    }
  ]
}
```

##### Cấu trúc Response Message trả về cho .NET BE:
```json
{
  "taskId": "7b8e19c0-9d8a-4c22-b5e1-8f3b20e11892",
  "userId": "93a1f812-78d1-419b-a012-38d7120a1e05",
  "success": true,
  "statusCode": 200,
  "message": "Trích xuất thông tin CCCD thành công.",
  "data": {
    "citizenId": "079201008899",
    "fullName": "NGUYỄN VĂN AN",
    "birthDate": "2010-05-15",
    "gender": "MALE",
    "nationality": "Việt Nam",
    "originPlace": "Hải Phòng",
    "residencePlace": "Số 123 Đường Nguyễn Huệ, Quận 1, TP.HCM",
    "expiryDate": "2035-05-15",
    "issueDate": "2021-10-10",
    "isReadable": true,
    "unreadableReason": null,
    "confidenceScores": {
      "overall": 0.95,
      "citizenId": 0.99,
      "fullName": 0.98,
      "birthDate": 0.99,
      "gender": 1.0,
      "nationality": 1.0,
      "originPlace": 0.92,
      "residencePlace": 0.91,
      "expiryDate": 0.95,
      "issueDate": 0.82
    },
    "thresholdValidation": {
      "appliedThreshold": 0.85,
      "overallConfidence": 0.95,
      "isPassedThreshold": true,
      "lowConfidenceFields": ["issueDate"],
      "warningMessage": null
    },
    "ruleValidation": {
      "isMatchedRule": true,
      "matchedDocType": "CITIZEN_ID",
      "isCompliantWithDescription": true,
      "notes": "Ảnh rõ nét, đầy đủ 2 mặt, thẻ còn hạn đến năm 2035."
    }
  },
  "errors": null
}
```

#### 7.2. RESTful API Endpoint (`/api/ocr/dependent-document`)
* **Phương thức:** `POST`
* **Content-Type:** `multipart/form-data`
* **Tham số:**
  * `frontFile` (UploadFile, bắt buộc): Ảnh mặt trước.
  * `backFile` (UploadFile, tùy chọn): Ảnh mặt sau.
  * `targetGroup` (Form string, tùy chọn): Nhóm đối tượng.
  * `rulesJson` (Form string, tùy chọn): Danh sách quy tắc JSON.
  * `appliedThreshold` (Form float, tùy chọn): Ngưỡng tin cậy ghi đè.

---

### 8. QUY TRÌNH KIỂM SOÁT ẢO GIÁC & AN TOÀN DỮ LIỆU (ANTI-HALLUCINATION)

1. **Cấu hình nhiệt độ bằng 0 (`temperature=0.0`):**
   * Trong tác vụ OCR hành chính, bất kỳ sự "sáng tạo" nào của AI đều là lỗi nghiêm trọng. Việc thiết lập `temperature=0.0` buộc mô hình chọn token có xác suất cao nhất, đảm bảo tính tất định và bóc tách trung thực dữ liệu nhìn thấy.
2. **Cơ chế phát hiện ảnh suy thoái (`isReadable` & `unreadableReason`):**
   * Nếu ảnh bị mờ nhòe, che khuất góc, lóa đèn flash không đọc được số CCCD: AI được chỉ thị bắt buộc trả về `isReadable = false` và nêu rõ lý do tại `unreadableReason`, tuyệt đối không được tự suy đoán số định danh.
3. **Cơ chế Human-in-the-loop tự động kích hoạt:**
   * Khi `isPassedThreshold = false`, hệ thống không tự ý từ chối vĩnh viễn mà đánh dấu cờ cảnh báo kèm danh sách `lowConfidenceFields`. Backend .NET sẽ dựa vào cờ này để điều hướng hiển thị giao diện cho người nộp thuế kiểm tra và sửa lại các ô thông tin bị nghi ngờ.

---

### 9. KẾT LUẬN & Ý NGHĨA KỸ THUẬT ĐỐI VỚI ĐỒ ÁN

1. **Tính hoàn thiện kỹ thuật cao:** Phân hệ không dừng lại ở mức "gọi API bóc tách ảnh đơn giản", mà đã thiết kế một giải pháp kỹ thuật trọn vẹn từ tiếp nhận bất đồng bộ (RabbitMQ), bóc tách 2 mặt ảnh, đánh giá độ tin cậy đa trường, tới thẩm định ngưỡng động từ cơ sở dữ liệu.
2. **Giải quyết bài toán phi tập trung & cấu hình linh hoạt:** Nhờ có bảng `system_configs` và module đối soát ngưỡng động, quản trị viên có thể điều chỉnh độ khắt khe của hệ thống OCR trong thời gian thực mà không cần dừng dịch vụ hay deploy lại mã nguồn.
3. **Độ tin cậy pháp lý vững chắc:** Mô hình phối hợp giữa `confidenceScores` từng trường và `rules` nghiệp vụ đảm bảo hồ sơ người phụ thuộc đáp ứng đầy đủ tính chính xác trước khi đưa vào công thức tính thuế TNCN.
