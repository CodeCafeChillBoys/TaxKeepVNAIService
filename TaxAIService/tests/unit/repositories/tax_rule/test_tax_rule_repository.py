import uuid
import pytest
from unittest.mock import MagicMock

from app.enum.tax_rule_enum import TaxRuleStatus
from app.models.dependent_rule import DependentRule
from app.models.tax_rule import TaxRule
from app.models.tax_rule_set import TaxRuleSet
from app.repositories.tax_rule.tax_rule_repository import TaxRuleRepository


# ==============================================================================
# Test 1: get_by_id() với chuỗi UUID hợp lệ vs không hợp lệ
# ==============================================================================
def test_get_by_id_with_valid_uuid_string():
    """
    Nếu truyền vào là 1 chuỗi string nhưng đúng format UUID,
    hàm phải tự parse sang UUID và query TaxRuleSet.
    """
    # A
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    valid_uuid = uuid.uuid4()
    # A
    repo.get_by_id(str(valid_uuid))
    # A
    # Đảm bảo query bảng TaxRuleSet
    mock_db.query.assert_called_once_with(TaxRuleSet)
    
    
def test_get_by_id_with_invalid_uuid_string():
    """
    Nếu truyền chuỗi rác không phải UUID (vd: 'abc-123'),
    hàm phải bắt lỗi ValueError và trả về None ngay, KHÔNG query DB.
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    result = repo.get_by_id("khong-phai-uuid")
    assert result is None
    # Xác nhận DB không bị query thừa
    mock_db.query.assert_not_called()
    

# ==============================================================================
# Test 2: get_rule_set_by_year() - Tìm bộ luật theo năm tính thuế
# ==============================================================================
def test_get_rule_set_by_year():
    """
    Tìm kiếm TaxRuleSet theo năm (ví dụ: năm 2026).
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    expected_rule_set = TaxRuleSet(name="Luật thuế 2026", tax_year=2026)
    
    # Giả lập query.filter().first() trả về expected_rule_set
    mock_db.query.return_value.filter.return_value.first.return_value = expected_rule_set
    result = repo.get_rule_set_by_year(2026)
    mock_db.query.assert_called_once_with(TaxRuleSet)
    assert result == expected_rule_set
    assert result.tax_year == 2026
    
# ==============================================================================
# Test 3: get_all_rule_sets() - Lấy tất cả và sắp xếp giảm dần theo năm
# ==============================================================================
def test_get_all_rule_sets():
    """
    Lấy toàn bộ TaxRuleSet, sắp xếp năm mới nhất lên đầu (order_by desc).
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    dummy_rule_sets = [
        TaxRuleSet(name="Luật thuế 2026", tax_year=2026),
        TaxRuleSet(name="Luật thuế 2025", tax_year=2025)
    ]
    mock_db.query.return_value.order_by.return_value.all.return_value = dummy_rule_sets
    result = repo.get_all_rule_sets()
    mock_db.query.assert_called_once_with(TaxRuleSet)
    assert result == dummy_rule_sets
    assert len(result) == 2
    
    
# ==============================================================================
# Test 4: check_existing_rule_codes() - Kiểm tra trùng mã code
# ==============================================================================
def test_check_existing_rule_codes_empty_list():
    """
    Nếu truyền danh sách rỗng [], hàm phải trả về False ngay mà không query DB.
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    assert repo.check_existing_rule_codes([]) is False
    mock_db.query.assert_not_called()


def test_check_existing_rule_codes_found():
    """
    Nếu mã code đã tồn tại trong bảng TaxRule, trả về True.
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    existing_rule = TaxRule(rule_code="PIT_PERSONAL_DEDUCTION", rule_name="Giảm trừ gia cảnh bản thân", rule_type="DEDUCTION")
    # Giả lập tìm thấy 1 rule
    mock_db.query.return_value.filter.return_value.first.return_value = existing_rule
    result = repo.check_existing_rule_codes(["PIT_PERSONAL_DEDUCTION"])
    assert result is True
    mock_db.query.assert_called_once_with(TaxRule)
    
# ==============================================================================
# Test 5: get_tax_rule_set_detail() - Lấy chi tiết bộ luật cùng các bảng con
# ==============================================================================
def test_get_tax_rule_set_detail_not_found():
    """
    Khi ID bộ luật không tồn tại trong DB, hàm trả về None.
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    # Giả lập get_rule_set_by_id trả về None
    mock_db.query.return_value.filter.return_value.first.return_value = None
    result = repo.get_tax_rule_set_detail(uuid.uuid4())
    assert result is None


