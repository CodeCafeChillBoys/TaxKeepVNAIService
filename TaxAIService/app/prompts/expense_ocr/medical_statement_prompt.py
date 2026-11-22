import re
from typing import Optional
from app.schemas.expense_ocr.expense_ocr_schema import AdminCategoryItem

MEDICAL_STATEMENT_RULES = """7a. BÓC TÁCH BẢNG KÊ CHI PHÍ KHÁM BỆNH, CHỮA BỆNH
   - Chọn đúng mã được đánh dấu là bảng kê KCB trong danh sách BE gửi. Nhận diện mẫu QĐ 697 hoặc QĐ 6556 qua tiêu đề, phần hành chính, bảng chi phí và phần tổng kết. Hóa đơn chỉ ghi "Thu viện phí" vẫn xử lý theo quy tắc hóa đơn.
   - Khi schema có các trường sau, điền medicalHeader, medicalSections, medicalLines và medicalSummary cho bảng kê. Mục 7 về items áp dụng cho hóa đơn.
   - medicalHeader: đọc mẫu, cơ sở KCB, tên và ngày sinh người bệnh, ngày khám và thời gian điều trị. Chỉ trả tình trạng dùng thẻ BHYT. Không ghi số thẻ trong bất kỳ trường nào, kể cả fields.
   - medicalSections: đánh số sectionIndex theo từng khối, đọc tình trạng dùng thẻ và mức hưởng. Dòng tiếp nối sang trang sau giữ sectionIndex của khối đó.
   - medicalLines: giữ sectionIndex, mã mục và tên mục như bản in. Đánh dấu isPackageSubLine cho dòng con của gói mục 10. Ánh xạ cột (1)–(5) vào itemName, unit, quantity, unitPriceHospital, unitPriceInsurance. Ánh xạ cột (6)–(13) lần lượt vào serviceRate, hospitalAmount, insuranceRate, insuranceAmount, insuranceFundPaid, patientCoPay, otherSourcePaid, patientSelfPay.
   - Trả null cho ô trống hoặc không đọc được, trả 0 cho ô ghi 0. Tách mức hưởng của khối khỏi tỷ lệ thanh toán BHYT của dòng.
   - Gợi ý theo từng khối: có dùng thẻ và cột (8) > 0 thì ELIGIBLE / IN_COVERAGE_COPAY. Nếu đồng thời cột (13) > 0 thì giữ riêng số cùng chi trả và số tự trả. Có dùng thẻ và cột (8) = 0 thì EXCLUDED / OUT_OF_COVERAGE. Không dùng thẻ thì đối chiếu danh mục KCB của Bộ Y tế để xác định ELIGIBLE / TREATMENT_EXPENSE_SELF_PAY hoặc EXCLUDED. Dòng không thuộc diện khám chữa bệnh hoặc chữ mờ không đọc được thì EXCLUDED / EXCLUDED_UNREADABLE.
   - medicalSummary: đọc số in ở phần tổng kết. Không đưa dòng "Cộng" hoặc dòng tổng kết vào medicalLines."""


def replace_medical_statement_rules(template: str, rules: str) -> str:
    # Stored templates and Redis may still contain an older version of section 7a.
    pattern = r"(?ms)^7a\. BÓC TÁCH BẢNG KÊ.*?(?=^[0-9]+\. |\Z)"
    template, count = re.subn(pattern, lambda _: f"{rules}\n\n" if rules else "", template)
    return f"{template.rstrip()}\n\n{rules}" if rules and not count else template


MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT = """Bạn là AI chuyên gia thẩm định và bóc tách BẢNG KÊ CHI PHÍ KHÁM BỆNH, CHỮA BỆNH (Mẫu số 01/BV hoặc 02/BV theo Quyết định số 6556/QĐ-BYT hoặc Quyết định 697/QĐ-BYT của Bộ Y tế) phục vụ hồ sơ quyết toán thuế TNCN tại Việt Nam.

TÀI LIỆU NÀY LÀ BẢNG KÊ CHI PHÍ Y TẾ ĐÍNH KÈM HÓA ĐƠN VIỆN PHÍ.

========================================================================================
QUY TẮC BÓC TÁCH BẢNG KÊ Y TẾ (CỰC KỲ QUAN TRỌNG):
========================================================================================
1. docTypeCode: BẮT BUỘC gán docTypeCode = '{medical_doc_type_code}'. Đặt isTaxDocument = true.
2. TUYỆT ĐỐI KHÔNG bóc tách các trường hóa đơn thương mại thông thường:
   - sellerTaxCode, sellerPhone, buyerTaxCode, invoiceSeries, lookupUrl, lookupCode: ĐỂ NULL.
   - mảng 'items': ĐỂ RỖNG []. TẤT CẢ dịch vụ y tế, tiền khám, xét nghiệm, thuốc PHẢI đưa vào 'medicalLines'.
3. THÔNG TIN CHUNG (CHỈ BÓC TÁCH CƠ BẢN):
   - sellerName: Tên cơ sở y tế / Bệnh viện (lấy từ tiêu đề bảng kê).
   - invoiceNumber: Số hồ sơ bệnh án hoặc số bảng kê / mã lượt khám nếu có.
   - invoiceDate: Ngày khám hoặc ngày lập bảng kê (YYYY-MM-DD). ĐỌC KỸ: Nếu bảng kê ghi "20/11/2026" thì invoiceDate là "2026-11-20", NĂM LÀ 2026, KHÔNG ĐƯỢC NHẦM VỚI 2020 HAY NĂM SINH!
   - extractedYear: Năm của invoiceDate (BẮT BUỘC 4 CHỮ SỐ, ví dụ: 2026). TUYỆT ĐỐI KHÔNG lấy năm sinh người bệnh (2000), không nhầm ngày 20 thành năm 2020.
   - buyerName: Họ tên người bệnh.
   - buyerIdCard: Số CCCD/CMND người bệnh nếu có ghi.
   - totalAmount: Tổng số tiền người bệnh thực trả (lấy từ medicalSummary.patientPaid).

4. BÓC TÁCH CHI TIẾT 4 KHỐI DỮ LIỆU Y TẾ:
   a. medicalHeader:
      - formCode: Mẫu số bảng kê (VD: 01/BV).
      - statementNumber: Số bảng kê hoặc số hồ sơ bệnh án.
      - formVersion: "QD6556" hoặc "QD697" nếu nhận diện được.
      - hospitalName / facilityName: Tên cơ sở y tế / Bệnh viện.
      - hospitalCode: Mã KCB BHYT nếu có.
      - department: Khoa điều trị.
      - patientName: Họ và tên người bệnh.
      - dob / patientDateOfBirth: Ngày sinh YYYY-MM-DD (hoặc YYYY-01-01 nếu chỉ có năm sinh).
      - gender: Giới tính ("Nam" hoặc "Nữ").
      - idCard / patientIdCard: Số CCCD/CMND người bệnh nếu có.
      - insuranceNumber: Mã thẻ BHYT nếu có.
      - benefitRate: Mức hưởng BHYT dạng số thập phân (ví dụ 80% = 0.8, 100% = 1.0).
      - hasInsuranceCard: true nếu có sử dụng thẻ BHYT, false nếu không dùng hoặc thu phí dịch vụ.
      - visitDate / admissionDate: Ngày đến khám hoặc ngày vào viện YYYY-MM-DD (Định dạng YYYY-MM-DD, kiểm tra đúng 4 chữ số năm, không nhầm ngày 20 thành năm 2020).
      - dischargeDate: Ngày kết thúc khám hoặc ra viện YYYY-MM-DD (Định dạng YYYY-MM-DD, ví dụ: "20/11/2026" -> "2026-11-20", TUYỆT ĐỐI KHÔNG ĐỌC LÀ 2020-11-20).
      - treatmentType: Ngoại trú hoặc Nội trú.

   b. medicalSections:
      - Đánh số sectionIndex (1, 2, 3...) theo từng nhóm chi phí ghi trên bảng kê (VD: I. Tiền khám bệnh, II. Chẩn đoán hình ảnh, III. Xét nghiệm, IV. Thuốc điều trị...).
      - hasInsuranceCard: Khối này có áp dụng BHYT hay không.
      - benefitRate: Mức hưởng BHYT (ví dụ 80% thì điền 0.8, 100% điền 1.0, không có thì null).

   c. medicalLines:
      - sectionIndex: Số thứ tự nhóm cha (1, 2, 3...).
      - itemOrder: STT dòng dịch vụ (1, 2, 3...).
      - itemName: Tên dịch vụ y tế, kỹ thuật, thuốc, xét nghiệm, vật tư.
      - unit: Đơn vị tính (Lần, Viên, Gói, Toa...).
      - quantity: Số lượng.
      - unitPrice / unitPriceHospital: Đơn giá viện phí.
      - totalAmount / hospitalAmount: Thành tiền = quantity x unitPrice.
      - insurancePaid / insuranceFundPaid: Số tiền Quỹ BHYT thanh toán (cột 10).
      - patientCoPay: Số tiền người bệnh cùng chi trả trong danh mục BHYT (cột 11).
      - patientSelfPay: Số tiền người bệnh tự trả (cột 13 hoặc toàn bộ nếu không dùng thẻ BHYT).
      - deductionStatus: Trạng thái giảm trừ thuế TNCN của từng dòng theo danh mục y tế gửi kèm (CHỈ CÓ 2 TRẠNG THÁI "ELIGIBLE" HOẶC "EXCLUDED"):
        * "ELIGIBLE": Dòng thuộc danh mục khám chữa bệnh hợp lệ trong phạm vi BHYT hoặc điều trị bệnh bắt buộc (khám bệnh, xét nghiệm thông thường, CĐHA, thuốc điều trị, phẫu thuật bệnh lý...).
        * "EXCLUDED": Bị loại trừ:
          + Toàn bộ dịch vụ thuộc Khối ngoài danh mục BHYT chi trả tự nguyện (gói xét nghiệm tầm soát đột biến gen tự nguyện, tầm soát dị ứng tự nguyện theo yêu cầu, khám tổng quát theo yêu cầu...).
          + Phẫu thuật tạo hình thẩm mỹ làm đẹp, cắt mí, nâng mũi, tiêm filler, botox, spa làm trắng da, thực phẩm chức năng bồi bổ (thuốc bổ gan, thực phẩm bảo vệ sức khỏe chống oxy hóa...), phòng VIP tự chọn, hoặc chữ mờ/không đủ dữ liệu căn cứ hợp lệ...
      - isEligibleDeduction: true nếu deductionStatus là "ELIGIBLE", false nếu "EXCLUDED".
      - deductionReason: Mã lý do cụ thể:
        * "IN_COVERAGE_COPAY" (cùng chi trả BHYT - Cột 11).
        * "TREATMENT_EXPENSE_SELF_PAY" (chỉ dùng khi bệnh nhân KHÔNG CÓ THẺ BHYT và điều trị bệnh bắt buộc theo quy định Bộ Y tế).
        * "EXCLUDED_COSMETIC_SURGERY" (thẩm mỹ làm đẹp).
        * "EXCLUDED_SKIN_CARE_SPA" (spa làm đẹp).
        * "EXCLUDED_FUNCTIONAL_FOOD" (thực phẩm chức năng, thuốc bổ gan, TPCN bồi bổ...).
        * "EXCLUDED_VOLUNTARY_SCREENING" hoặc "EXCLUDED_OUT_OF_COVERAGE" (dịch vụ/xét nghiệm tầm soát tự chọn ngoài danh mục BHYT).
        * "EXCLUDED_VIP_ROOM" (tiện ích tự chọn).
        * "EXCLUDED_UNREADABLE" (chữ mờ/không đủ căn cứ).
      - eligibleAmount: Số tiền người bệnh chi trả thực tế hợp lệ giảm trừ:
        * QUY TẮC CỐT LÕI: Đối với bảng kê có BHYT, eligibleAmount CHỈ ĐƯỢC LẤY từ phần cùng chi trả trong danh mục BHYT (patientCoPay - Cột 11). Toàn bộ phần tự chi trả (patientSelfPay - Cột 13) của khối ngoài danh mục hoặc thuốc/TPCN bổ sung BẮT BUỘC có eligibleAmount = 0.
        * Nếu deductionStatus == "ELIGIBLE": eligibleAmount = patientCoPay (nếu có BHYT) hoặc patientSelfPay (nếu không có BHYT và điều trị bắt buộc).
        * Nếu deductionStatus == "EXCLUDED": eligibleAmount = 0.
      - suggestedStatus: "ELIGIBLE" hoặc "EXCLUDED" (đồng bộ với deductionStatus).
      - confidenceScore: Độ rõ nét từ 0.0 đến 1.0.

   d. medicalSummary:
      - totalHospitalAmount: Tổng chi phí khám chữa bệnh cả đợt.
      - insurancePaidAmount / insuranceFundPaid: Tổng tiền Quỹ BHYT chi trả.
      - patientPaid / patientPaidAmount: Tổng số tiền người bệnh phải thanh toán thực tế.
      - patientSelfPayAmount: Chi phí tự trả ngoài danh mục BHYT.
      - coPayWithinInsurance: Tổng tiền cùng chi trả trong danh mục BHYT.
      - otherPatientPayments: Chi phí tự trả khác nếu có.

5. MẢNG 'fields':
   Chỉ tạo các mục trong fields cho các thông tin y tế, ví dụ:
   - sellerName, buyerName, invoiceDate, buyerIdCard, totalAmount
   - medicalSummary.totalHospitalAmount, medicalSummary.patientPaid
   - medicalLines.[i].itemName, medicalLines.[i].hospitalAmount, medicalLines.[i].patientSelfPay
   TUYỆT ĐỐI KHÔNG đưa các trường hóa đơn rác (sellerTaxCode, invoiceSeries,...) vào mảng fields.
{medical_categories_guide}"""


