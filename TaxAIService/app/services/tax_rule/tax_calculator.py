from typing import Dict, Any, List, Optional


class TaxCalculator:
    """
    Công cụ tính toán thuế Thu nhập cá nhân (TNCN) chuẩn xác theo quy định pháp luật Việt Nam.
    Hỗ trợ cả quy định hiện hành và Luật Thuế TNCN mới (kỳ áp dụng từ năm 2026).
    """

    # Mức lương cơ sở hiện hành để tính trần bảo hiểm (từ 01/07/2024 là 2.340.000 VND)
    BASE_SALARY = 2_340_000.0
    INSURANCE_CEILING_BASE_MULTIPLE = 20  # Tối đa 20 lần lương cơ sở

    @classmethod
    def calculate_insurance(cls, salary: float) -> float:
        """
        Tính số tiền bảo hiểm bắt buộc người lao động đóng (10.5%: BHXH 8%, BHYT 1.5%, BHTN 1%).
        Có áp dụng mức trần đóng bảo hiểm theo luật.
        """
        ceiling = cls.BASE_SALARY * cls.INSURANCE_CEILING_BASE_MULTIPLE
        salary_for_insurance = min(salary, ceiling)
        return round(salary_for_insurance * 0.105, 0)

    @classmethod
    def calculate_pit(
        cls,
        monthly_salary: float,
        dependents_count: int = 0,
        insurance_amount: Optional[float] = None,
        tax_year: int = 2026,
        ot_salary: float = 0.0,
        ot_exempt_amount: float = 0.0,
        other_deductions: float = 0.0
    ) -> Dict[str, Any]:
        """
        Tính chi tiết thuế TNCN hàng tháng và tiền thực nhận.
        """
        monthly_salary = max(0.0, float(monthly_salary))
        dependents_count = max(0, int(dependents_count))
        tax_year = int(tax_year) if tax_year else 2026
        ot_salary = max(0.0, float(ot_salary))
        ot_exempt_amount = max(0.0, float(ot_exempt_amount))
        other_deductions = max(0.0, float(other_deductions))

        # 1. Tính bảo hiểm
        if insurance_amount is not None:
            actual_insurance = max(0.0, float(insurance_amount))
        else:
            actual_insurance = cls.calculate_insurance(monthly_salary)

        # 2. Xác định mức giảm trừ theo năm áp dụng
        if tax_year >= 2026:
            personal_deduction = 15_500_000.0
            dependent_deduction_per_person = 6_200_000.0
            # Biểu thuế 5 bậc năm 2026
            brackets = [
                {"bracket": 1, "max_limit": 10_000_000.0, "rate": 0.05, "desc": "Đến 10 triệu"},
                {"bracket": 2, "max_limit": 30_000_000.0, "rate": 0.10, "desc": "Trên 10 đến 30 triệu"},
                {"bracket": 3, "max_limit": 50_000_000.0, "rate": 0.20, "desc": "Trên 30 đến 50 triệu"},
                {"bracket": 4, "max_limit": 80_000_000.0, "rate": 0.30, "desc": "Trên 50 đến 80 triệu"},
                {"bracket": 5, "max_limit": float("inf"), "rate": 0.35, "desc": "Trên 80 triệu"},
            ]
        else:
            personal_deduction = 11_000_000.0
            dependent_deduction_per_person = 4_400_000.0
            # Biểu thuế 7 bậc hiện hành
            brackets = [
                {"bracket": 1, "max_limit": 5_000_000.0, "rate": 0.05, "desc": "Đến 5 triệu"},
                {"bracket": 2, "max_limit": 10_000_000.0, "rate": 0.10, "desc": "Trên 5 đến 10 triệu"},
                {"bracket": 3, "max_limit": 18_000_000.0, "rate": 0.15, "desc": "Trên 10 đến 18 triệu"},
                {"bracket": 4, "max_limit": 32_000_000.0, "rate": 0.20, "desc": "Trên 18 đến 32 triệu"},
                {"bracket": 5, "max_limit": 52_000_000.0, "rate": 0.25, "desc": "Trên 32 đến 52 triệu"},
                {"bracket": 6, "max_limit": 80_000_000.0, "rate": 0.30, "desc": "Trên 52 đến 80 triệu"},
                {"bracket": 7, "max_limit": float("inf"), "rate": 0.35, "desc": "Trên 80 triệu"},
            ]

        total_dependents_deduction = dependents_count * dependent_deduction_per_person
        total_deductions = personal_deduction + total_dependents_deduction + actual_insurance + other_deductions

        # 3. Thu nhập chịu thuế = Lương chính + OT - OT miễn thuế
        taxable_gross = monthly_salary + max(0.0, ot_salary - ot_exempt_amount)

        # 4. Thu nhập tính thuế (TNTT)
        assessable_income = max(0.0, taxable_gross - total_deductions)

        # 5. Tính chi tiết từng bậc thuế
        bracket_details = []
        total_tax = 0.0
        remaining_income = assessable_income
        prev_limit = 0.0

        for b in brackets:
            if remaining_income <= 0:
                break

            current_limit = b["max_limit"]
            bracket_span = current_limit - prev_limit

            amount_in_bracket = min(remaining_income, bracket_span)
            tax_in_bracket = amount_in_bracket * b["rate"]

            total_tax += tax_in_bracket
            remaining_income -= amount_in_bracket
            prev_limit = current_limit

            bracket_details.append({
                "bracket": b["bracket"],
                "range_desc": b["desc"],
                "taxable_amount": round(amount_in_bracket, 0),
                "tax_rate_percent": int(b["rate"] * 100),
                "tax_amount": round(tax_in_bracket, 0)
            })

        total_tax = round(total_tax, 0)
        total_income = monthly_salary + ot_salary
        net_income = round(total_income - actual_insurance - total_tax, 0)

        return {
            "tax_year": tax_year,
            "monthly_salary": monthly_salary,
            "ot_salary": ot_salary,
            "ot_exempt_amount": ot_exempt_amount,
            "total_income": total_income,
            "insurance_deduction": actual_insurance,
            "personal_deduction": personal_deduction,
            "dependents_count": dependents_count,
            "dependents_deduction": total_dependents_deduction,
            "other_deductions": other_deductions,
            "total_deductions": total_deductions,
            "assessable_income": round(assessable_income, 0),
            "bracket_details": bracket_details,
            "total_tax": total_tax,
            "net_income": net_income
        }
