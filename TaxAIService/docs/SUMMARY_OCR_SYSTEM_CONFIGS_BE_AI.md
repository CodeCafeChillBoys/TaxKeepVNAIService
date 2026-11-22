# 📑 BÁO CÁO TỔNG HỢP NÂNG CẤP HỆ THỐNG OCR & QUẢN TRỊ CẤU HÌNH ĐỘNG
**Dự án:** TaxKeep VN  
**Phạm vi đồng bộ:** AI Service (`TaxAIService`) & Backend Service (`BE_Service`) & Hướng dẫn tích hợp Frontend (FE)  
**Ngày cập nhật:** 21/11/2026  
**Trạng thái kiểm thử:** AI Service: 129/129 Passed (100%) | BE Service: 646/646 Passed (100%)  

---

## 1. TỔNG QUAN CÁC NÂNG CẤP CHÍNH
Trong đợt nâng cấp vừa qua, hệ thống đã hoàn thiện toàn diện các hạng mục liên quan đến OCR, chuẩn hóa dữ liệu tài chính y tế và quản trị tham số động:
1. **Tách biệt và chuyên biệt hóa Bảng kê y tế:** Phân tách rõ luồng Hóa đơn viện phí thông thường (`MEDICAL_RECEIPT`) và Bảng kê chi tiết KCB Mẫu 01/BV, 02/BV (`MEDICAL_COST_STATEMENT`).
2. **Loại bỏ trạng thái `NEED_REVIEW`:** Đồng bộ chuẩn phân loại y tế sang 2 trạng thái duy nhất: `ELIGIBLE` (Hợp lệ) và `EXCLUDED` (Bị loại trừ).
3. **Đồng bộ bộ 3 chỉ số thẩm định chất lượng ảnh:** Cả 4 luồng OCR (`expense`, `income`, `dependent`, `certificate`) đều trả về đầy đủ `overallConfidence`, `appliedThreshold`, `isPassedThreshold`.
4. **Bỏ hardcode ở Backend:** BE không còn gán cứng `AppliedThreshold = 0.80`, AI Service tự động đọc từ Database và trả kết quả đối soát động về cho BE.
5. **Quản trị cấu hình hệ thống động (`system_configs`):** Seed đầy đủ 50 tham số ngưỡng tin cậy và trường cốt lõi lên Database của AI.
6. **Động hóa toàn bộ Prompt Templates (`ai_prompt_templates`):** Đưa các prompt thẩm định lên DB, cho phép Admin tùy chỉnh trực tiếp qua Admin Dashboard mà không cần sửa code.

---

## 2. CHI TIẾT PHÂN HỆ AI SERVICE (`TaxAIService`)

### 2.1. Tách và động hóa Prompt Bảng kê Y tế & Hóa đơn chi phí
* **`PROMPT_EXPENSE_OCR`:** Chuyên biệt cho Hóa đơn GTGT, học phí, từ thiện, bảo hiểm, khấu trừ thuế.
  * Hỗ trợ placeholder động `{medical_statement_rules}`.
* **`PROMPT_MEDICAL_STATEMENT_RULES`:** Quy tắc bóc tách bảng kê chi phí KCB (Mục 7a) nạp động vào hóa đơn chi phí khi có danh mục KCB.
* **`PROMPT_MEDICAL_STATEMENT_OCR`:** Prompt chuyên biệt cho Bảng kê chi phí KCB theo Quyết định 6556/QĐ-BYT và 697/QĐ-BYT.
* Đã tạo migration Alembic `d9a2e3f4b5c6_make_medical_prompts_dynamic.py` nạp toàn bộ lên DB Supabase.

### 2.2. Bỏ trạng thái `NEED_REVIEW`
* Enum `MedicalDeductionStatus` và `SuggestedStatus`: Chỉ giữ `ELIGIBLE` và `EXCLUDED`.
* Logic tính `eligibleAmount`:
  * Nếu `ELIGIBLE`: `eligibleAmount = patientCoPay + patientSelfPay`.
  * Nếu `EXCLUDED`: `eligibleAmount = 0`.

### 2.3. Cấu hình hệ thống động (`system_configs`)
Đã nạp 50 key cấu hình idempotent vào DB qua migration `c8f1e2d3b4a5_seed_all_document_system_configs.py`:
* **Chung:** `AI_CONFIDENCE_THRESHOLD = 0.80`, `CRUCIAL_EXTRACTION_FIELDS`, `MEDICAL_STATEMENT_AMOUNT_TOLERANCE = 1000.0`.
* **Hóa đơn (`expense_ocr`):** `THRESHOLD_MEDICAL_RECEIPT`, `THRESHOLD_MEDICAL_COST_STATEMENT`, `THRESHOLD_EDUCATION_RECEIPT`, `THRESHOLD_DONATION_RECEIPT`, `THRESHOLD_WITHHOLDING_VOUCHER` (0.85), `THRESHOLD_VAT_INVOICE`, `THRESHOLD_SALES_INVOICE`, `THRESHOLD_INSURANCE_PREMIUM_RECEIPT`, `THRESHOLD_GENERAL_EXPENSE`.
* **Thu nhập (`income_ocr`):** `THRESHOLD_INCOME_PAYSLIP = 0.80`.
* **Người phụ thuộc (`dependent_ocr`):** `THRESHOLD_CITIZEN_ID` & `THRESHOLD_CCCD` (0.85), `THRESHOLD_BIRTH_CERTIFICATE`, `THRESHOLD_STUDENT_CARD`, `THRESHOLD_DISABILITY_CERTIFICATE`, `THRESHOLD_MARRIAGE_CERTIFICATE`, `THRESHOLD_RELATIONSHIP_CERTIFICATE`, `THRESHOLD_RESIDENCE_CT07`, `THRESHOLD_SUPPORT_COMMITMENT_FORM`.
* **Chứng chỉ chuyên gia (`certificate_ocr`):** `THRESHOLD_EXPERT_CERTIFICATE`, `THRESHOLD_TAX_AGENT`, `THRESHOLD_CPA`, `THRESHOLD_ACCOUNTANT`, `THRESHOLD_CHIEF_ACCOUNTANT`.

