# TÀI LIỆU ĐẶC TẢ NGHIỆP VỤ PHÂN HỆ
## MODULE: OCR GIẤY TỜ NGƯỜI PHỤ THUỘC & ĐỐI SOÁT NGƯỠNG ĐỘNG (DEPENDENT DOCUMENT OCR & DYNAMIC THRESHOLD VALIDATION)
**Nhánh phát triển:** `feature/implementation_DependentDocumentOcr`  
**Dự án:** TaxKeep VN - Dịch vụ Trí tuệ Nhân tạo Hỗ trợ Thuế TNCN (TaxAIService)  
**Ngày hoàn thiện đặc tả:** 28/09/2026  
**Trạng thái:** Đặc tả nghiệp vụ mức Conceptual (Chuyên sâu OCR) / Sẵn sàng Review  

---

## 1. TỔNG QUAN PHÂN HỆ

Phân hệ **OCR Giấy tờ Người phụ thuộc & Đối soát ngưỡng động** là thành phần xử lý trí tuệ nhân tạo thị giác (Computer Vision / Multimodal OCR) chuyên trách của dịch vụ `TaxAIService`. Phân hệ có nhiệm vụ tiếp nhận hình ảnh/tệp scan các loại giấy tờ pháp lý chứng minh người phụ thuộc, tự động nhận diện phân loại mẫu văn bản, trích xuất quang học toàn bộ các trường thông tin nhân thân, và chấm điểm độ tin cậy độc lập cho từng trường dữ liệu.

Điểm cốt lõi của phân hệ là cơ chế **Đối soát ngưỡng tin cậy động (Dynamic Threshold Evaluation)**: thay vì cố định một con số tin cậy cứng trong mã nguồn, hệ thống cho phép đối chiếu điểm số của từng trường với các ngưỡng an toàn do Quản trị viên thiết lập động. Điều này giúp phát hiện chính xác các trường hợp tài liệu bị mờ, lóa sáng, che khuất hoặc chụp sai lệch, đảm bảo dữ liệu đưa vào hệ thống luôn đạt độ chính xác cao nhất.

---

## 2. DANH SÁCH CÁC ĐẶC TẢ NGHIỆP VỤ CỐT LÕI (CHUYÊN PHẦN OCR)