def test_get_tax_rule_set_detail_success():
    """
    Khi tìm thấy bộ luật:
    - Trả về tuple (rule_set, rules, dep_rules)
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    
    rule_set_id = uuid.uuid4()
    dummy_rule_set = TaxRuleSet(rule_set_id=rule_set_id, name="Luật 2026", tax_year=2026)
    
    rule_id = uuid.uuid4()
    dummy_rule = TaxRule(rule_id=rule_id, rule_set_id=rule_set_id, rule_code="PIT_01", rule_name="Giảm trừ", rule_type="DEDUCTION")
    dummy_dep_rule = DependentRule(id=uuid.uuid4(), rule_id=rule_id, dependent_type="CHILD", name="Con dưới 18")
    # Giả lập:
    # 1. Query TaxRuleSet -> trả về dummy_rule_set
    # 2. Query TaxRule -> trả về [dummy_rule]
    # 3. Query DependentRule -> trả về [dummy_dep_rule]
    mock_db.query.return_value.filter.return_value.first.return_value = dummy_rule_set
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        [dummy_rule],      # Lần gọi .all() đầu tiên (cho TaxRule)
        [dummy_dep_rule]   # Lần gọi .all() thứ hai (cho DependentRule)
    ]
    result = repo.get_tax_rule_set_detail(rule_set_id)
    assert result is not None
    rs, rules, dep_rules = result
    assert rs == dummy_rule_set
    assert len(rules) == 1
    assert len(dep_rules) == 1




# ==============================================================================
# Test 6: create_tax_rule_set() - Tạo bộ luật mới kèm các bảng con
# ==============================================================================
def test_create_tax_rule_set_success():
    """
    Quy trình tạo:
    1. db.add(rule_set)
    2. db.flush() (để sinh ID cho cha)
    3. Gán rule_set_id vào từng rule con và db.add_all(rules)
    4. db.add_all(dependent_rules)
    5. db.commit() và db.refresh(rule_set)
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    rule_set = TaxRuleSet(rule_set_id=uuid.uuid4(), name="Luật 2026", tax_year=2026)
    rules = [TaxRule(rule_code="RULE_1", rule_name="Luật 1", rule_type="DEDUCTION")]
    dep_rules = [DependentRule(dependent_type="CHILD", name="Con nhỏ")]
    # Act
    rs, r_list, d_list = repo.create_tax_rule_set(rule_set, rules, dep_rules)
    # Assert
    mock_db.add.assert_called_once_with(rule_set)
    assert mock_db.flush.call_count == 2          # Gọi flush 2 lần
    assert mock_db.add_all.call_count == 2        # Thêm rules và dependent_rules
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(rule_set)
    assert r_list[0].rule_set_id == rule_set.rule_set_id
    
def test_create_tax_rule_set_rollback_on_error():
    """
    Nếu trong quá trình tạo xảy ra lỗi (ví dụ commit thất bại):
    - Bắt buộc phải gọi db.rollback() để không làm bẩn Database
    - Phải re-raise lỗi ra ngoài
    """
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("Lỗi ghi DB")  # Giả lập lỗi tại bước commit
    repo = TaxRuleRepository(db=mock_db)
    rule_set = TaxRuleSet(name="Luật lỗi", tax_year=2026)
    # Kiểm tra xem có văng Exception và rollback không
    with pytest.raises(Exception, match="Lỗi ghi DB"):
        repo.create_tax_rule_set(rule_set, [], [])
    mock_db.rollback.assert_called_once()
    
    