### 2.4. Đọc ngưỡng động thông minh
* `dependent_ocr_service.py`: Tự động đọc theo `category_code=result.data.document_type` (vd: đọc `THRESHOLD_CITIZEN_ID` cho CCCD).
* `certificate_ocr_service.py`: Tự động đọc theo `category_code=doc.certificate_type` (vd: đọc `THRESHOLD_TAX_AGENT` cho Đại lý thuế).

---

## 3. CHI TIẾT PHÂN HỆ BACKEND SERVICE (`BE_Service`)

### 3.1. Đồng bộ DTOs & Message Contracts
* **DTOs Chứng chỉ hành nghề (`TaxKeepVN.Application`):**
  * `CertificateOcrRequestMessage`: Bổ sung `AppliedThreshold` (optional, không ép cứng).
  * `CertificateExtractedDataDto`: Bổ sung `AppliedThreshold` (decimal) và `IsPassedThreshold` (bool).
  * `CertificateOcrResponseMessage`: Bổ sung `AppliedThreshold` và `IsPassedThreshold`.
* **DTOs Hóa đơn / Chi phí:** Đã đồng bộ `OverallConfidence`, `AppliedThreshold`, `IsPassedThreshold`.
* **DTOs Người phụ thuộc & Thu nhập:** Nhận và lưu trữ đầy đủ bộ 3 chỉ số.

### 3.2. Gỡ bỏ gán cứng và nhận ngưỡng động từ AI
* **`ExpertApplicationService.cs`:** Gỡ bỏ dòng gán cứng `AppliedThreshold = 0.80m` khi gửi request sang RabbitMQ.
* **`CertificateOcrConsumerBackgroundService.cs`:** Đọc trực tiếp `AppliedThreshold` và `IsPassedThreshold` từ AI Service trả về và lưu vào hồ sơ đăng ký chuyên gia.

---

## 4. CHI TIẾT TÍCH HỢP FRONTEND (FE)

### 4.1. Cấu trúc dữ liệu Bảng kê y tế (`MEDICAL_COST_STATEMENT`)
FE nhận JSON gồm 4 khối để render:
1. `medicalHeader`: Bệnh viện, khoa, tên bệnh nhân, ngày sinh, ngày khám/vào/ra viện, BHYT (`hasInsuranceCard`, `benefitRate`).
2. `medicalSections`: Danh sách các nhóm chi phí cha (I, II, III...).
3. `medicalLines`: Chi tiết dịch vụ/thuốc kèm cột `deductionStatus` (`ELIGIBLE` / `EXCLUDED`), số tiền được trừ `eligibleAmount`, lý do `deductionReason`.
4. `medicalSummary`: Tổng viện phí, tiền BHYT trả, tổng tiền bệnh nhân trả, tiền cùng chi trả, tiền tự trả.

### 4.2. Xử lý Cảnh báo chất lượng ảnh trên UI
Trên tất cả các màn hình upload (Hóa đơn, Thu nhập, Người phụ thuộc, Chứng chỉ):
* Nếu `isPassedThreshold == false`: Hiển thị cảnh báo màu vàng/cam:  
  * *"Ảnh chụp bị mờ hoặc độ tin cậy thấp (overallConfidence < appliedThreshold). Vui lòng kiểm tra lại thông tin hoặc chụp lại ảnh rõ nét hơn."*
* Nếu `isPassedThreshold == true`: Hiển thị trạng thái màu xanh đạt chuẩn.

### 4.3. Admin Web Dashboard
* Sẵn sàng tích hợp API CRUD bảng `system_configs` để Admin cấu hình ngưỡng tin cậy theo thời gian thực.
* Sẵn sàng tích hợp API xem và cập nhật Prompt Templates trong bảng `ai_prompt_templates`.

---

## 5. BẢNG TỔNG HỢP KIỂM THỬ (TEST SUMMARY)

| Phân hệ | Bộ test | Số lượng test | Trạng thái |
| :--- | :--- | :--- | :--- |
| **TaxAIService** | Pytest (Unit / Services) | **129 / 129** | ✅ 100% Passed (1.60s) |
| **BE_Service** | xUnit (.NET 8 Unit Tests) | **646 / 646** | ✅ 100% Passed (319ms) |