def build_medical_categories_guide(categories_text: str) -> str:
    """Tạo đoạn hướng dẫn đối chiếu danh mục dịch vụ y tế."""
    if not categories_text:
        return ""
    return (
        "\n\nDANH MỤC DỊCH VỤ Y TẾ ĐƯỢC GIẢM TRỪ VÀ LOẠI TRỪ (THEO QĐ 697/QĐ-BYT & THUẾ TNCN):\n"
        f"{categories_text}\n\n"
        "QUY TẮC PHÂN LOẠI CHI TIẾT (ĐẶC BIỆT LÀ CÁC DÒNG XÉT NGHIỆM VÀ DỊCH VỤ):\n"
        "1. DỰA VÀO TỶ LỆ VÀ CỘT BHYT (CĂN CỨ ĐỊNH LƯỢNG ƯU TIÊN SỐ 1):\n"
        "   - Nếu bệnh nhân có dùng thẻ BHYT (benefitRate > 0 hoặc hasInsuranceCard = true):\n"
        "     + Dòng dịch vụ/xét nghiệm/thuốc có tỷ lệ BHYT > 0% và có Quỹ BHYT/Cùng chi trả > 0 (Khối A):\n"
        "       --> BẮT BUỘC gán deductionStatus = 'ELIGIBLE', isEligibleDeduction = true, deductionReason = 'IN_COVERAGE_COPAY', eligibleAmount = patientCoPay.\n"
        "     + Dòng dịch vụ/xét nghiệm/thuốc có tỷ lệ BHYT = 0%, Quỹ BHYT = 0 và bệnh nhân tự trả 100% (Khối B - Ngoài danh mục BHYT):\n"
        "       --> BẮT BUỘC gán deductionStatus = 'EXCLUDED', isEligibleDeduction = false, deductionReason = 'EXCLUDED_OUT_OF_COVERAGE', eligibleAmount = 0.\n"
        "2. DỰA VÀO BẢN CHẤT CỦA DỊCH VỤ XÉT NGHIỆM:\n"
        "   - HỢP LỆ (ELIGIBLE): Xét nghiệm bệnh học phục vụ chẩn đoán và điều trị bệnh lý (công thức máu, sinh hóa máu, nước tiểu, vi sinh, chẩn đoán hình ảnh, sinh thiết...).\n"
        "   - LOẠI TRỪ (EXCLUDED): Xét nghiệm tầm soát tự nguyện theo yêu cầu, không phục vụ điều trị trực tiếp (gói tầm soát đột biến gen, tầm soát dị ứng tự nguyện theo yêu cầu, xét nghiệm ADN huyết thống, khám sức khỏe tổng quát tự chọn...). Gán deductionStatus = 'EXCLUDED', deductionReason = 'EXCLUDED_OUT_OF_COVERAGE' hoặc 'EXCLUDED_VOLUNTARY_SCREENING', eligibleAmount = 0.\n"
        "3. CÁC KHOẢN LOẠI TRỪ KHÁC:\n"
        "   - Thực phẩm chức năng, thuốc bổ gan, vitamin bồi bổ: deductionStatus = 'EXCLUDED', deductionReason = 'EXCLUDED_FUNCTIONAL_FOOD', eligibleAmount = 0.\n"
        "   - Phẫu thuật thẩm mỹ làm đẹp, spa chăm sóc da, phòng VIP tự chọn: deductionStatus = 'EXCLUDED', eligibleAmount = 0."
    )


def build_medical_statement_prompt(
    medical_doc_type: str = "MEDICAL_COST_STATEMENT",
    categories_text: str = "",
    prompt_service: Optional[object] = None,
) -> str:
    """Tạo prompt bóc tách bảng kê KCB với các biến cần thiết, hỗ trợ nạp động từ PromptTemplateService nếu có."""
    guide = build_medical_categories_guide(categories_text)
    if prompt_service and hasattr(prompt_service, "get_rendered_prompt"):
        rendered = prompt_service.get_rendered_prompt(
            prompt_key="PROMPT_MEDICAL_STATEMENT_OCR",
            default_template=MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
            params={
                "medical_doc_type_code": medical_doc_type,
                "medical_categories_guide": guide,
            },
        )
        if guide and categories_text not in rendered:
            rendered += guide
        return rendered

    prompt = MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT.replace("{medical_doc_type_code}", medical_doc_type)
    prompt = prompt.replace("{medical_categories_guide}", guide)
    return prompt
