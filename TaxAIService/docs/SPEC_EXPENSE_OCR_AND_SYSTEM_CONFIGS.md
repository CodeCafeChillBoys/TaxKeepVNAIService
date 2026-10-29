# TÀI LIỆU ĐẶC TẢ NGHIỆP VỤ PHÂN HỆ
## MODULE: KHAI BÁO HÓA ĐƠN CHI PHÍ HỢP LỆ & QUẢN TRỊ CẤU HÌNH HỆ THỐNG ĐỘNG (EXPENSE OCR & DYNAMIC SYSTEM CONFIGURATIONS)
**Nhánh phát triển:** `feature/implementation_expenseOcrAndSystemConfigs`  
**Dự án:** TaxKeep VN - Dịch vụ Trí tuệ Nhân tạo Hỗ trợ Thuế TNCN (TaxAIService)  
**Ngày hoàn thiện đặc tả:** 28/09/2026  
**Trạng thái:** Đặc tả nghiệp vụ mức Conceptual / Sẵn sàng Review & Thống nhất  

---

## 1. TỔNG QUAN PHÂN HỆ

Trong hệ thống thuế thu nhập cá nhân và quản trị chi tiêu cá nhân TaxKeep VN, người nộp thuế có quyền kê khai các khoản chi phí hợp lệ được trừ khi tính thuế hoặc phục vụ việc quản lý ngân sách cá nhân/hộ kinh doanh, bao gồm: viện phí y tế khám chữa bệnh, biên lai học phí đào tạo, chứng từ đóng góp từ thiện nhân đạo, và phí bảo hiểm nhân thọ/hưu trí tự nguyện.

Phân hệ **Khai báo hóa đơn chi phí hợp lệ & Quản trị cấu hình hệ thống động** cung cấp giải pháp bóc tách tự động toàn diện từ tệp hóa đơn (ảnh chụp hoặc tệp điện tử PDF), nhận dạng danh mục hàng hóa chi tiết theo từng dòng (Line Items), thẩm định ngưỡng an toàn 3 tầng, đối soát tính cân đối tài chính và niên độ tính thuế. Toàn bộ chính sách kiểm soát và ngưỡng tin cậy được quản trị động bởi Quản trị viên, không bị phụ thuộc vào việc sửa đổi mã nguồn phần mềm.

---

## 2. DANH SÁCH CÁC ĐẶC TẢ NGHIỆP VỤ CỐT LÕI

