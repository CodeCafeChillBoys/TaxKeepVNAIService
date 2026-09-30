# TÀI LIỆU ĐẶC TẢ NGHIỆP VỤ PHÂN HỆ
## MODULE: TIẾP NHẬN VĂN BẢN QUY PHẠM THUẾ & TỰ ĐỘNG HÓA TRÍCH XUẤT QUY TẮC (TAX RULE DOCUMENT INGESTION & KNOWLEDGE EXTRACTION)
**Nhánh phát triển:** `feature/implemation_UploadTaxRuleDocumentByAIExtraction`  
**Dự án:** TaxKeep VN - Dịch vụ Trí tuệ Nhân tạo Hỗ trợ Thuế TNCN (TaxAIService)  
**Ngày hoàn thiện đặc tả:** 28/09/2026  
**Trạng thái:** Đặc tả nghiệp vụ mức Conceptual / Sẵn sàng Review & Thống nhất  

---

## 1. TỔNG QUAN PHÂN HỆ

Hệ thống chính sách và văn bản pháp luật về Thuế Thu nhập Cá nhân (TNCN) tại Việt Nam thường xuyên được sửa đổi, bổ sung và điều chỉnh theo tiến trình phát triển kinh tế (các Nghị quyết của Ủy ban Thường vụ Quốc hội về mức giảm trừ gia cảnh, biểu thuế lũy tiến từng phần, quy định về đóng góp bảo hiểm, quỹ hưu trí và các khoản phụ cấp miễn thuế).

Phân hệ **Tiếp nhận văn bản quy phạm thuế & Tự động hóa trích xuất quy tắc** giải quyết triệt để nút thắt cổ chai của các phần mềm truyền thống: thay vì lập trình viên phải sửa code và Quản trị viên phải gõ tay hàng trăm con số phức tạp từ các tập tài liệu pháp lý dài hàng chục trang, phân hệ cho phép tải trực tiếp văn bản pháp quy (file PDF), tự động xác thực nguồn gốc văn bản, sử dụng AI để bóc tách toàn bộ công thức, biểu thuế, hạn mức giảm trừ, và chuyển thành bộ quy tắc có thể kiểm duyệt và kích hoạt vận hành tự động cho toàn bộ hệ thống tính thuế.

---

## 2. DANH SÁCH CÁC ĐẶC TẢ NGHIỆP VỤ CỐT LÕI

