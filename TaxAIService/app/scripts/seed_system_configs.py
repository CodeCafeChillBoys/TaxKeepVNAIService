import os
import sys
import logging
from typing import List, Dict, Any

# Đảm bảo import được module app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import Session
from app.infrastructure.database import get_db_context
from app.models.ai_extraction_models import SystemConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_SYSTEM_CONFIGS: List[Dict[str, Any]] = [
    # ── 1. CẤU HÌNH HỆ THỐNG CHUNG ──────────────────────────────────────────
    {
        "config_key": "AI_CONFIDENCE_THRESHOLD",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất AI mặc định toàn hệ thống (0.0 - 1.0)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_EXTRACTION_FIELDS",
        "config_value": "total_amount,seller_tax_code,buyer_id_card,invoice_number",
        "data_type": "LIST_STRING",
        "description": "Danh sách trường cốt lõi mặc định bắt buộc rõ nét cho hóa đơn",
        "is_active": True,
    },
    {
        "config_key": "MEDICAL_STATEMENT_AMOUNT_TOLERANCE",
        "config_value": "1000.0",
        "data_type": "FLOAT",
        "description": "Dung sai chênh lệch số tiền cho phép khi đối soát bảng kê y tế (VNĐ)",
        "is_active": True,
    },
    {
        "config_key": "ALLOWED_DOCUMENT_TYPES",
        "config_value": "BIRTH_CERTIFICATE, CITIZEN_ID, STUDENT_CARD, DISABILITY_CERTIFICATE, MARRIAGE_CERTIFICATE, RELATIONSHIP_CERTIFICATE, SUPPORT_COMMITMENT_FORM, RESIDENCE_CT07, OTHER",
        "data_type": "LIST_STRING",
        "description": "Danh mục các loại giấy tờ hồ sơ người phụ thuộc hợp lệ (Admin có thể thêm/sửa trên UI)",
        "is_active": True,
    },
    {
        "config_key": "ALLOWED_DEPENDENT_TYPES",
        "config_value": "CHILD_UNDER_18, CHILD_OVER_18_STUDYING, CHILD_OVER_18_DISABLED, PARENT_RETIRED, PARENT_DISABLED, SPOUSE_RETIRED, SPOUSE_DISABLED, OTHER_HELPLESS",
        "data_type": "LIST_STRING",
        "description": "Danh mục mã phân loại nhóm người phụ thuộc chuẩn hóa (Admin có thể thêm/sửa trên UI)",
        "is_active": True,
    },

    # ── 2. HÓA ĐƠN CHI PHÍ & CHỨNG TỪ GIẢM TRỪ (EXPENSE OCR) ─────────────────
    # 2.1 Y tế & Khám chữa bệnh
    {
        "config_key": "THRESHOLD_MEDICAL_RECEIPT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Hóa đơn / Biên lai viện phí khám chữa bệnh",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_MEDICAL_RECEIPT",
        "config_value": "total_amount,seller_name,invoice_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Biên lai viện phí y tế",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_MEDICAL_COST_STATEMENT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Bảng kê chi phí KCB (Mẫu 01/BV, 02/BV)",
        "is_active": True,
    },

    # 2.2 Học phí & Giáo dục đào tạo
    {
        "config_key": "THRESHOLD_EDUCATION_RECEIPT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Biên lai / Hóa đơn học phí, giáo dục đào tạo",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_EDUCATION_RECEIPT",
        "config_value": "total_amount,seller_name,invoice_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Hóa đơn / Biên lai học phí",
        "is_active": True,
    },

    # 2.3 Từ thiện & Nhân đạo
    {
        "config_key": "THRESHOLD_DONATION_RECEIPT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng từ đóng góp từ thiện, nhân đạo, khuyến học",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_DONATION_RECEIPT",
        "config_value": "total_amount,seller_name,invoice_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Chứng từ đóng góp từ thiện",
        "is_active": True,
    },

    # 2.4 Khấu trừ thuế TNCN
    {
        "config_key": "THRESHOLD_WITHHOLDING_VOUCHER",
        "config_value": "0.85",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng từ khấu trừ thuế TNCN điện tử / giấy",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_WITHHOLDING_VOUCHER",
        "config_value": "total_income,tax_withheld,seller_tax_code,income_year",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Chứng từ khấu trừ thuế TNCN",
        "is_active": True,
    },

    # 2.5 Hóa đơn GTGT & Hóa đơn thương mại
    {
        "config_key": "THRESHOLD_VAT_INVOICE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Hóa đơn Giá trị gia tăng (VAT)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_VAT_INVOICE",
        "config_value": "total_amount,seller_tax_code,invoice_number,invoice_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Hóa đơn GTGT",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_SALES_INVOICE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Hóa đơn bán hàng trực tiếp",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_SALES_INVOICE",
        "config_value": "total_amount,seller_name,invoice_number,invoice_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Hóa đơn bán hàng",
        "is_active": True,
    },

    # 2.6 Bảo hiểm nhân thọ / hưu trí tự nguyện
    {
        "config_key": "THRESHOLD_INSURANCE_PREMIUM_RECEIPT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Biên lai bảo hiểm nhân thọ / hưu trí tự nguyện",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_INSURANCE_PREMIUM_RECEIPT",
        "config_value": "total_amount,seller_name,invoice_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Biên lai bảo hiểm",
        "is_active": True,
    },

    # 2.7 Chi phí chung
    {
        "config_key": "THRESHOLD_GENERAL_EXPENSE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Hóa đơn / Chứng từ chi phí chung",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_GENERAL_EXPENSE",
        "config_value": "total_amount,seller_tax_code",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Hóa đơn / Chứng từ chi phí chung",
        "is_active": True,
    },

    # ── 3. THU NHẬP TIỀN LƯƠNG & TIỀN CÔNG (INCOME OCR) ───────────────────────
    {
        "config_key": "THRESHOLD_INCOME_PAYSLIP",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Phiếu lương / Xác nhận thu nhập chịu thuế",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_INCOME_PAYSLIP",
        "config_value": "total_taxable_income,month,year",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Phiếu lương / Bảng kê thu nhập",
        "is_active": True,
    },

    # ── 4. HỒ SƠ NGƯỜI PHỤ THUỘC (DEPENDENT OCR) ─────────────────────────────
    # 4.1 Căn cước công dân / CMND
    {
        "config_key": "THRESHOLD_CITIZEN_ID",
        "config_value": "0.85",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Căn cước công dân / CMND người phụ thuộc",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_CITIZEN_ID",
        "config_value": "citizen_id,full_name,birth_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Căn cước công dân",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_CCCD",
        "config_value": "0.85",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Căn cước công dân (alias CCCD)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_CCCD",
        "config_value": "citizen_id,full_name,birth_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Căn cước công dân (alias CCCD)",
        "is_active": True,
    },

    # 4.2 Giấy khai sinh
    {
        "config_key": "THRESHOLD_BIRTH_CERTIFICATE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Giấy khai sinh người phụ thuộc",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_BIRTH_CERTIFICATE",
        "config_value": "full_name,birth_date,father_full_name,mother_full_name",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Giấy khai sinh",
        "is_active": True,
    },

    # 4.3 Thẻ học sinh / sinh viên
    {
        "config_key": "THRESHOLD_STUDENT_CARD",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Thẻ học sinh / sinh viên",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_STUDENT_CARD",
        "config_value": "full_name,student_id",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Thẻ học sinh / sinh viên",
        "is_active": True,
    },

    # 4.4 Giấy xác nhận khuyết tật
    {
        "config_key": "THRESHOLD_DISABILITY_CERTIFICATE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Giấy xác nhận khuyết tật",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_DISABILITY_CERTIFICATE",
        "config_value": "full_name",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Giấy xác nhận khuyết tật",
        "is_active": True,
    },

    # 4.5 Giấy chứng nhận kết hôn
    {
        "config_key": "THRESHOLD_MARRIAGE_CERTIFICATE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Giấy chứng nhận kết hôn",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_MARRIAGE_CERTIFICATE",
        "config_value": "full_name,spouse_full_name",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Giấy chứng nhận kết hôn",
        "is_active": True,
    },

    # 4.6 Giấy xác nhận quan hệ / cư trú (CT07/CT08)
    {
        "config_key": "THRESHOLD_RELATIONSHIP_CERTIFICATE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Giấy xác nhận thông tin quan hệ cư trú (CT07/CT08)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_RELATIONSHIP_CERTIFICATE",
        "config_value": "full_name,citizen_id",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Giấy xác nhận quan hệ cư trú",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_RESIDENCE_CT07",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Giấy xác nhận thông tin về cư trú (Mẫu CT07)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_RESIDENCE_CT07",
        "config_value": "full_name,citizen_id",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Giấy xác nhận thông tin về cư trú (CT07)",
        "is_active": True,
    },

    # 4.7 Bản cam kết nghĩa vụ phụ dưỡng
    {
        "config_key": "THRESHOLD_SUPPORT_COMMITMENT_FORM",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Bản cam kết nghĩa vụ phụ dưỡng người phụ thuộc",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_SUPPORT_COMMITMENT_FORM",
        "config_value": "full_name",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Bản cam kết nghĩa vụ phụ dưỡng",
        "is_active": True,
    },

    # ── 5. CHỨNG CHỈ HÀNH NGHỀ CHUYÊN GIA (CERTIFICATE OCR) ───────────────────
    {
        "config_key": "THRESHOLD_EXPERT_CERTIFICATE",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng chỉ hành nghề chuyên gia (mặc định chung)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_EXPERT_CERTIFICATE",
        "config_value": "certificate_number,full_name,issue_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi bắt buộc rõ nét cho Chứng chỉ hành nghề chuyên gia",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_TAX_AGENT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng chỉ hành nghề dịch vụ làm thủ tục về thuế (Đại lý thuế)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_TAX_AGENT",
        "config_value": "certificate_number,full_name,issue_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Chứng chỉ Đại lý thuế",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_CPA",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng chỉ Kiểm toán viên (CPA)",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_CPA",
        "config_value": "certificate_number,full_name,issue_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Chứng chỉ Kiểm toán viên (CPA)",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_ACCOUNTANT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng chỉ hành nghề Kế toán viên",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_ACCOUNTANT",
        "config_value": "certificate_number,full_name,issue_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Chứng chỉ hành nghề Kế toán viên",
        "is_active": True,
    },
    {
        "config_key": "THRESHOLD_CHIEF_ACCOUNTANT",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng tin cậy trích xuất Chứng chỉ bồi dưỡng Kế toán trưởng",
        "is_active": True,
    },
    {
        "config_key": "CRUCIAL_FIELDS_CHIEF_ACCOUNTANT",
        "config_value": "certificate_number,full_name,issue_date",
        "data_type": "LIST_STRING",
        "description": "Trường cốt lõi cho Chứng chỉ bồi dưỡng Kế toán trưởng",
        "is_active": True,
    },
]