1. [Đặc tả 1: Tiếp nhận và tiền xử lý hình ảnh chứng từ OCR](#đặc-tả-1-tiếp-nhận-và-tiền-xử-lý-hình-ảnh-chứng-từ-ocr)
2. [Đặc tả 2: Tự động nhận diện và phân loại mẫu giấy tờ](#đặc-tả-2-tự-động-nhận-diện-và-phân-loại-mẫu-giấy-tờ)
3. [Đặc tả 3: Bóc tách quang học các trường dữ liệu định danh & chấm điểm tin cậy](#đặc-tả-3-bóc-tách-quang-học-các-trường-dữ-liệu-định-danh--chấm-điểm-tin-cậy)
4. [Đặc tả 4: Thẩm định ngưỡng tin cậy OCR động & cảnh báo lỗi hình ảnh](#đặc-tả-4-thẩm-định-ngưỡng-tin-cậy-ocr-động--cảnh-báo-lỗi-hình-ảnh)
5. [Đặc tả 5: Quản trị quy tắc bóc tách và cấu hình ngưỡng tin cậy OCR](#đặc-tả-5-quản-trị-quy-tắc-bóc-tách-và-cấu-hình-ngưỡng-tin-cậy-ocr)

---

### ĐẶC TẢ 1: TIẾP NHẬN VÀ TIỀN XỬ LÝ HÌNH ẢNH CHỨNG TỪ OCR

#### 1. Tên chức năng
Tiếp nhận và tiền xử lý hình ảnh chứng từ OCR (Image Ingestion & Preprocessing for OCR).

#### 2. Mục đích
Tiếp nhận các tệp hình ảnh hoặc tệp scan giấy tờ người phụ thuộc (hỗ trợ cả ảnh đơn hoặc cặp ảnh 2 mặt), kiểm tra tính toàn vẹn kỹ thuật của tệp hình ảnh và chuẩn hóa góc quay, độ phân giải trước khi đưa vào mô hình nhận dạng quang học.

#### 3. Actor
- Hệ thống gọi dịch vụ (Client / Core Backend)
- Dịch vụ tiền xử lý hình ảnh OCR (System Preprocessor)

#### 4. Điều kiện trước
- Tệp hình ảnh hoặc tệp PDF được gửi đến dịch vụ OCR qua giao diện xử lý (tải trực tiếp hoặc qua cơ chế hàng đợi bất đồng bộ).

#### 5. Luồng chính
1. Hệ thống tiếp nhận yêu cầu xử lý OCR kèm tệp chứng từ:
   - *Trường hợp ảnh đơn:* 1 tệp ảnh hoặc PDF (Giấy khai sinh, Giấy xác nhận thông tin cư trú CT07, Thẻ sinh viên, Giấy xác nhận khuyết tật...).
   - *Trường hợp ảnh cặp:* 2 tệp ảnh tương ứng Mặt trước và Mặt sau của thẻ Căn cước công dân (CCCD).
2. Hệ thống thực hiện kiểm tra kỹ thuật sơ bộ:
   - Kiểm tra định dạng tệp (JPEG, PNG, WebP, PDF).
   - Kiểm tra dung lượng tệp (trong ngưỡng quy định, ví dụ <= 10MB/ảnh).
   - Kiểm tra độ phân giải tối thiểu để đảm bảo ký tự có thể đọc được (tối thiểu 720p).
3. Hệ thống tiến hành chuẩn hóa hình ảnh:
   - Tự động phát hiện hướng đặt văn bản và xoay thẳng ảnh về góc 0° chuẩn (Orientation Correction).
   - Tự động cân bằng độ sáng, độ tương phản và khử nhiễu nhẹ nếu ảnh bị tối.
4. Đóng gói luồng hình ảnh đã chuẩn hóa và chuyển sang phân hệ phân loại mẫu giấy tờ.

#### 6. Luồng thay thế / Ngoại lệ
- **Tệp bị hỏng hoặc sai định dạng:** Tệp không thể giải mã thành ảnh (corrupted file) hoặc không đúng định dạng cho phép -> Hệ thống trả về mã lỗi: `INVALID_IMAGE_FORMAT` kèm thông báo chi tiết.
- **Dung lượng vượt quá giới hạn:** Tệp vượt quá dung lượng cho phép -> Hệ thống từ chối xử lý và yêu cầu giảm độ phân giải xuống mức phù hợp.
- **Ảnh quá mờ / đen hoàn toàn:** Hệ thống kiểm tra sơ bộ phát hiện độ sắc nét quá thấp (Blur score dưới sàn tối thiểu) -> Trả về cảnh báo ảnh không đủ điều kiện xử lý OCR ngay tại tầng tiền xử lý.

#### 7. Kết quả sau khi thực hiện
- Hình ảnh chứng từ được chuẩn hóa sạch, đúng chiều đọc và sẵn sàng cho công đoạn nhận dạng ký tự quang học.

#### 8. Business Rules
- Khi xử lý thẻ CCCD, nếu phía client cung cấp 2 ảnh (mặt trước và mặt sau), hệ thống phải gom nhóm và xử lý đồng thời trong cùng một ngữ cảnh bóc tách để liên kết thông tin 2 mặt.
- Tiền xử lý không được làm biến dạng tỷ lệ khung hình (Aspect Ratio) hoặc làm suy giảm chất lượng các chi tiết vi mô của ký tự.

#### 9. Điểm chưa thống nhất
- Cơ chế hỗ trợ định dạng ảnh chụp từ điện thoại iPhone (tệp đuôi `.HEIC`): Có tự động chuyển đổi sang JPEG trên hệ thống hay bắt buộc phía client phải chuyển đổi trước khi gửi?

---

### ĐẶC TẢ 2: TỰ ĐỘNG NHẬN DIỆN VÀ PHÂN LOẠI MẪU GIẤY TỜ

#### 1. Tên chức năng
Tự động nhận diện và phân loại mẫu giấy tờ (Automated Document Classification for OCR).

#### 2. Mục đích
Ứng dụng thị giác máy tính để tự động nhận biết cấu trúc, bố cục thị giác và tiêu đề văn bản nhằm phân loại chính xác giấy tờ thuộc mẫu biểu nào, từ đó áp dụng khuôn mẫu bóc tách ký tự phù hợp nhất.

#### 3. Actor
- Dịch vụ phân loại AI (Classification Engine)
- Hệ thống (System)

#### 4. Điều kiện trước
- Hình ảnh chứng từ đã hoàn thành công đoạn tiền xử lý.

#### 5. Luồng chính
1. Hệ thống quét bố cục tổng thể, các dấu hiệu đặc trưng (quốc huy, hoa văn bảo an, con dấu, tiêu đề quốc hiệu):
2. Hệ thống phân loại chứng từ vào một trong các loại danh mục tài liệu được hỗ trợ:
   - `CCCD_CHIP_FRONT` / `CCCD_CHIP_BACK`: Thẻ Căn cước công dân gắn chip (mặt trước / mặt sau).
   - `CCCD_12_FRONT` / `CCCD_12_BACK`: Thẻ Căn cước công dân 12 số không chip / CMND.
   - `BIRTH_CERTIFICATE`: Giấy khai sinh (bản chính, bản sao trích lục).
   - `CT07_RESIDENCE_CERTIFICATE`: Giấy xác nhận thông tin về cư trú (Mẫu CT07).
   - `STUDENT_CARD_OR_CERTIFICATE`: Thẻ học sinh / sinh viên hoặc Giấy xác nhận của cơ sở đào tạo.
   - `DISABILITY_CERTIFICATE`: Giấy xác nhận mức độ khuyết tật hoặc hồ sơ bệnh án.
3. Hệ thống trả về mã định danh loại tài liệu (`docTypeCode`) kèm chỉ số tin cậy phân loại (Classification Confidence).
4. Hệ thống nạp bộ quy tắc bóc tách trường tương ứng với loại tài liệu vừa nhận diện để phục vụ bước bóc tách tiếp theo.

#### 6. Luồng thay thế / Ngoại lệ
- **Tài liệu không thuộc danh mục hỗ trợ:** Ảnh tải lên là chứng từ khác (ví dụ: bằng lái xe, hóa đơn, hộ chiếu, ảnh chụp ngẫu nhiên) -> Hệ thống tự động gán nhãn `UNSUPPORTED_DOCUMENT` kèm lý do nhận diện và dừng tiến trình bóc tách.
- **Tài liệu bị che khuất tiêu đề và con dấu:** Không đủ đặc trưng để phân biệt giữa Giấy khai sinh và văn bản hành chính thông thường -> Gán nhãn `UNKNOWN_DOCUMENT` và chuyển cảnh báo chất lượng hình ảnh về cho client.

#### 7. Kết quả sau khi thực hiện
- Xác định chính xác loại văn bản của từng tệp ảnh, sẵn sàng kích hoạt đúng khuôn mẫu bóc tách ký tự cho từng trường tương ứng.

#### 8. Business Rules
- Nếu người dùng nộp CCCD mà chỉ gửi 1 ảnh mặt sau, hệ thống phải phân loại rõ là "Mặt sau CCCD" và thông báo cần bổ sung mặt trước mới đủ bộ trường thông tin cơ bản.
- Tỷ lệ tin cậy phân loại mẫu giấy tờ phải đạt trên 0.85; nếu dưới mức này, tài liệu bị coi là không xác định được danh tính mẫu.

#### 9. Điểm chưa thống nhất
- Phân biệt giữa Giấy khai sinh viết tay cũ (trước năm 2000) và Giấy khai sinh in vi tính hiện đại: Có cần chia thành 2 mã loại bóc tách riêng biệt hay dùng chung một bộ trích xuất?

---

### ĐẶC TẢ 3: BÓC TÁCH QUANG HỌC CÁC TRƯỜNG DỮ LIỆU ĐỊNH DANH & CHẤM ĐIỂM TIN CẬY

#### 1. Tên chức năng
Bóc tách quang học các trường dữ liệu định danh & chấm điểm tin cậy (Field-level Data Extraction & Confidence Scoring).

#### 2. Mục đích
Trích xuất toàn bộ các ký tự chữ và số trên từng vùng thông tin của giấy tờ, chuyển đổi hình ảnh thành dữ liệu có cấu trúc, đồng thời tính toán điểm tin cậy độc lập (Field Confidence Score) từ 0.0 đến 1.0 cho từng trường.

#### 3. Actor
- Động cơ OCR đa phương thức (Multimodal OCR Engine)
- Hệ thống (System)

#### 4. Điều kiện trước
- Tài liệu đã được phân loại thành công vào một mẫu giấy tờ cụ thể.

#### 5. Luồng chính
1. Hệ thống kích hoạt bộ trích xuất dữ liệu tương ứng với loại giấy tờ đã nhận diện.
2. Hệ thống bóc tách các trường dữ liệu định danh chi tiết:
   - **Đối với Thẻ Căn cước công dân (CCCD):**
     - Số Căn cước công dân / Số định danh (12 chữ số).
     - Họ và tên (chữ hoa có dấu).
     - Ngày tháng năm sinh (định dạng chuẩn `DD/MM/YYYY`).
     - Giới tính, Quốc tịch, Quê quán, Nơi thường trú.
     - Ngày cấp, Ngày hết hạn giá trị, Đặc điểm nhân dạng (mặt sau).
   - **Đối với Giấy khai sinh:**
     - Số văn bản, Số quyển trích lục.
     - Họ tên người được khai sinh, Ngày tháng năm sinh, Giới tính, Dân tộc.
     - Nơi sinh / Nơi đăng ký khai sinh.
     - Họ tên, năm sinh, số định danh của Cha và Mẹ.
   - **Đối với Giấy xác nhận cư trú (CT07):**
     - Họ tên chủ hộ, Thông tin các thành viên trong gia đình kèm số định danh và mối quan hệ với chủ hộ.
   - **Đối với Thẻ sinh viên / Giấy xác nhận trường:**
     - Tên cơ sở đào tạo, Họ tên học sinh/sinh viên, Mã số sinh viên, Niên khóa đào tạo.
3. Đối với từng trường thông tin bóc tách được, Hệ thống đo lường và chấm **Điểm tin cậy độc lập (Confidence Score)** từ 0.0 đến 1.0:
   - Điểm số phản ánh mức độ rõ nét của nét chữ, độ tự tin của mô hình thị giác và mức độ chuẩn mực ngữ nghĩa tiếng Việt của từ bóc tách.
4. Đóng gói kết quả bóc tách thành danh sách các cặp giá trị: `[Tên trường, Giá trị ký tự, Điểm tin cậy]`.

#### 6. Luồng thay thế / Ngoại lệ
- **Ký tự bị lóa đèn flash hoặc vết ố:** Ví dụ 3 số cuối của dãy số CCCD bị ánh đèn flash che phủ -> Hệ thống trích xuất phần chữ số đọc được, phần bị lóa đánh dấu ký tự không đọc được (`?`) và hạ điểm tin cậy của trường đó xuống mức thấp (ví dụ 0.3 - 0.5).
- **Chữ viết tay cổ bị nhòe:** Trên giấy khai sinh cũ, họ tên hoặc ngày sinh bị ố vàng, nét mực phai -> Bóc tách giá trị phỏng đoán kèm cờ cảnh báo chữ viết tay độ tin cậy thấp.

#### 7. Kết quả sau khi thực hiện
- Bộ dữ liệu định danh hoàn chỉnh dưới dạng số hóa có cấu trúc.
- Mỗi trường dữ liệu đều có thước đo định lượng về chất lượng nhận dạng, phục vụ cho việc đối soát tự động.

#### 8. Business Rules
- **Nguyên tắc chống ảo giác (Anti-Hallucination):** Mô hình OCR tuyệt đối không được tự ý bịa thêm ký tự hoặc tự động sửa số CCCD nếu hình ảnh thực tế không hiển thị ký tự đó; nếu không rõ, bắt buộc phải trả về điểm tin cậy thấp.
- Định dạng ngày tháng năm trích xuất phải được chuẩn hóa về định dạng chuẩn quốc tế hoặc cấu trúc ngày hợp lệ.

#### 9. Điểm chưa thống nhất
- Có cần trích xuất và trả về tọa độ khung bao trực quan (Bounding Box) của từng trường chữ trên ảnh để client vẽ khung bôi sáng hay không?

---

### ĐẶC TẢ 4: THẨM ĐỊNH NGƯỠNG TIN CẬY OCR ĐỘNG & CẢNH BÁO LỖI HÌNH ẢNH

#### 1. Tên chức năng
Thẩm định ngưỡng tin cậy OCR động & cảnh báo lỗi hình ảnh (Dynamic OCR Threshold Auditing & Image Quality Warning).

#### 2. Mục đích
So sánh kết quả điểm tin cậy OCR với các ngưỡng an toàn được cấu hình động từ cơ sở dữ liệu, kiểm tra các trường thông tin cốt lõi (Crucial Fields), tự động đưa ra kết luận: Kết quả OCR đạt chuẩn, cần cảnh báo chụp lại, hay từ chối tiếp nhận.

#### 3. Actor
- Động cơ đối soát ngưỡng (Threshold Validation Engine)
- Hệ thống gọi dịch vụ (Client / Core System)

#### 4. Điều kiện trước
- Đã có dữ liệu bóc tách và bảng điểm tin cậy từng trường từ công đoạn OCR.
- Đã nạp cấu hình ngưỡng tin cậy tương ứng với loại giấy tờ từ cơ sở dữ liệu.

#### 5. Luồng chính
1. Hệ thống truy xuất cấu hình ngưỡng áp dụng cho loại tài liệu đang xử lý:
   - Ngưỡng tin cậy OCR tổng thể (`OVERALL_THRESHOLD`, ví dụ: 0.85).
   - Danh sách các trường cốt lõi bắt buộc (`CRUCIAL_FIELDS`, ví dụ: Số CCCD, Họ tên, Ngày sinh).
   - Ngưỡng tin cậy tối thiểu cho từng trường cốt lõi (ví dụ: Số CCCD >= 0.90, Họ tên >= 0.85).
2. Hệ thống thực hiện tính toán và kiểm tra 2 bước:
   - **Bước 1 - Kiểm tra điểm trung bình:** Tính điểm tin cậy trung bình của toàn bộ các trường bóc tách được và so sánh với `OVERALL_THRESHOLD`.
   - **Bước 2 - Rà soát trường cốt lõi:** Kiểm tra độc lập từng trường trong danh sách `CRUCIAL_FIELDS`. Điểm của trường cốt lõi phải đồng thời vượt qua ngưỡng sàn riêng biệt.
3. Đánh giá trạng thái kết quả OCR:
   - *Trường hợp Đạt chuẩn (OCR Passed):* Cả điểm trung bình và toàn bộ trường cốt lõi đều đạt ngưỡng -> Trả về trạng thái `SUCCESS`, cung cấp đầy đủ dữ liệu bóc tách.
4. Đóng gói kết quả phản hồi gửi lại cho hệ thống gọi.

#### 6. Luồng thay thế / Ngoại lệ
- **Ảnh mờ toàn phần (Điểm trung bình dưới ngưỡng):** Toàn bộ ảnh bị nhòe nét hoặc chụp rung tay -> Hệ thống trả về trạng thái `FAILED_THRESHOLD_OVERALL`, kèm thông điệp: "Ảnh chụp quá mờ, không đảm bảo độ rõ nét để đọc văn bản. Vui lòng chụp lại".
- **Cháy sáng / Lóa cục bộ ở trường cốt lõi:** Tổng thể ảnh rất rõ nhưng riêng trường Số CCCD bị lóa sáng (điểm tin cậy < 0.90) -> Hệ thống trả về trạng thái `WARNING_CRUCIAL_FIELD_LOW_CONFIDENCE`, chỉ đích danh: "Trường Số CCCD bị chói sáng hoặc mờ nét" để client thông báo chính xác cho người dùng kiểm tra lại vùng đó.
- **Trường cốt lõi bị khuyết thiếu (Missing Field):** Ảnh chụp bị cắt góc làm mất hẳn vị trí của trường Họ tên hoặc Số CCCD -> Trả về lỗi `MISSING_CRUCIAL_FIELD`.

#### 7. Kết quả sau khi thực hiện
- Đưa ra kết luận minh bạch về chất lượng OCR của tài liệu.
- Ngăn chặn triệt để tình trạng dữ liệu OCR rác, mờ hoặc sai lệch lọt vào các khâu xử lý tiếp theo của ứng dụng.

#### 8. Business Rules
- **Quyền phủ quyết của Trường cốt lõi (Crucial Field Veto):** Dù điểm tin cậy trung bình của tài liệu đạt mức rất cao (ví dụ 0.92) nhưng nếu chỉ một trường cốt lõi duy nhất (như Số CCCD) bị điểm thấp dưới ngưỡng sàn quy định, toàn bộ kết quả OCR vẫn bị đánh dấu là không đạt chuẩn an toàn.
- Toàn bộ ngưỡng so sánh phải được nạp động từ CSDL, không cố định cứng trong mã nguồn.

#### 9. Điểm chưa thống nhất
- Khi kết quả bị cảnh báo điểm thấp, hệ thống OCR nên chỉ trả về mã lỗi cảnh báo hay vẫn trả kèm theo chuỗi ký tự đã bóc tách được để client linh hoạt hiển thị cho người dùng tự sửa?

---

### ĐẶC TẢ 5: QUẢN TRỊ QUY TẮC BÓC TÁCH VÀ CẤU HÌNH NGƯỠNG TIN CẬY OCR

#### 1. Tên chức năng
Quản trị quy tắc bóc tách và cấu hình ngưỡng tin cậy OCR (OCR Rules & Threshold Configuration Management).

#### 2. Mục đích
Cung cấp công cụ cho Quản trị viên (Admin) tùy biến danh sách các trường bóc tách, định nghĩa danh sách các trường cốt lõi cho từng loại giấy tờ và tinh chỉnh các ngưỡng tin cậy OCR theo thời gian thực mà không cần sửa code hay triển khai lại dịch vụ.

#### 3. Actor
- Quản trị viên hệ thống (Admin)
- Dịch vụ quản lý cấu hình (Config Subsystem)

#### 4. Điều kiện trước
- Admin đăng nhập bằng tài khoản có quyền cấu hình hệ thống AI.

#### 5. Luồng chính
1. Admin truy cập màn hình "Quản trị Ngưỡng & Quy tắc OCR Giấy tờ".
2. Hệ thống hiển thị danh mục các loại giấy tờ hỗ trợ (CCCD chip, CCCD cũ, Giấy khai sinh, CT07...).
3. Admin chọn một loại giấy tờ để xem và điều chỉnh:
   - Cài đặt ngưỡng tin cậy tổng thể (ví dụ: điều chỉnh từ 0.80 lên 0.85).
   - Đánh dấu hoặc bỏ đánh dấu một trường có phải là "Trường cốt lõi" (Crucial Field) hay không.
   - Thiết lập ngưỡng điểm sàn riêng cho từng trường cốt lõi.
   - Thêm/bớt các trường thông tin cần mô hình OCR trích xuất.
4. Admin nhấn nút "Lưu và Áp dụng cấu hình".
5. Hệ thống kiểm tra tính hợp lệ của các thông số (ngưỡng từ 0.0 đến 1.0, danh sách trường hợp lệ), lưu phiên bản mới vào cơ sở dữ liệu và làm mới bộ nhớ đệm (Cache).
6. Quy tắc và ngưỡng mới được kích hoạt áp dụng ngay lập tức cho các yêu cầu OCR tiếp theo.

#### 6. Luồng thay thế / Ngoại lệ
- **Giá trị ngưỡng không hợp lệ:** Admin nhập giá trị vượt ngoài khoảng [0.0, 1.0] (ví dụ nhập 85 thay vì 0.85) -> Hệ thống báo lỗi và từ chối cập nhật.
- **Để trống trường cốt lõi:** Admin bỏ chọn toàn bộ trường cốt lõi của loại giấy tờ CCCD -> Hệ thống cảnh báo bắt buộc phải có ít nhất trường Số CCCD và Họ tên là trường cốt lõi để đảm bảo an toàn định danh.

#### 7. Kết quả sau khi thực hiện
- Quản trị viên hoàn toàn chủ động trong việc siết chặt (khi cần tăng độ chính xác) hoặc nới lỏng (khi cần hỗ trợ các thiết bị camera chụp kém) ngưỡng chất lượng của mô hình OCR.

#### 8. Business Rules
- Việc cập nhật cấu hình ngưỡng chỉ áp dụng cho các lượt gọi OCR phát sinh sau thời điểm lưu, không làm thay đổi trạng thái đối soát của các kết quả OCR đã lưu trong lịch sử.
- Mọi thao tác chỉnh sửa ngưỡng phải được ghi nhận lịch sử kiểm toán (Audit Log) gồm: Tài khoản Admin thực hiện, giá trị ngưỡng cũ, giá trị ngưỡng mới, thời điểm cập nhật.

#### 9. Điểm chưa thống nhất
- Cơ chế phân tách ngưỡng theo môi trường: Có hỗ trợ cài đặt bộ ngưỡng riêng cho môi trường Kiểm thử (Staging) và môi trường Vận hành thực tế (Production) trên cùng một giao diện hay không?

---

## 3. BẢNG TỔNG HỢP VÀ ÁNH XẠ TRẠNG THÁI OCR

| STT | Tên đặc tả nghiệp vụ OCR | Trọng tâm kỹ thuật xử lý | Trạng thái luồng xử lý OCR |
| :--- | :--- | :--- | :--- |
| **1** | Tiếp nhận & tiền xử lý hình ảnh | Kiểm tra tệp, xoay thẳng & khử nhiễu ảnh | Tiếp nhận -> Ảnh đã chuẩn hóa / Lỗi tệp |
| **2** | Nhận diện & phân loại mẫu giấy tờ | Xác định cấu trúc mẫu tài liệu (CCCD, Khai sinh...) | Xác định `docTypeCode` / `UNSUPPORTED` |
| **3** | Bóc tách quang học & chấm điểm | Số hóa văn bản & tính điểm tin cậy từng trường | Trích xuất hoàn tất kèm bảng Confidence Score |
| **4** | Thẩm định ngưỡng tin cậy OCR động | Đối soát ngưỡng trung bình & kiểm tra trường cốt lõi | Đạt chuẩn (`SUCCESS`) / Cảnh báo mờ (`WARNING`) |
| **5** | Quản trị quy tắc & cấu hình ngưỡng | Thiết lập tham số sàn chất lượng thời gian thực | Cấu hình lưu phiên bản mới, áp dụng tức thời |