1. [Đặc tả 1: Tải lên và thẩm định nguồn gốc văn bản quy phạm thuế](#đặc-tả-1-tải-lên-và-thẩm-định-nguồn-gốc-văn-bản-quy-phạm-thuế)
2. [Đặc tả 2: Tự động bóc tách quy tắc tính thuế và biểu thuế lũy tiến](#đặc-tả-2-tự-động-bóc-tách-quy-tắc-tính-thuế-và-biểu-thuế-lũy-tiến)
3. [Đặc tả 3: Đối soát niên độ áp dụng và hiệu lực thi hành văn bản](#đặc-tả-3-đối-soát-niên-độ-áp-dụng-và-hiệu-lực-thi-hành-văn-bản)
4. [Đặc tả 4: Rà soát, hiệu chỉnh và kích hoạt bộ quy tắc thuế](#đặc-tả-4-rà-soát-hiệu-chỉnh-và-kích-hoạt-bộ-quy-tắc-thuế)
5. [Đặc tả 5: Quản trị danh mục nguồn tin cậy và lịch sử phiên bản quy tắc thuế](#đặc-tả-5-quản-trị-danh-mục-nguồn-tin-cậy-và-lịch-sử-phiên-bản-quy-tắc-thuế)

---

### ĐẶC TẢ 1: TẢI LÊN VÀ THẨM ĐỊNH NGUỒN GỐC VĂN BẢN QUY PHẠM THUẾ

#### 1. Tên chức năng
Tải lên và thẩm định nguồn gốc văn bản quy phạm thuế (Tax Document Ingestion & Legal Source Verification).

#### 2. Mục đích
Cho phép Quản trị viên tải lên văn bản luật, nghị định, thông tư về thuế TNCN và tự động kiểm chứng tính chính danh của nguồn tài liệu thông qua danh sách các cổng thông tin điện tử được nhà nước công nhận (Whitelist).

#### 3. Actor
- Quản trị viên hệ thống (Admin)
- Hệ thống thẩm định nguồn (System)

#### 4. Điều kiện trước
- Admin đã đăng nhập với vai trò Quản trị viên chính sách thuế.
- Hệ thống đã thiết lập danh sách các tên miền nguồn chính thống được phép tải tài liệu (ví dụ: `chinhphu.vn`, `mof.gov.vn`, `gdt.gov.vn`, `thuvienphapluat.vn`).

#### 5. Luồng chính
1. Admin truy cập màn hình "Cập nhật Quy tắc Thuế mới".
2. Admin nhập các thông tin ban đầu:
   - Tên gọi văn bản (ví dụ: "Nghị quyết 954/2020/UBTVQH14 về điều chỉnh mức giảm trừ gia cảnh").
   - Cơ quan ban hành (Quốc hội, Chính phủ, Bộ Tài chính).
   - Đường dẫn liên kết nguồn gốc của văn bản (`sourceUrl`).
   - Niên độ tính thuế dự kiến áp dụng (`inputTaxYear`).
3. Admin tải lên tệp văn bản ở định dạng PDF (chấp nhận cả PDF dạng văn bản số và PDF bản scan có dấu đỏ).
4. Hệ thống thực hiện thẩm định đường dẫn nguồn (`sourceUrl`):
   - Chuẩn hóa đường dẫn, bóc tách tên miền gốc.
   - So sánh với Danh mục nguồn tài liệu tin cậy (Source Whitelist).
5. Nếu nguồn hợp lệ và tệp PDF nguyên vẹn:
   - Hệ thống ghi nhận tài liệu, chuyển trạng thái sang **"Tiếp nhận hợp lệ - Đang trích xuất" (Accepted / Extracting)**.
   - Hệ thống đưa văn bản vào hàng đợi xử lý bóc tách thông minh.

#### 6. Luồng thay thế / Ngoại lệ
- **Nguồn văn bản không thuộc danh mục tin cậy:** Đường dẫn nguồn trỏ về các trang mạng xã hội, diễn đàn không chính thống, hoặc trang web lạ không nằm trong Whitelist -> Hệ thống lập tức từ chối tiếp nhận, cảnh báo nguy cơ văn bản giả mạo hoặc chưa được xác thực.
- **Tệp PDF bị hỏng hoặc vượt quá số trang cho phép:** Tệp bị lỗi không mở được hoặc dài quá 50 trang -> Hệ thống yêu cầu kiểm tra lại tệp hoặc trích tách riêng phần chương/điều khoản quy định về thuế TNCN trước khi nộp.

#### 7. Kết quả sau khi thực hiện
- Văn bản pháp luật được lưu trữ an toàn kèm nguồn gốc minh bạch, sẵn sàng cho công đoạn giải mã và bóc tách quy tắc.

#### 8. Business Rules
- Bắt buộc phải cung cấp đường dẫn nguồn xuất xứ của văn bản pháp lý để bảo đảm tính giải trình khi cơ quan kiểm toán yêu cầu đối soát.
- Mọi văn bản tải lên phải được kiểm tra virus và bảo mật trước khi đưa vào hàng đợi xử lý của trí tuệ nhân tạo.

#### 9. Điểm chưa thống nhất
- Có cho phép nộp văn bản nội bộ hoặc quy chế chi tiêu của riêng doanh nghiệp (không có URL nhà nước) cho phiên bản dành riêng cho khách hàng doanh nghiệp hay không?

---

### ĐẶC TẢ 2: TỰ ĐỘNG BÓC TÁCH QUY TẮC TÍNH THUẾ VÀ BIỂU THUẾ LŨY TIẾN

#### 1. Tên chức năng
Tự động bóc tách quy tắc tính thuế và biểu thuế lũy tiến (Automated Tax Rule & Progressive Tax Bracket Extraction).

#### 2. Mục đích
Sử dụng trí tuệ nhân tạo chuyên sâu về ngôn ngữ và thị giác để đọc hiểu toàn bộ nội dung văn bản pháp lý, bóc tách tự động các định mức giảm trừ, các bậc thuế và điều kiện miễn giảm thành cấu trúc dữ liệu rõ ràng.

#### 3. Actor
- Hệ thống AI bóc tách chính sách (System AI Engine)
- Hệ thống lõi (Core System)

#### 4. Điều kiện trước
- Tệp văn bản PDF đã vượt qua bước thẩm định nguồn gốc và tiền kiểm tra tệp.

#### 5. Luồng chính
1. Hệ thống tự động phân loại hình thái tệp:
   - *Nếu là văn bản số (Text PDF):* Trích xuất văn bản trực tiếp theo từng trang để tối ưu tốc độ xử lý.
   - *Nếu là bản scan (Scanned PDF có con dấu, chữ ký):* Kích hoạt chế độ thị giác đa phương thức (Multimodal Vision) để đọc hiểu từng trang ảnh.
2. Hệ thống tiến hành bóc tách các nhóm thông tin cốt lõi:
   - **Thông tin định danh văn bản:** Số hiệu văn bản, loại văn bản (Luật/Nghị định/Thông tư), ngày ký ban hành, người ký.
   - **Các mức giảm trừ gia cảnh chuẩn:**
     - Mức giảm trừ cho bản thân người nộp thuế (triệu đồng/tháng).
     - Mức giảm trừ cho mỗi người phụ thuộc (triệu đồng/tháng).
   - **Biểu thuế lũy tiến từng phần:**
     - Danh sách các bậc thuế (từ Bậc 1 đến Bậc 7).
     - Thu nhập tính thuế tối thiểu và tối đa của từng bậc (triệu đồng/tháng hoặc triệu đồng/năm).
     - Thuế suất tương ứng (%) của từng bậc.
   - **Các quy định miễn giảm & phụ cấp đặc thù:**
     - Mức khoán chi ăn trưa, điện thoại, trang phục được miễn thuế.
     - Mức đóng góp bảo hiểm bắt buộc và quỹ hưu trí tự nguyện được trừ tối đa.
     - Các điều khoản miễn trừ thuế đối với thu nhập từ kiều hối, bất động sản thân nhân...
3. Hệ thống tổng hợp toàn bộ các thông số bóc tách được thành một **Bản nháp bộ quy tắc thuế (Draft Rule Set)** kèm theo đoạn trích dẫn điều khoản tương ứng trong văn bản để làm căn cứ đối soát.
4. Chuyển kết quả sang bước đối soát niên độ và hiệu lực thi hành.

#### 6. Luồng thay thế / Ngoại lệ
- **Văn bản không chứa nội dung quy định về thuế TNCN:** Ví dụ Admin tải nhầm Luật Đất đai hoặc Thông tư thuế GTGT -> Hệ thống nhận diện nội dung không liên quan, thông báo: "Không tìm thấy điều khoản quy định về Thuế TNCN trong tài liệu này" và kết thúc xử lý.
- **Biểu thuế bóc tách bị thiếu bậc:** Số bậc thuế trích xuất được không đủ chuỗi liên tục (bị đứt đoạn từ bậc 3 nhảy sang bậc 5) -> Hệ thống đánh cờ cảnh báo lỗi cấu trúc nghiêm trọng để Quản trị viên lưu ý.

#### 7. Kết quả sau khi thực hiện
- Bộ quy tắc thuế được chuyển đổi từ ngôn ngữ pháp lý sang dữ liệu số hóa có cấu trúc hoàn chỉnh.
- Mọi con số đều gắn liền với trích dẫn điều khoản làm căn cứ pháp lý.

#### 8. Business Rules
- Bảng biểu thuế lũy tiến bóc tách phải đảm bảo tính liên tục của các khoảng thu nhập (mức trần của bậc trước phải là mức sàn của bậc kế tiếp).
- Các định mức tiền tệ phải được chuẩn hóa về đơn vị tiền tệ đồng nhất (VNĐ) để phục vụ tính toán tự động.

#### 9. Điểm chưa thống nhất
- Cơ chế xử lý đối với các điều khoản có tính chất định tính (ví dụ: "trong trường hợp đặc biệt do Thủ tướng Chính phủ quyết định"): Hệ thống sẽ bỏ qua hay lưu dạng ghi chú tham khảo?

---

### ĐẶC TẢ 3: ĐỐI SOÁT NIÊN ĐỘ ÁP DỤNG VÀ HIỆU LỰC THI HÀNH VĂN BẢN

#### 1. Tên chức năng
Đối soát niên độ áp dụng và hiệu lực thi hành văn bản (Tax Year Matching & Enforcement Effective Date Verification).

#### 2. Mục đích
Phân tích tính hiệu lực thời gian của văn bản pháp lý, đối chiếu năm áp dụng trong văn bản với năm mà Quản trị viên dự định áp dụng, đưa ra cảnh báo sớm nếu phát hiện sự bất tương đồng.

#### 3. Actor
- Hệ thống đối soát (System)
- Quản trị viên (Admin)

#### 4. Điều kiện trước
- Bộ quy tắc thuế đã được bóc tách xong các mốc ngày tháng và niên độ.
- Có thông tin năm tính thuế do Admin nhập (`inputTaxYear`).

#### 5. Luồng chính
1. Hệ thống phân tích văn bản để bóc tách 3 mốc thời gian pháp lý:
   - Ngày ký ban hành văn bản.
   - Ngày văn bản bắt đầu có hiệu lực thi hành (Effective Date).
   - Niên độ tính thuế bắt đầu áp dụng (`extractedTaxYear`).
2. Hệ thống thực hiện đối chiếu:
   - So sánh `extractedTaxYear` với `inputTaxYear` của Admin.
3. Nếu hai thông số trùng khớp:
   - Hệ thống đánh dấu trạng thái **"Niên độ hoàn toàn trùng khớp" (`isTaxYearMatched = True`)**.
4. Hệ thống kiểm tra xem văn bản mới này có tuyên bố thay thế hoặc bãi bỏ văn bản quy phạm nào trước đó hay không (dựa trên điều khoản thi hành).
5. Đóng gói bộ quy tắc và chuyển sang giao diện kiểm duyệt của Admin.

#### 6. Luồng thay thế / Ngoại lệ
- **Sai lệch niên độ (Không làm gián đoạn bóc tách - Non-blocking Warning):** Admin nhập năm 2026 nhưng văn bản quy định áp dụng từ kỳ tính thuế năm 2020 -> Hệ thống **vẫn bóc tách đầy đủ toàn bộ quy tắc**, không hủy bỏ tiến trình mà gắn nhãn cảnh báo vàng: `warning: "Năm tính thuế khai báo (2026) khác với năm ghi trên văn bản (2020)"`. Điều này giúp Admin không bị mất công tải lại và có thể chủ động sửa năm áp dụng tại bước sau.
- **Văn bản chưa có hiệu lực tại thời điểm tải lên:** Văn bản được ký ban hành nhưng ngày có hiệu lực ở tương lai xa -> Hệ thống gắn cờ "Quy tắc dự kiến có hiệu lực trong tương lai".

#### 7. Kết quả sau khi thực hiện
- Xác lập rõ ràng phạm vi thời gian áp dụng của bộ quy tắc thuế, ngăn chặn việc áp dụng nhầm văn bản cũ đã hết hiệu lực cho các năm quyết toán mới.

#### 8. Business Rules
- Hệ thống áp dụng nguyên tắc bóc tách không chặn (Non-blocking): Dù phát hiện sai lệch năm tính thuế, hệ thống vẫn phải hoàn thành trích xuất dữ liệu và giao quyền quyết định cuối cùng cho Quản trị viên.
- Tại một thời điểm trong một năm tính thuế, chỉ có duy nhất một bộ quy tắc thuế được phép ở trạng thái "Kích hoạt chính thức" (Active).

#### 9. Điểm chưa thống nhất
- Đối với các văn bản có hiệu lực hồi tố (ví dụ ban hành vào tháng 6 nhưng cho phép áp dụng hồi tố từ ngày 01/01 của năm): Hệ thống có cần tự động tính toán lại các hồ sơ tạm tính thuế của các tháng trước hay không?

---

### ĐẶC TẢ 4: RÀ SOÁT, HIỆU CHỈNH VÀ KÍCH HOẠT BỘ QUY TẮC THUẾ

#### 1. Tên chức năng
Rà soát, hiệu chỉnh và kích hoạt bộ quy tắc thuế (Review, Manual Adjustment & Rule Set Activation).

#### 2. Mục đích
Cung cấp bàn làm việc cho Quản trị viên rà soát toàn bộ các tham số AI đã bóc tách, đối chiếu với văn bản gốc, trực tiếp sửa đổi các sai sót (nếu có) và chính thức phê duyệt áp dụng bộ quy tắc cho toàn hệ thống.

#### 3. Actor
- Quản trị viên chính sách thuế (Admin)
- Hệ thống (System)

#### 4. Điều kiện trước
- Bộ quy tắc thuế đã bóc tách xong và đang ở trạng thái **"Bản nháp chờ duyệt" (Draft Rule Set)**.

#### 5. Luồng chính
1. Admin truy cập danh sách các bộ quy tắc đang chờ duyệt và mở chi tiết bộ quy tắc vừa tải lên.
2. Hệ thống hiển thị giao diện đối soát chuyên nghiệp:
   - Một bên là văn bản PDF pháp lý gốc.
   - Một bên là danh mục các tham số đã trích xuất (Mức giảm trừ gia cảnh, Bảng 7 bậc thuế, Các khoản phụ cấp miễn thuế).
3. Các tham số có cảnh báo (sai lệch năm, điểm tin cậy thấp) được bôi sáng để Admin tập trung kiểm tra.
4. Admin đối chiếu từng tham số; nếu phát hiện sai sót do câu chữ văn bản phức tạp, Admin có quyền chỉnh sửa trực tiếp các con số trên form.
5. Sau khi kiểm tra hoàn tất, Admin chọn phạm vi áp dụng (ví dụ: Áp dụng từ kỳ tính thuế 2026 trở đi) và nhấn nút **"Phê duyệt và Kích hoạt bộ quy tắc" (Approve & Activate)**.
6. Hệ thống thực hiện kiểm toán lần cuối (tính liên tục của các bậc thuế, các số liệu không âm), lưu trữ phiên bản chính thức, chuyển trạng thái thành **"Đang kích hoạt" (Active)** và đồng bộ ngay lập tức sang động cơ tính thuế của ứng dụng.
7. Gửi thông báo xác nhận cập nhật chính sách thuế thành công cho toàn bộ ban quản trị.

#### 6. Luồng thay thế / Ngoại lệ
- **Admin phát hiện văn bản tải lên bị trùng hoặc sai hoàn toàn:** Admin nhấn nút "Từ chối và Hủy bản nháp" -> Hệ thống đánh dấu hủy và lưu trữ hồ sơ phục vụ kiểm toán nội bộ.
- **Vi phạm tính toàn vẹn khi Admin sửa tay:** Admin sửa bậc thuế khiến bậc 2 có mức sàn cao hơn mức trần của bậc 1 -> Hệ thống báo lỗi logic toán học và yêu cầu điều chỉnh lại trước khi cho phép kích hoạt.

#### 7. Kết quả sau khi thực hiện
- Bộ quy tắc thuế mới trở thành nguồn tri thức chuẩn mực (Single Source of Truth) để hệ thống thực hiện toàn bộ các nghiệp vụ tính toán thuế TNCN, quyết toán và tư vấn thuế tự động.

#### 8. Business Rules
- Bắt buộc phải có sự xác nhận và phê duyệt của con người (Human-in-the-loop) thì bộ quy tắc thuế mới được phép kích hoạt vào hệ thống tính toán thực tế; AI không được phép tự động kích hoạt luật mới.
- Mọi thao tác chỉnh sửa tay của Admin phải được ghi nhận rõ: Ai sửa, giá trị AI bóc tách ban đầu là gì, giá trị mới là gì, lý do sửa đổi.

#### 9. Điểm chưa thống nhất
- Cơ chế kiểm thử hồi quy tự động (Regression Testing): Có nên tự động chạy thử bộ quy tắc mới trên 100 kịch bản tính thuế mẫu trước khi cho phép kích hoạt chính thức hay không?

---

### ĐẶC TẢ 5: QUẢN TRỊ DANH MỤC NGUỒN TIN CẬY VÀ LỊCH SỬ PHIÊN BẢN QUY TẮC THUẾ

#### 1. Tên chức năng
Quản trị danh mục nguồn tin cậy và lịch sử phiên bản quy tắc thuế (Source Whitelist & Tax Rule Versioning Management).

#### 2. Mục đích
Cho phép quản lý danh sách các cổng thông tin chính phủ được phép khai thác tài liệu, đồng thời lưu trữ lịch sử toàn diện các phiên bản luật thuế qua từng thời kỳ để phục vụ việc quyết toán thuế cho các năm cũ.

#### 3. Actor
- Quản trị viên hệ thống (Admin)
- Hệ thống (System)

#### 4. Điều kiện trước
- Admin có thẩm quyền quản trị cấu hình hệ thống.

#### 5. Luồng chính
1. Admin truy cập mục "Quản trị Nguồn văn bản & Lịch sử Chính sách thuế".
2. **Quản trị danh mục nguồn tin cậy (Source Whitelist Management):**
   - Admin xem danh sách các tên miền cơ quan nhà nước đang được phép tải tài liệu.
   - Admin có thể thêm mới tên miền (ví dụ: bổ sung cổng thông tin của Cục Thuế TP. Hà Nội, Cục Thuế TP. Hồ Chí Minh), chỉnh sửa hoặc tạm dừng một nguồn nếu nguồn đó không còn an toàn.
3. **Quản lý lịch sử phiên bản quy tắc thuế (Rule Versioning):**
   - Hệ thống hiển thị dòng thời gian các bộ quy tắc qua từng năm (Phiên bản áp dụng cho năm 2024, năm 2025, năm 2026...).
   - Admin có thể tra cứu lại nội dung chi tiết của các bộ quy tắc cũ, xem văn bản pháp lý gốc đính kèm.
4. Khi người dùng thực hiện quyết toán thuế cho một năm trong quá khứ, Hệ thống tự động truy xuất đúng phiên bản quy tắc thuế có hiệu lực trong năm đó để áp dụng tính toán chính xác.

#### 6. Luồng thay thế / Ngoại lệ
- **Trùng lặp tên miền trong Whitelist:** Admin thêm một tên miền đã tồn tại -> Hệ thống thông báo tên miền đã có trong danh mục.
- **Khôi phục phiên bản quy tắc cũ:** Trong trường hợp văn bản mới bị cơ quan nhà nước hoãn thi hành đột xuất, Admin có quyền kích hoạt lại phiên bản quy tắc của năm liền kề trước đó.

#### 7. Kết quả sau khi thực hiện
- Đảm bảo tính pháp lý bền vững của hệ thống: Luôn có khả năng giải trình và tính toán thuế chính xác cho cả hiện tại lẫn các kỳ thanh tra quyết toán thuế quá khứ (lên tới 5 - 10 năm trước).

#### 8. Business Rules
- Lịch sử các phiên bản quy tắc thuế tuyệt đối không được xóa bỏ khỏi cơ sở dữ liệu để phục vụ công tác thanh tra thuế và kiểm toán độc lập.
- Việc bổ sung tên miền mới vào danh mục nguồn tin cậy phải được kiểm tra giao thức bảo mật (chỉ chấp nhận HTTPS).

#### 9. Điểm chưa thống nhất
- Cơ chế thông báo tự động (Notification Broadcast) cho toàn bộ người nộp thuế trong hệ thống khi có một chính sách thuế mới được kích hoạt áp dụng.

---

## 3. BẢNG TỔNG HỢP VÀ ÁNH XẠ TRẠNG THÁI NGHIỆP VỤ

| STT | Tên đặc tả nghiệp vụ | Trọng tâm giải quyết | Trạng thái văn bản / Bộ quy tắc |
| :--- | :--- | :--- | :--- |
| **1** | Tải lên & thẩm định nguồn gốc | Thẩm định URL nguồn & kiểm tra tính nguyên vẹn | Tải lên -> Hợp lệ (Accepted) / Từ chối |
| **2** | Tự động bóc tách quy tắc & biểu thuế | Trích xuất mức giảm trừ & Bảng 7 bậc thuế | Đang bóc tách -> Bản nháp (Draft Rule Set) |
| **3** | Đối soát niên độ & hiệu lực | Khớp năm tính thuế & cảnh báo không chặn | Niên độ khớp / Cảnh báo sai lệch năm |
| **4** | Rà soát, hiệu chỉnh & kích hoạt | Chuyên viên thẩm định, sửa tay & phê duyệt | Bản nháp -> Kích hoạt chính thức (Active) |
| **5** | Quản trị nguồn & lịch sử phiên bản | Quản lý Whitelist tên miền & phiên bản luật | Quản trị liên tục, lưu vết không thời hạn |