import argparse
import json
import os
import sys
import httpx

def main():
    parser = argparse.ArgumentParser(description="Kiểm thử nghiệm thu Nghị định 253/2026/NĐ-CP theo đặc tả §13.3")
    parser.add_argument("--pdf", required=True, help="Đường dẫn tới file PDF Nghị định 253 (61 trang)")
    parser.add_argument("--url", default="http://localhost:8000/api/law-changesets/extract", help="URL của endpoint trích xuất")
    parser.add_argument("--context", default=None, help="Đường dẫn file nd253_request_context.json")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"[LỖI] Không tìm thấy file PDF: {args.pdf}")
        sys.exit(1)

    context_path = args.context
    if not context_path:
        default_context = os.path.join(os.path.dirname(__file__), "fixtures", "law_changeset", "nd253_request_context.json")
        if os.path.exists(default_context):
            context_path = default_context
        else:
            print("[LỖI] Không tìm thấy file fixture nd253_request_context.json")
            sys.exit(1)

    with open(context_path, "r", encoding="utf-8") as f:
        context_str = f.read()

    print(f"[*] Đang gửi request tới {args.url}...")
    print(f"[*] File PDF: {args.pdf} ({os.path.getsize(args.pdf) / (1024*1024):.2f} MB)")
    print("[*] Chờ AI phân tích (có thể mất từ 30s đến 2 phút tùy độ lớn file scan)...")

    with open(args.pdf, "rb") as f:
        file_bytes = f.read()

    try:
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(
                args.url,
                files={"file": (os.path.basename(args.pdf), file_bytes, "application/pdf")},
                data={"context": context_str},
            )
    except Exception as e:
        print(f"[LỖI] Gặp lỗi khi kết nối tới endpoint: {e}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[LỖI] Server trả về mã HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    if data.get("status") != "SUCCESS":
        print(f"[THẤT BẠI] Extraction FAILED:")
        print(f"  Mã lỗi: {data.get('errorCode')}")
        print(f"  Nội dung: {data.get('errorMessage')}")
        sys.exit(1)

    result = data.get("result", {})
    coverage = result.get("coverage", {})
    operations = result.get("operations", [])
    relations = result.get("relations", [])

    print("\n" + "="*70)
    print("           BÁO CÁO NGHIỆM THU NGHỊ ĐỊNH 253/2026/NĐ-CP")
    print("="*70)

    # 1. Tiêu chí 1: Coverage
    pages_read = coverage.get("pagesRead", 0)
    total_pages = coverage.get("totalPages", 0)
    mode = coverage.get("mode")
    print(f"\n1. TIÊU CHÍ ĐỘ BAO PHỦ TRANG (COVERAGE):")
    print(f"   - Tổng số trang: {total_pages}")
    print(f"   - Số trang đọc được: {pages_read}")
    print(f"   - Chế độ đọc: {mode}")
    if pages_read == 61:
        print("   => [ĐẠT] Đã đọc trọn vẹn 61 trang (không bị cắt trang như code cũ).")
    else:
        print(f"   => [CẢNH BÁO/KHÔNG ĐẠT] pagesRead = {pages_read} (Kỳ vọng: 61).")

    # 2. Tiêu chí 2: Không được có (AI không được bịa lại luật cũ)
    forbidden_codes = [
        "PIT_TAX_SCHEDULE",
        "PIT_DEDUCTION_PERSONAL",
        "PIT_DEDUCTION_DEPENDENT",
        "PIT_DEPENDENT_MAX_MONTHLY_INCOME"
    ]
    found_forbidden = [op for op in operations if op.get("ruleCode") in forbidden_codes]
    print(f"\n2. TIÊU CHÍ KHÔNG ĐƯỢC CÓ (PHÒNG NGỪA AI BỊA SỐ CỦA LUẬT):")
    if not found_forbidden:
        print("   => [ĐẠT] Hoàn toàn không có dòng nào cho biểu thuế, 15.5tr, 6.2tr hay thu nhập tối đa.")
    else:
        print(f"   => [KHÔNG ĐẠT] Phát hiện các dòng không hợp lệ do AI sinh ra:")
        for op in found_forbidden:
            print(f"      - {op.get('op')} {op.get('ruleCode')}")

    # 3. Tiêu chí 3: Đủ 6 dòng "Phải có" ở §13.3
    print(f"\n3. TIÊU CHÍ 6 DÒNG 'PHẢI CÓ' (§13.3):")
    def find_op(code):
        return [o for o in operations if o.get("ruleCode") == code]

    checks = [
        ("PIT_DEDUCTION_MEDICAL", "23.000.000 VND/year (Y tế)", lambda ops: any(o.get("after", {}).get("valueNumber") == 23000000 for o in ops)),
        ("PIT_DEDUCTION_EDUCATION", "24.000.000 VND/year (Giáo dục)", lambda ops: any(o.get("after", {}).get("valueNumber") == 24000000 for o in ops)),
        ("PIT_DEDUCTION_VOLUNTARY_INSURANCE_CAP", "3.000.000 VND/month (Hưu trí tự nguyện)", lambda ops: any(o.get("after", {}).get("valueNumber") == 3000000 for o in ops)),
        ("PIT_WITHHOLD_CASUAL_MIN_PAYMENT", "5.000.000 VND/payment (Khấu trừ vãng lai)", lambda ops: any(o.get("after", {}).get("valueNumber") == 5000000 for o in ops)),
        ("PIT_WITHHOLD_CASUAL_RATE", "RECITE 0.1 (Thuế suất 10%)", lambda ops: any(o.get("op") == "RECITE" for o in ops)),
        ("PIT_SETTLEMENT_SELF_REQUIRED_IF_MED_EDU", "FLAG (Cờ tự quyết toán khi giảm trừ y tế/GD)", lambda ops: len(ops) > 0),
    ]

    for code, desc, validator in checks:
        matching = find_op(code)
        if matching and validator(matching):
            op_item = matching[0]
            cit = op_item.get("citation", {})
            print(f"   [ĐẠT] {code}: {desc}")
            print(f"         Căn cứ: Điều {cit.get('article')}, khoản {cit.get('clause')}, điểm {cit.get('point')} (Trang {cit.get('page')})")
        elif matching:
            print(f"   [CHƯA CHUẨN] Tìm thấy {code} nhưng giá trị chưa khớp kỳ vọng: {matching}")
        else:
            print(f"   [THIẾU] Không tìm thấy dòng cho mã {code} ({desc})")

    # Quan hệ bãi bỏ / thay thế
    print(f"\n4. CÁC QUAN HỆ VĂN BẢN (RELATIONS):")
    for rel in relations:
        print(f"   - {rel.get('type')} {rel.get('targetDocumentNumber')} | Điều {rel.get('citation', {}).get('article')} (Trang {rel.get('citation', {}).get('page')})")

    print("\n" + "="*70)
    print("Hoàn tất đối chiếu kết quả!")

if __name__ == "__main__":
    main()