def _run_seed_on_session(db: Session) -> int:
    count = 0
    for item in SEED_SYSTEM_CONFIGS:
        existing = db.query(SystemConfig).filter(SystemConfig.config_key == item["config_key"]).first()
        if not existing:
            config = SystemConfig(
                config_key=item["config_key"],
                config_value=item["config_value"],
                data_type=item.get("data_type", "STRING"),
                description=item.get("description"),
                is_active=item.get("is_active", True),
                is_deleted=False,
            )
            db.add(config)
            count += 1
            logger.info(f"Đã thêm cấu hình: {item['config_key']} = {item['config_value']}")
        else:
            updated = False
            if existing.is_deleted:
                existing.is_deleted = False
                existing.deleted_at = None
                updated = True
            if not existing.is_active and item.get("is_active", True):
                existing.is_active = True
                updated = True
            if not existing.description and item.get("description"):
                existing.description = item.get("description")
                updated = True
            if existing.data_type != item.get("data_type", "STRING"):
                existing.data_type = item.get("data_type", "STRING")
                updated = True
            if updated:
                logger.info(f"Đã cập nhật cấu hình: {item['config_key']}")
    db.commit()
    logger.info(f"Hoàn thành khởi tạo cấu hình hệ thống. Đã xử lý {len(SEED_SYSTEM_CONFIGS)} cấu hình.")
    return count


def seed_system_configs(db: Session = None) -> int:
    """Nạp danh sách cấu hình hệ thống ban đầu vào cơ sở dữ liệu (idempotent)."""
    if db is not None:
        return _run_seed_on_session(db)

    with get_db_context() as session:
        return _run_seed_on_session(session)


if __name__ == "__main__":
    seed_system_configs()