# ==============================================================================
# Test 7: get_tax_rule_set_detail_by_year()
# ==============================================================================
def test_get_tax_rule_set_detail_by_year_not_found():
    """Khi năm tính thuế không tồn tại, trả về None."""
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = repo.get_tax_rule_set_detail_by_year(2099)
    assert result is None


def test_get_tax_rule_set_detail_by_year_success():
    """Khi tìm thấy năm tính thuế, gọi tiếp get_tax_rule_set_detail để lấy chi tiết."""
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    rule_set_id = uuid.uuid4()
    dummy_rs = TaxRuleSet(rule_set_id=rule_set_id, tax_year=2026, name="Luật 2026")

    # Giả lập get_rule_set_by_year tìm thấy dummy_rs
    repo.get_rule_set_by_year = MagicMock(return_value=dummy_rs)
    # Giả lập get_tax_rule_set_detail trả về tuple kết quả
    repo.get_tax_rule_set_detail = MagicMock(return_value=(dummy_rs, [], []))

    result = repo.get_tax_rule_set_detail_by_year(2026)

    assert result == (dummy_rs, [], [])
    repo.get_tax_rule_set_detail.assert_called_once_with(rule_set_id)



# ==============================================================================
# Test 8: approve_tax_rule_set() - Admin phê duyệt luật
# ==============================================================================
def test_approve_tax_rule_set_not_found():
    """Nếu ID bộ luật không tồn tại, trả về None."""
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = repo.approve_tax_rule_set(uuid.uuid4())
    assert result is None