1. [Đặc tả 1: Tiếp nhận và phân loại chứng từ chi phí](#đặc-tả-1-tiếp-nhận-và-phân-loại-chứng-từ-chi-phí)
2. [Đặc tả 2: Bóc tách thông tin hóa đơn và bảng chi tiết hàng hóa/dịch vụ](#đặc-tả-2-bóc-tách-thông-tin-hóa-đơn-và-bảng-chi-tiết-hàng-hóadịch-vụ)
3. [Đặc tả 3: Thẩm định ngưỡng tin cậy 3 tầng và bảo vệ trường cốt lõi](#đặc-tả-3-thẩm-định-ngưỡng-tin-cậy-3-tầng-và-bảo-vệ-trường-cốt-lõi)
4. [Đặc tả 4: Đối soát niên độ tính thuế và tính nhất quán tài chính](#đặc-tả-4-đối-soát-niên-độ-tính-thuế-và-tính-nhất-quán-tài-chính)
5. [Đặc tả 5: Hiệu chỉnh đối chiếu trực quan và xác nhận ghi nhận chi phí](#đặc-tả-5-hiệu-chỉnh-đối-chiếu-trực-quan-và-xác-nhận-ghi-nhận-chi-phí)
6. [Đặc tả 6: Quản trị cấu hình hệ thống & chính sách chi phí động](#đặc-tả-6-quản-trị-cấu-hình-hệ-thống--chính-sách-chi-phí-động)

---

### ĐẶC TẢ 1: TIẾP NHẬN VÀ PHÂN LOẠI CHỨNG TỪ CHI PHÍ

#### 1. Tên chức năng
Tiếp nhận và phân loại chứng từ chi phí (Expense Document Ingestion & Classification).

#### 2. Mục đích
Tiếp nhận tài liệu chi phí do người nộp thuế tải lên, tự động xác định chứng từ thuộc danh mục chi phí hợp lệ nào (hoặc từ chối các loại chứng từ rác/không thuộc diện được khấu trừ thuế).

#### 3. Actor
- Người nộp thuế (User)
- Hệ thống phân loại AI (System)

#### 4. Điều kiện trước
- User đã đăng nhập và truy cập vào mục "Kê khai chi phí giảm trừ / Chi tiêu".
- Hệ thống đã nạp danh mục các loại chi phí hợp lệ từ cấu hình quản trị.

#### 5. Luồng chính
1. User nhấn nút "Tải lên hóa đơn chi phí", chọn tệp hình ảnh (JPEG, PNG) hoặc tệp hóa đơn điện tử PDF.
2. User có thể chọn trước danh mục dự kiến (ví dụ: Viện phí, Học phí) hoặc để chế độ "Hệ thống tự động nhận diện".
3. Hệ thống tiếp nhận tệp và phân tích nội dung hình ảnh/văn bản để xác định bản chất của chứng từ:
   - *Hóa đơn y tế, viện phí, thuốc men (`MEDICAL_EXPENSE_INVOICE`).*
   - *Biên lai / Hóa đơn học phí, đào tạo (`EDUCATION_FEE_INVOICE`).*
   - *Chứng từ đóng góp từ thiện, nhân đạo, khuyến học (`CHARITY_DONATION_RECEIPT`).*
   - *Biên lai phí bảo hiểm nhân thọ / hưu trí tự nguyện (`INSURANCE_PREMIUM_RECEIPT`).*
4. Hệ thống kiểm tra xem chứng từ có thuộc danh mục được phép khấu trừ theo quy định hiện hành hay không.
5. Nếu thuộc danh mục hợp lệ, Hệ thống gán mã loại tài liệu tương ứng kèm lý do nhận diện và chuyển sang luồng bóc tách dữ liệu chi tiết.

#### 6. Luồng thay thế / Ngoại lệ
- **Tài liệu không thuộc diện hỗ trợ / Chứng từ sinh hoạt cá nhân thông thường:** Tài liệu tải lên là hóa đơn ăn uống nhà hàng, cà phê, vé xem phim, hóa đơn siêu thị mua sắm tiêu dùng, hoặc ảnh phong cảnh không liên quan -> Hệ thống tự động phân loại thành **"Tài liệu không hỗ trợ" (`UNSUPPORTED`)**, hiển thị thông báo giải thích rõ lý do chứng từ này không thuộc diện được khấu trừ thuế TNCN và dừng quy trình.
- **Tệp bị mờ toàn phần hoặc hỏng định dạng:** Hệ thống thông báo tệp không thể nhận diện được nội dung và yêu cầu User tải lên tệp mới rõ nét hơn.

#### 7. Kết quả sau khi thực hiện
- Tài liệu được phân loại chính xác vào danh mục chi phí tương ứng, sẵn sàng cho bước bóc tách dữ liệu.
- Các tài liệu rác hoặc không hợp lệ bị loại bỏ ngay từ đầu, giảm thiểu tải xử lý cho hệ thống và thời gian của người dùng.

#### 8. Business Rules
- Chỉ các khoản chi phí thuộc danh mục pháp luật thuế TNCN cho phép giảm trừ hoặc thuộc danh mục quản lý tài chính được cấu hình bởi Quản trị viên mới được chấp nhận tiếp tục xử lý.
- Mọi trường hợp phân loại `UNSUPPORTED` phải kèm theo diễn giải ngắn gọn bằng tiếng Việt để người dùng hiểu vì sao chứng từ bị từ chối.

#### 9. Điểm chưa thống nhất
- Người dùng có được quyền ghi đè (Override) danh mục nếu cho rằng AI phân loại nhầm danh mục chi phí hay không?

---

### ĐẶC TẢ 2: BÓC TÁCH THÔNG TIN HÓA ĐƠN VÀ BẢNG CHI TIẾT HÀNG HÓA/DỊCH VỤ

#### 1. Tên chức năng
Bóc tách thông tin hóa đơn và bảng chi tiết hàng hóa/dịch vụ (Invoice Metadata & Line Items Extraction).

#### 2. Mục đích
Tự động trích xuất toàn bộ thông tin hành chính, pháp lý, tài chính của hóa đơn và bóc tách chính xác từng dòng hàng hóa/dịch vụ trong bảng chi tiết kèm tọa độ nhận diện trực quan.

#### 3. Actor
- Hệ thống AI bóc tách (System AI Service)
- Người nộp thuế (User)

#### 4. Điều kiện trước
- Chứng từ đã được phân loại thành công vào một danh mục hợp lệ.

#### 5. Luồng chính
1. Hệ thống thực hiện bóc tách khối **Thông tin đơn vị phát hành (Bên bán / Bệnh viện / Nhà trường):**
   - Tên cơ sở/đơn vị phát hành.
   - Mã số thuế (MST) của bên bán.
   - Địa chỉ và số điện thoại liên hệ.
2. Hệ thống bóc tách khối **Thông tin định danh hóa đơn:**
   - Ký hiệu mẫu số và ký hiệu hóa đơn (Series).
   - Số hóa đơn (Invoice Number).
   - Ngày, tháng, năm lập hóa đơn.
   - Đường link tra cứu và mã tra cứu hóa đơn điện tử (nếu là hóa đơn điện tử).
3. Hệ thống bóc tách khối **Thông tin khách hàng / người thụ hưởng (Bên mua):**
   - Họ tên người mua hàng / bệnh nhân / học sinh.
   - Mã định danh cá nhân / CCCD / Mã số thuế cá nhân.
   - Địa chỉ thường trú/liên hệ.
4. Hệ thống bóc tách khối **Thông tin tài chính tổng hợp:**
   - Tổng tiền chưa thuế, tiền thuế GTGT (nếu có), và tổng số tiền thanh toán thực tế (bằng số và bằng chữ).
5. Hệ thống trích xuất **Bảng danh mục chi tiết hàng hóa / dịch vụ (Line Items):**
   - Số thứ tự từng dòng.
   - Tên danh mục dịch vụ / hàng hóa / tên thuốc / khoản phí đào tạo.
   - Đơn vị tính, số lượng, đơn giá và thành tiền của từng dòng.
6. Hệ thống tính toán điểm tin cậy độc lập (Field-level Confidence) và ghi nhận tọa độ khung bao trực quan (Bounding Box) cho các trường thông tin chính để hỗ trợ hiển thị đối chiếu.

#### 6. Luồng thay thế / Ngoại lệ
- **Hóa đơn không có bảng chi tiết (Hóa đơn tóm tắt/Phiếu thu một khoản gộp):** Hệ thống chỉ bóc tách tổng số tiền và nội dung diễn giải chung, đánh dấu danh mục bảng hàng hóa là dạng đơn lẻ (Single item).
- **Hóa đơn dài nhiều trang:** Hệ thống tổng hợp dữ liệu qua các trang, nối các dòng hàng hóa chi tiết thành một danh sách duy nhất và kiểm tra khớp tổng tiền ở trang cuối cùng.

#### 7. Kết quả sau khi thực hiện
- Toàn bộ nội dung hóa đơn và bảng kê chi tiết được chuyển đổi thành dữ liệu có cấu trúc hoàn chỉnh.
- Tọa độ hiển thị được lưu lại để phục vụ tính năng soi sáng vị trí thông tin trên ảnh gốc khi người dùng kiểm tra.

#### 8. Business Rules
- Bắt buộc phải bóc tách đầy đủ Mã số thuế bên bán và Số hóa đơn đối với các loại hóa đơn điện tử để làm căn cứ tra cứu tính pháp lý trên cổng Tổng cục Thuế.
- Tổng thành tiền của từng dòng hàng hóa sau khi cộng lại phải khớp với tổng tiền thanh toán trên hóa đơn (cho phép sai số làm tròn số học tối đa 1.000 VNĐ).

#### 9. Điểm chưa thống nhất
- Quy định bóc tách tên thuốc/viện phí: Có cần ánh xạ tên thuốc bóc tách được với Danh mục thuốc bảo hiểm y tế của Bộ Y tế hay chỉ lưu tên thuần văn bản?

---

### ĐẶC TẢ 3: THẨM ĐỊNH NGƯỠNG TIN CẬY 3 TẦNG VÀ BẢO VỆ TRƯỜNG CỐT LÕI

#### 1. Tên chức năng
Thẩm định ngưỡng tin cậy 3 tầng và bảo vệ trường cốt lõi (3-Tier Confidence Auditing & Crucial Fields Protection).

#### 2. Mục đích
Thiết lập cơ chế kiểm soát chất lượng dữ liệu đa tầng nghiêm ngặt, đảm bảo các trường dữ liệu ảnh hưởng trực tiếp đến nghĩa vụ thuế không bị nhận diện sai lệch.

#### 3. Actor
- Động cơ đối soát dữ liệu (Validation Engine)
- Hệ thống (System)

#### 4. Điều kiện trước
- Dữ liệu hóa đơn đã được bóc tách và có điểm tin cậy cho từng trường.
- Hệ thống đã nạp bộ tham số cấu hình ngưỡng và danh mục trường cốt lõi tương ứng từ CSDL.

#### 5. Luồng chính
Hệ thống tiến hành thẩm định qua 3 tầng độc lập:
1. **Tầng 1 - Thẩm định loại tài liệu (Document Type Gate):**
   - Kiểm tra mã loại tài liệu có nằm trong danh mục hỗ trợ hay không. Nếu là `UNSUPPORTED`, lập tức dừng quy trình và từ chối xử lý.
2. **Tầng 2 - Thẩm định ngưỡng tin cậy tổng thể (Overall Confidence Gate):**
   - Tính toán điểm tin cậy trung bình của toàn bộ các trường trên hóa đơn.
   - So sánh với ngưỡng điểm tổng quan được cấu hình riêng cho danh mục đó (ví dụ: ngưỡng hóa đơn y tế là 0.82, biên lai đóng góp từ thiện là 0.85).
3. **Tầng 3 - Thẩm định độc lập các trường cốt lõi (Crucial Fields Gate):**
   - Truy xuất danh sách các trường bắt buộc sống còn của loại hóa đơn đang xét (ví dụ: Số hóa đơn, Tổng tiền thanh toán, Ngày lập hóa đơn, Mã số thuế bên bán).
   - Kiểm tra từng trường cốt lõi: Điểm tin cậy của trường đó phải lớn hơn hoặc bằng ngưỡng sàn riêng biệt (ví dụ: Tổng tiền >= 0.90, Số hóa đơn >= 0.88).
4. Nếu cả 3 tầng thẩm định đều vượt qua:
   - Gán trạng thái hồ sơ chi phí là **"Thẩm định đạt chuẩn" (Passed / Auto-Approved)**.
   - Cho phép người dùng chuyển tiếp sang bước hoàn tất kê khai.

#### 6. Luồng thay thế / Ngoại lệ
- **Vi phạm Tầng 2 (Điểm tổng thể thấp do ảnh mờ đều):** Hệ thống đánh cờ cảnh báo **"Cần rà soát tổng thể"** và hiển thị khuyến nghị chụp lại ảnh.
- **Vi phạm Tầng 3 (Tổng thể tốt nhưng có một trường cốt lõi bị nghi ngờ):** Ví dụ ảnh rất nét nhưng con số tổng tiền bị vết mực che khuất -> Hệ thống gắn cờ cảnh báo đích danh: "Trường Tổng tiền không đạt ngưỡng an toàn", đồng thời bôi đỏ vị trí trường này trên giao diện người dùng.

#### 7. Kết quả sau khi thực hiện
- Phân loại rõ ràng hóa đơn nào đủ điều kiện tự động chấp thuận, hóa đơn nào bắt buộc phải có sự xác nhận của con người trước khi dùng tính thuế.

#### 8. Business Rules
- Bất kỳ hồ sơ nào vi phạm quy tắc tại Tầng 3 (Trường cốt lõi bị điểm thấp hoặc bị trống) tuyệt đối không được phép tự động phê duyệt tính giảm trừ thuế.
- Danh mục các trường cốt lõi phải được cấu hình tách biệt cho từng loại chi phí (ví dụ: Hóa đơn y tế bắt buộc có tên bệnh nhân, nhưng biên lai đóng góp từ thiện bắt buộc có tên tổ chức nhận quyên góp).

#### 9. Điểm chưa thống nhất
- Quy định ngưỡng điểm tối thiểu để cho phép người dùng tự sửa trên giao diện (ví dụ nếu điểm quá thấp < 0.40 thì bắt buộc chụp lại hoàn toàn chứ không cho sửa tay).

---

### ĐẶC TẢ 4: ĐỐI SOÁT NIÊN ĐỘ TÍNH THUẾ VÀ TÍNH NHẤT QUÁN TÀI CHÍNH

#### 1. Tên chức năng
Đối soát niên độ tính thuế và tính nhất quán tài chính (Tax Year Matching & Financial Consistency Auditing).

#### 2. Mục đích
Ngăn chặn gian lận hoặc nhầm lẫn khi người nộp thuế sử dụng hóa đơn của các năm trước hoặc hóa đơn bị tẩy xóa số tiền để đưa vào kỳ quyết toán thuế hiện tại.

#### 3. Actor
- Hệ thống (System)
- Người nộp thuế (User)

#### 4. Điều kiện trước
- Hóa đơn đã bóc tách thành công thông tin ngày lập và các số liệu tài chính.
- User đang thao tác trong một kỳ quyết toán thuế xác định (ví dụ: Kỳ tính thuế năm 2026).

#### 5. Luồng chính
1. Hệ thống trích xuất năm phát hành hóa đơn (`extractedYear`) từ trường ngày lập hóa đơn.
2. Hệ thống so sánh `extractedYear` với năm tính thuế mục tiêu mà User đang kê khai (`targetYear`):
   - *Trường hợp trùng khớp:* Ghi nhận cờ `isTaxYearMatched = True`.
3. Hệ thống thực hiện kiểm toán tính cân đối số học trên hóa đơn:
   - Tính tổng tiền của toàn bộ các dòng hàng hóa chi tiết: `Tổng_tính_toán = Σ (Số lượng × Đơn giá)`.
   - Đối chiếu `Tổng_tính_toán` với trường `Tổng tiền chưa thuế` và `Tổng tiền thanh toán` trên hóa đơn.
   - Kiểm tra tính hợp lý của tỷ lệ thuế GTGT (nếu có).
4. Nếu niên độ khớp và số liệu cân đối:
   - Hệ thống đánh dấu chứng từ đạt tính toàn vẹn tài chính.

#### 6. Luồng thay thế / Ngoại lệ
- **Sai lệch năm quyết toán (Mismatch Tax Year):** Ví dụ User kê khai thuế năm 2026 nhưng tải lên hóa đơn xuất ngày 15/12/2024 -> Hệ thống không chặn đứng hoàn toàn mà chuyển trạng thái sang **"Cảnh báo sai lệch niên độ"**, hiển thị thông báo rõ ràng cho User: "Hóa đơn được phát hành trong năm 2024, không thuộc kỳ tính thuế 2026".
- **Không nhất quán về số học (Số tiền không khớp):** Tổng thành tiền của các dòng hàng hóa lệch đáng kể so với tổng tiền ghi ở chân hóa đơn -> Hệ thống cảnh báo nguy cơ hóa đơn bị cắt dán, tẩy xóa hoặc bóc tách thiếu dòng để User rà soát lại.

#### 7. Kết quả sau khi thực hiện
- Phát hiện sớm các lỗi sai niên độ hóa đơn vốn là nguyên nhân phổ biến khiến hồ sơ quyết toán thuế bị cơ quan thuế loại trừ và xử phạt chậm nộp.
- Đảm bảo số liệu chi phí đưa vào công thức tính thuế hoàn toàn chính xác.

#### 8. Business Rules
- Chi phí chỉ được coi là hợp lệ để giảm trừ thuế TNCN khi hóa đơn được phát hành trong đúng niên độ tính thuế theo quy định của Luật Thuế (từ ngày 01/01 đến hết ngày 31/12 của năm tính thuế đó).
- Trường hợp hóa đơn có sai lệch niên độ, hệ thống vẫn lưu lại dữ liệu nháp nhưng bắt buộc User phải xác nhận lại mục đích kê khai trước khi gửi hồ sơ chính thức.

#### 9. Điểm chưa thống nhất
- Cơ chế xử lý hóa đơn xuất vào đầu năm sau nhưng chi trả cho dịch vụ của năm trước (ví dụ viện phí thanh toán đợt Tết dương lịch): Có cho phép áp dụng ngoại lệ tính theo thời điểm thanh toán thực tế không?

---

### ĐẶC TẢ 5: HIỆU CHỈNH ĐỐI CHIẾU TRỰC QUAN VÀ XÁC NHẬN GHI NHẬN CHI PHÍ

#### 1. Tên chức năng
Hiệu chỉnh đối chiếu trực quan và xác nhận ghi nhận chi phí (Visual Comparison, Human Adjustment & Expense Confirmation).

#### 2. Mục đích
Cung cấp màn hình làm việc trực quan cho phép người nộp thuế dễ dàng so sánh kết quả AI bóc tách với ảnh gốc hóa đơn, tự tay chỉnh sửa các trường bị cảnh báo và chính thức xác nhận đưa vào sổ chi phí.

#### 3. Actor
- Người nộp thuế (User)
- Hệ thống (System)

#### 4. Điều kiện trước
- Hóa đơn đã hoàn thành các bước bóc tách và đối soát tự động.

#### 5. Luồng chính
1. Hệ thống hiển thị giao diện đối chiếu song song:
   - Bên trái (hoặc phía trên): Bản xem trước ảnh gốc hóa đơn.
   - Bên phải (hoặc phía dưới): Biểu mẫu các trường dữ liệu bóc tách được phân nhóm khoa học (Bên bán, Bên mua, Chi tiết chi phí, Tổng tiền).
2. Khi User nhấn chuột hoặc chạm vào bất kỳ ô nhập liệu nào trên biểu mẫu, Hệ thống tự động di chuyển khung nhìn và làm sáng (Highlight Bounding Box) vị trí của thông tin đó trên ảnh gốc.
3. Các trường bị cảnh báo do điểm tin cậy thấp hoặc có nghi ngờ sai lệch được đánh dấu bằng màu viền cam/đỏ để thu hút sự chú ý của User.
4. User kiểm tra số liệu, thực hiện chỉnh sửa lại các ký tự bị sai (nếu có).
5. User kiểm tra tổng tiền và nhấn "Xác nhận và Lưu chi phí".
6. Hệ thống ghi nhận dữ liệu chính thức, lưu trữ lịch sử chỉnh sửa (Audit Trail: giá trị ban đầu do AI trích xuất vs giá trị người dùng hiệu chỉnh) và cập nhật số tiền vào bảng tính thuế tạm tính của User.

#### 6. Luồng thay thế / Ngoại lệ
- **User phát hiện ảnh chụp bị nhầm người hoặc hóa đơn không còn giá trị:** User nhấn nút "Hủy bỏ và Xóa hóa đơn" -> Hệ thống xóa bỏ phiên làm việc và không ghi nhận chi phí.
- **User sửa đổi số tiền vượt quá ngưỡng hợp lý:** User sửa số tiền lên gấp nhiều lần so với số tiền AI đọc được -> Hệ thống hiển thị cảnh báo xác nhận hai lần để chống thao tác nhầm lẫn.

#### 7. Kết quả sau khi thực hiện
- Khoản chi phí được chuyển từ trạng thái "Bản nháp bóc tách" sang **"Đã xác nhận chính thức" (Confirmed Expense)**.
- Toàn bộ vết kiểm toán phục vụ việc giải trình với cơ quan thuế sau này được lưu trữ an toàn.

#### 8. Business Rules
- Bắt buộc phải lưu vết kiểm toán (Audit Trail) gồm: Ảnh gốc, kết quả thô của AI, thông tin người sửa, thời điểm sửa và giá trị cuối cùng.
- Khi người dùng chủ động sửa dữ liệu, hệ thống tự động cập nhật lại các chỉ số cân đối tài chính liên quan.

#### 9. Điểm chưa thống nhất
- Người dùng có thể xóa một dòng hàng hóa cụ thể trong hóa đơn nếu dòng đó là hàng hóa không thuộc diện được giảm trừ (ví dụ mua thuốc kèm mỹ phẩm) hay không?

---

### ĐẶC TẢ 6: QUẢN TRỊ CẤU HÌNH HỆ THỐNG & CHÍNH SÁCH CHI PHÍ ĐỘNG

#### 1. Tên chức năng
Quản trị cấu hình hệ thống & chính sách chi phí động (Dynamic System Configuration & Expense Policy Management).

#### 2. Mục đích
Cho phép Quản trị viên (Admin) quản lý tập trung toàn bộ các tham số vận hành, ngưỡng an toàn cho từng danh mục chi phí, danh sách trường cốt lõi và các quy tắc kiểm soát theo thời gian thực mà không cần lập trình viên sửa code.

#### 3. Actor
- Quản trị viên hệ thống (Admin)
- Hệ thống (System)

#### 4. Điều kiện trước
- Admin đăng nhập bằng tài khoản có quyền Quản trị hệ thống (System Administrator).

#### 5. Luồng chính
1. Admin truy cập màn hình "Quản trị Cấu hình Hệ thống" (`System Configs Management`).
2. Hệ thống hiển thị danh sách các cấu hình đang hoạt động được phân nhóm:
   - Nhóm tham số AI (Ngưỡng tin cậy chung, Ngưỡng riêng cho từng loại hóa đơn).
   - Nhóm danh mục chi phí (Mã danh mục, Tên hiển thị, Quy tắc nhận diện).
   - Nhóm trường cốt lõi (Crucial Fields theo từng danh mục).
   - Nhóm tham số vận hành (Dung lượng file tối đa, thời gian giữ file tạm).
3. Admin thực hiện tạo mới, chỉnh sửa giá trị tham số:
   - Hệ thống tự động suy đoán và kiểm tra định dạng kiểu dữ liệu (Số thực, Chuỗi văn bản, JSON, Danh sách phân tách bằng dấu phẩy).
4. Admin nhấn "Cập nhật cấu hình".
5. Hệ thống lưu cấu hình mới, cập nhật bộ nhớ đệm và kích hoạt áp dụng ngay lập tức cho các giao dịch tải hóa đơn diễn ra sau đó.
6. Cho phép Admin tạm ẩn (Soft Delete) hoặc kích hoạt lại các cấu hình khi cần thiết.

#### 6. Luồng thay thế / Ngoại lệ
- **Sai kiểu dữ liệu:** Admin nhập chữ vào trường yêu cầu số thực (ví dụ nhập chữ "cao" vào ô ngưỡng tin cậy) -> Hệ thống báo lỗi và chặn lưu dữ liệu.
- **Xóa cấu hình mặc định quan trọng:** Admin cố tình xóa cấu hình cơ sở của hệ thống -> Hệ thống từ chối và cảnh báo đây là tham số bắt buộc để duy trì hoạt động.

#### 7. Kết quả sau khi thực hiện
- Hệ thống hoạt động linh hoạt, dễ dàng thích ứng với các thay đổi chính sách kiểm soát chi phí mà không phát sinh chi phí triển khai phần mềm mới.

#### 8. Business Rules
- Cơ chế xóa cấu hình phải áp dụng nguyên tắc Xóa mềm (Soft Delete) để bảo toàn tính toàn vẹn của dữ liệu và nhật ký đối soát trong quá khứ.
- Mọi thay đổi về cấu hình phải được ghi nhận vào nhật ký kiểm trị gồm: Admin thực hiện, giá trị cũ, giá trị mới, thời điểm thay đổi.

#### 9. Điểm chưa thống nhất
- Quy định giới hạn số lần thay đổi cấu hình trong ngày và cơ chế tự động gửi email thông báo cho toàn bộ đội ngũ Quản trị khi có một cấu hình ngưỡng quan trọng bị sửa đổi.

---

## 3. BẢNG TỔNG HỢP VÀ ÁNH XẠ TRẠNG THÁI NGHIỆP VỤ

| STT | Tên đặc tả nghiệp vụ | Trọng tâm giải quyết | Trạng thái chứng từ chi phí |
| :--- | :--- | :--- | :--- |
| **1** | Tiếp nhận và phân loại chứng từ | Tải tệp & phân loại danh mục chi phí hợp lệ | Tải lên -> Hợp lệ / Bị từ chối (Unsupported) |
| **2** | Bóc tách thông tin & bảng chi tiết | Trích xuất thông tin bên bán, bên mua & Line items | Đang bóc tách -> Bóc tách thành công |
| **3** | Thẩm định ngưỡng tin cậy 3 tầng | Kiểm tra ngưỡng chung & bảo vệ trường cốt lõi | Đạt chuẩn (Passed) / Cần rà soát (Flagged) |
| **4** | Đối soát niên độ & cân đối tài chính | Khớp năm quyết toán & kiểm tra số học | Niên độ hợp lệ / Cảnh báo sai lệch niên độ |
| **5** | Hiệu chỉnh đối chiếu & xác nhận | Soi sáng ảnh gốc, sửa sai sót & lưu vết | Bản nháp -> Đã xác nhận chính thức |
| **6** | Quản trị cấu hình hệ thống động | Điều chỉnh ngưỡng & danh mục thời gian thực | Cấu hình lưu phiên bản mới, áp dụng tức thời |