def test_approve_tax_rule_set_success():
    """
    Khi phê duyệt thành công:
    - Status của TaxRuleSet đổi thành ACTIVE
    - Gán approved_by = admin_id
    - Cascade cập nhật TaxRule và DependentRule thành ACTIVE
    - db.commit() và db.refresh()
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    
    rule_set_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    rule_set = TaxRuleSet(rule_set_id=rule_set_id, status=TaxRuleStatus.DRAFT.value)

    # Giả lập tìm thấy rule_set
    mock_db.query.return_value.filter.return_value.first.return_value = rule_set
    # Giả lập tìm thấy danh sách rule_id con
    mock_db.query.return_value.filter.return_value.all.return_value = [(uuid.uuid4(),)]

    result = repo.approve_tax_rule_set(rule_set_id, admin_id=admin_id)

    assert result is not None
    assert result.status == TaxRuleStatus.ACTIVE.value
    assert result.approved_by == admin_id
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(rule_set)


def test_approve_tax_rule_set_rollback_on_error():
    """Nếu xảy ra lỗi DB khi approve, phải rollback và ném lỗi."""
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("DB Lock Error")
    repo = TaxRuleRepository(db=mock_db)

    rule_set = TaxRuleSet(rule_set_id=uuid.uuid4())
    mock_db.query.return_value.filter.return_value.first.return_value = rule_set

    with pytest.raises(Exception, match="DB Lock Error"):
        repo.approve_tax_rule_set(rule_set.rule_set_id)

    mock_db.rollback.assert_called_once()
    
    
# ==============================================================================
# Test 9: update_tax_rule_set() - Cập nhật bộ luật
# ==============================================================================
def test_update_tax_rule_set_not_found():
    """Khi ID bộ luật không tồn tại, trả về None."""
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = repo.update_tax_rule_set(uuid.uuid4(), name="Tên mới")
    assert result is None


def test_update_tax_rule_set_basic_fields():
    """Cập nhật các trường cơ bản của TaxRuleSet: name, tax_year, status..."""
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    
    rule_set_id = uuid.uuid4()
    rule_set = TaxRuleSet(rule_set_id=rule_set_id, name="Tên cũ", tax_year=2025)

    mock_db.query.return_value.filter.return_value.first.return_value = rule_set
    # Giả lập hàm get_tax_rule_set_detail ở cuối
    repo.get_tax_rule_set_detail = MagicMock(return_value=(rule_set, [], []))

    result = repo.update_tax_rule_set(
        rule_set_id=rule_set_id,
        name="Tên mới 2026",
        tax_year=2026,
        status="ACTIVE"
    )

    assert rule_set.name == "Tên mới 2026"
    assert rule_set.tax_year == 2026
    assert rule_set.status == "ACTIVE"
    mock_db.commit.assert_called_once()


def test_update_tax_rule_set_with_new_rules():
    """
    Khi truyền danh sách tax_rules mới:
    - Nếu rule chưa có trong DB, hàm tạo mới TaxRule và db.add()
    """
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)
    
    rule_set_id = uuid.uuid4()
    rule_set = TaxRuleSet(rule_set_id=rule_set_id, name="Luật 2026")
    mock_db.query.return_value.filter.return_value.first.return_value = rule_set
    # Giả lập DB hiện tại chưa có rule nào
    mock_db.query.return_value.filter.return_value.all.return_value = []
    repo.get_tax_rule_set_detail = MagicMock(return_value=(rule_set, [], []))

    new_rule_data = [
        {"rule_code": "PIT_NEW", "rule_name": "Quy tắc mới", "value": 15000000.0}
    ]

    repo.update_tax_rule_set(rule_set_id=rule_set_id, tax_rules=new_rule_data)

    # db.add phải được gọi để thêm TaxRule mới
    mock_db.add.assert_called()
    mock_db.commit.assert_called_once()


def test_update_tax_rule_set_rollback_on_error():
    """Nếu commit thất bại khi update, phải rollback và ném lỗi."""
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("Update Failed")
    repo = TaxRuleRepository(db=mock_db)

    rule_set = TaxRuleSet(rule_set_id=uuid.uuid4())
    mock_db.query.return_value.filter.return_value.first.return_value = rule_set

    with pytest.raises(Exception, match="Update Failed"):
        repo.update_tax_rule_set(rule_set.rule_set_id, name="Lỗi")

    mock_db.rollback.assert_called_once()



# ==============================================================================
# Test: Bao phủ cả 2 nhánh UPDATE và ADD cho dependent_rules
# ==============================================================================
def test_update_tax_rule_set_both_update_and_add_dependent_rules():
    # --------------------------------------------------------------------------
    # BƯỚC 1: ARRANGE (Chuẩn bị dữ liệu)
    # --------------------------------------------------------------------------
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)

    rule_set_id = uuid.uuid4()
    parent_rule_id = uuid.uuid4()
    dep_id = uuid.uuid4()  # <-- ID này đại diện cho người ĐÃ CÓ trong DB

    rule_set = TaxRuleSet(rule_set_id=rule_set_id, name="Luật thuế 2026")
    parent_rule = TaxRule(rule_id=parent_rule_id, rule_set_id=rule_set_id, rule_code="PIT_DEDUCTION_DEPENDENT")
    
    # 1. Tạo người cũ trong DB (để test UPDATE)
    existing_dep = DependentRule(
        id=dep_id,
        rule_id=parent_rule_id,
        dependent_type="CHILD",
        name="Con nhỏ (Tên cũ)",
        max_age=10,
        is_studying=False
    )

    # 2. Dạy cho mock_db trả về dữ liệu khi code query:
    mock_db.query.return_value.filter.return_value.first.return_value = rule_set
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        [parent_rule],   # Query 1: Lấy danh sách rule cha
        [existing_dep]   # Query 2: Lấy danh sách người phụ thuộc cũ trong DB
    ]
    repo.get_tax_rule_set_detail = MagicMock(return_value=(rule_set, [], []))

    # --------------------------------------------------------------------------
    # BƯỚC 2: CHUẨN BỊ MẢNG GỒM CẢ 2 NGƯỜI
    # --------------------------------------------------------------------------
    dependent_rules_payload = [
        # 👉 NGƯỜI 1: Có "id" -> Ép code chạy vào nhánh UPDATE
        {
            "id": dep_id,                     # Trùng ID với existing_dep
            "name": "Con nhỏ (Đã sửa tên)",
            "dependent_type": "ADULT_CHILD",
            "max_age": 18,
            "max_monthly_income": 1000000.0,
            "is_studying": True,
            "is_disabled": False,
            "conditions": {"student": True},
            "status": "ACTIVE"
        },
        # 👉 NGƯỜI 2: Không có "id" -> Ép code chạy vào nhánh ADD (elif parent_rule_id)
        {
            "name": "Cha mẹ già (Người mới toanh)",
            "dependent_type": "PARENT",
            "max_age": 60,
            "max_monthly_income": 500000.0,
            "is_studying": False,
            "is_disabled": True,
            "status": "DRAFT"
        }
    ]

    # --------------------------------------------------------------------------
    # BƯỚC 3: ACT (Thực thi hàm)
    # --------------------------------------------------------------------------
    repo.update_tax_rule_set(
        rule_set_id=rule_set_id,
        dependent_rules=dependent_rules_payload
    )

    # --------------------------------------------------------------------------
    # BƯỚC 4: ASSERT (Kiểm tra xem cả 2 nhánh đã chạy chưa)
    # --------------------------------------------------------------------------
    # 1. Kiểm tra nhánh UPDATE: Người cũ existing_dep đã bị đổi tên và tuổi chưa?
    assert existing_dep.name == "Con nhỏ (Đã sửa tên)"
    assert existing_dep.dependent_type == "ADULT_CHILD"
    assert existing_dep.max_age == 18
    assert existing_dep.is_studying is True

    # 2. Kiểm tra nhánh ADD: mock_db có được gọi hàm add() để lưu người mới không?
    mock_db.add.assert_called()

    # 3. Đảm bảo đã lưu (commit)
    mock_db.commit.assert_called_once()


def test_update_tax_rule_set_update_existing_tax_rules_all_fields():
    """Bao phủ cập nhật toàn bộ các trường của TaxRule đã tồn tại (theo rule_id và theo rule_code)."""
    mock_db = MagicMock()
    repo = TaxRuleRepository(db=mock_db)

    rule_set_id = uuid.uuid4()
    rule_id_1 = uuid.uuid4()
    rule_id_2 = uuid.uuid4()

    rule_set = TaxRuleSet(rule_set_id=rule_set_id, name="Luật 2026")
    r1 = TaxRule(rule_id=rule_id_1, rule_set_id=rule_set_id, rule_code="CODE_1")
    r2 = TaxRule(rule_id=rule_id_2, rule_set_id=rule_set_id, rule_code="CODE_2")

    mock_db.query.return_value.filter.return_value.first.return_value = rule_set
    mock_db.query.return_value.filter.return_value.all.return_value = [r1, r2]
    repo.get_tax_rule_set_detail = MagicMock(return_value=(rule_set, [r1, r2], []))

    tax_rules_payload = [
        # Khớp theo rule_id
        {
            "rule_id": rule_id_1,
            "rule_code": "CODE_1_NEW",
            "rule_name": "Tên 1",
            "rule_type": "DEDUCTION",
            "condition": {"key": "val"},
            "value": 100.0,
            "unit": "VND",
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "legal_document": "Nghị định 01",
            "article": "1",
            "clause": "2",
            "point": "a",
            "source_url": "https://chinhphu.vn",
            "status": "ACTIVE"
        },
        # Khớp theo rule_code (không có rule_id)
        {
            "rule_code": "CODE_2",
            "rule_name": "Tên 2",
            "rule_type": "TAX_BRACKET",
            "condition": "custom_cond",
            "value": 200.0,
            "unit": "%",
            "status": "DRAFT"
        }
    ]

    repo.update_tax_rule_set(
        rule_set_id=rule_set_id,
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        tax_rules=tax_rules_payload
    )

    assert rule_set.effective_from == "2026-01-01"
    assert rule_set.effective_to == "2026-12-31"

    assert r1.rule_code == "CODE_1_NEW"
    assert r1.rule_name == "Tên 1"
    assert r1.value == 100.0
    assert r1.legal_document == "Nghị định 01"
    assert r1.status == "ACTIVE"

    assert r2.rule_name == "Tên 2"
    assert r2.value == 200.0
    assert r2.status == "DRAFT"



