# TÀI LIỆU ĐẶC TẢ NGHIỆP VỤ PHÂN HỆ
## MODULE: TƯ VẤN CHUYÊN GIA & QUẢN LÝ ĐẶT LỊCH (EXPERT CONSULTATION & BOOKING MANAGEMENT)
**Nhánh phát triển:** `feature/specification_expertConsultationAndBooking`  
**Dự án:** TaxKeep VN - Dịch vụ Trí tuệ Nhân tạo Hỗ trợ Thuế TNCN (TaxAIService)  
**Ngày hoàn thiện đặc tả:** 28/09/2026  
**Trạng thái:** Đặc tả nghiệp vụ mức Conceptual / Sẵn sàng Review & Thống nhất  

---

## 1. TỔNG QUAN PHÂN HỆ

Phân hệ **Tư vấn chuyên gia (Expert Consultation)** là cầu nối trực tiếp giữa người dùng (cá nhân kinh doanh, doanh nghiệp vừa và nhỏ, người dùng có nhu cầu xử lý bài toán kế toán - thuế chuyên sâu) và các chuyên gia có chứng chỉ hành nghề được hệ thống kiểm định.

Hệ thống đóng vai trò trung gian xác thực, điều phối lịch hẹn, cung cấp không gian tương tác trực tuyến 1-1, đảm bảo tính bảo mật dữ liệu tài chính và thực thi cơ chế giao dịch an toàn thông qua mô hình **Tạm giữ tiền bảo đảm (Escrow)**.

---

## 2. DANH SÁCH CÁC ĐẶC TẢ NGHIỆP VỤ CỐT LÕI

1. [Đặc tả 1: Đăng ký & Thẩm định chuyên gia (Expert Registration & Review)](#đặc-tả-1-đăng-ký-và-thẩm-định-hồ-sơ-chuyên-gia-expert-registration--application-review)
2. [Đặc tả 2: Tìm kiếm & lựa chọn chuyên gia (Search & Select Expert)](#đặc-tả-2-tìm-kiếm--lựa-chọn-chuyên-gia-search--select-expert)
3. [Đặc tả 3: Đặt lịch tư vấn (Booking Consultation)](#đặc-tả-3-đặt-lịch-tư-vấn-booking-consultation)
4. [Đặc tả 4: Thanh toán & tạm giữ tiền (Payment & Escrow)](#đặc-tả-4-thanh-toán--tạm-giữ-tiền-payment--escrow)
5. [Đặc tả 5: Thực hiện tư vấn 1-1 (1-on-1 Consultation Execution)](#đặc-tả-5-thực-hiện-tư-vấn-1-1-1-on-1-consultation-execution)
6. [Đặc tả 6: Đánh giá & feedback (Rating & Feedback)](#đặc-tả-6-đánh-giá--feedback-rating--feedback)
7. [Đặc tả 7: Giải ngân & xử lý tranh chấp (Disbursement & Dispute Handling)](#đặc-tả-7-giải-ngân--xử-lý-tranh-chấp-disbursement--dispute-handling)
8. [Đặc tả 8: Quản lý tư vấn của chuyên gia (Expert Consultation Management)](#đặc-tả-8-quản-lý-tư-vấn-của-chuyên-gia-expert-consultation-management)

---

### ĐẶC TẢ 1: ĐĂNG KÝ VÀ THẨM ĐỊNH HỒ SƠ CHUYÊN GIA (EXPERT REGISTRATION & APPLICATION REVIEW)

#### 1. Tên chức năng
Đăng ký trở thành chuyên gia và thẩm định hồ sơ chuyên gia (Expert Registration & Application Review Flow).

#### 2. Mục đích
- Tiếp nhận hồ sơ đăng ký tư cách chuyên gia từ người dùng hiện tại trên nền tảng.
- Thu thập, xác thực thông tin năng lực, kinh nghiệm, lĩnh vực chuyên môn thuế/kế toán.
- Quản lý tải lên và thẩm định tính pháp lý của chứng chỉ hành nghề/văn bằng chuyên môn.
- Cho phép chuyên gia đề xuất mức phí tư vấn theo từng loại phiên và kiểm soát trong khung giá trần/sàn của hệ thống.
- Cung cấp quy trình thẩm định đa trạng thái cho Admin/Reviewer: Phê duyệt (cấp vai trò Expert), Yêu cầu bổ sung tài liệu, hoặc Từ chối kèm lý do văn bản.
- Lưu trữ lịch sử toàn diện và nhật ký kiểm toán (Audit Trail) cho toàn bộ vòng đời hồ sơ.

#### 3. Actor
- **Người dùng / Ứng viên chuyên gia (User / Expert Applicant):** Khởi tạo hồ sơ, lưu bản nháp (Draft), cập nhật thông tin/chứng chỉ, nộp hồ sơ chính thức (Submit), bổ sung thông tin khi có yêu cầu (NeedSupplement), theo dõi trạng thái hồ sơ.
- **Quản trị viên / Đội ngũ thẩm định (Admin / Reviewer):** Tiếp nhận danh sách hồ sơ, tra cứu đối soát tính xác thực của từng văn bằng/chứng chỉ, phê duyệt, từ chối kèm lý do bắt buộc, hoặc yêu cầu bổ sung thông tin.
- **Hệ thống (System):** Tự động kiểm tra tính hợp lệ của dữ liệu, kiểm soát ràng buộc duy nhất 1 hồ sơ hoạt động tại 1 thời điểm, sinh mã hồ sơ (`EXP-yyyyMM-XXXX`), kiểm soát khung giá sàn/trần, ghi nhật ký kiểm toán (Audit Log), nâng quyền tài khoản khi được duyệt và gửi thông báo hệ thống theo thời gian thực.

#### 4. Điều kiện trước
1. Người đăng ký đã có tài khoản người dùng trên hệ thống với trạng thái hoạt động (`Status == "active"`).
2. Người dùng không có hồ sơ đăng ký chuyên gia nào đang trong quá trình xử lý ở trạng thái:
   - `PendingReview` (Đang chờ xét duyệt)
   - `NeedSupplement` (Đang chờ bổ sung)
3. Người dùng không bị cấm đăng ký chuyên gia do vi phạm đạo đức/quy chế nền tảng trước đó.
4. Admin/Reviewer đã đăng nhập với thẩm quyền xét duyệt hồ sơ chuyên môn.

#### 5. Cấu trúc dữ liệu hồ sơ đăng ký
1. **Thông tin cá nhân & Giới thiệu:**
   - Họ và tên (`fullName`).
   - Đường dẫn ảnh đại diện (`avatarUrl`).
   - Chức danh công việc (`jobTitle`).
   - Đơn vị / Công ty đang công tác (`companyName`).
   - Tiểu sử / Giới thiệu tóm tắt bản thân (`bio`).
2. **Kinh nghiệm làm việc:**
   - Số năm kinh nghiệm thực tế (`yearsOfExperience`).
   - Vị trí/chức vụ công việc hiện tại (`currentPosition`).
   - Mô tả chi tiết kinh nghiệm chuyên môn trong lĩnh vực thuế, kế toán, pháp lý doanh nghiệp (`experienceDescription`).
3. **Lĩnh vực chuyên môn thế mạnh (`Specializations`):**
   - Lựa chọn 1 hoặc nhiều lĩnh vực từ danh mục hệ thống quản lý động (ví dụ: Quyết toán thuế TNCN/TNDN, Hoàn thuế, Chuyển giá, Kế toán nội bộ, Tư vấn chính sách thuế, Đại lý thuế...).
4. **Hồ sơ chứng chỉ / Bằng cấp (`Certificates`):**
   - Loại chứng chỉ (`certificateType`), tên chứng chỉ (`certificateName`), số chứng chỉ (`certificateNumber`), cơ quan cấp (`issuingOrganization`), ngày cấp (`issueDate`).
   - Thời hạn hiệu lực:
     - *Chứng chỉ có thời hạn:* `HasExpiry = true` -> Bắt buộc nhập ngày hết hạn (`expiryDate`).
     - *Chứng chỉ không có thời hạn:* `HasExpiry = false` -> `expiryDate = null` (không bắt buộc).
   - Tệp đính kèm (`fileUrl`, `fileType`, `fileSize`) định dạng PDF, PNG, JPG/JPEG.
   - Trạng thái xác minh của từng chứng chỉ: `PendingVerification`, `Verified`, `Rejected`, `Expired`.
5. **Đề xuất biểu phí dịch vụ (`Fee Proposals`):**
   - Loại phiên tư vấn (`SessionType`: `ONLINE_MEETING`, `CHAT`, `VOICE_CALL`).
   - Thời lượng buổi tư vấn theo phút (`durationMinutes`: 30, 45, 60, 90, 120 phút...).
   - Mức phí đề xuất (`proposedFee` tính bằng VNĐ). Phải nằm trong giới hạn cấu hình của nền tảng: $\text{Giá sàn (MinFee)} \le \text{Giá đề xuất} \le \text{Giá trần (MaxFee)}$.

#### 6. Luồng nghiệp vụ chi tiết

##### A. Luồng ứng viên đăng ký (Candidate Application Flow)
1. **Truy cập & Kiểm tra điều kiện:** Người dùng chọn "Đăng ký làm Chuyên gia". Hệ thống kiểm tra điều kiện (BR-01, BR-02). Nếu đang có hồ sơ `PendingReview` hoặc `NeedSupplement`, hệ thống điều hướng vào xem hồ sơ hiện tại, không cho tạo hồ sơ mới.
2. **Nhập liệu & Lưu bản nháp (Draft):**
   - Ứng viên nhập thông tin cá nhân, kinh nghiệm, chọn chuyên môn và đề xuất mức phí.
   - Ứng viên tải lên từng file chứng chỉ đính kèm.
   - Ứng viên có thể lưu bản nháp (`Draft`) nhiều lần, quay lại sửa đổi, xóa hoặc thêm mới chứng chỉ. Trạng thái `Draft` chưa gửi đến Admin.
3. **Nộp hồ sơ chính thức (Submit Application):**
   - Ứng viên nhấn "Nộp hồ sơ xét duyệt".
   - Hệ thống kiểm tra toàn diện: bắt buộc các trường thông tin cốt lõi, tối thiểu có ít nhất 1 chứng chỉ hợp lệ (BR-05), ngày cấp/hết hạn hợp lệ (BR-06), phí đề xuất nằm trong khung sàn - trần (BR-08).
   - Nếu hợp lệ: Trạng thái chuyển từ `Draft` $\rightarrow$ **`PendingReview`**. Hệ thống tự sinh mã hồ sơ `EXP-yyyyMM-XXXX`, ghi nhận thời điểm gửi, tạo nhật ký kiểm toán (BR-11) và gửi thông báo đến Admin.

##### B. Luồng thẩm định & Ra quyết định của Admin (Review Flow)
1. **Tiếp nhận & Xem chi tiết:** Admin xem danh bạ hồ sơ chờ duyệt, lọc theo trạng thái/chuyên môn, mở chi tiết hồ sơ để đối soát thông tin năng lực và tải xem tài liệu chứng chỉ.
2. **Thẩm định từng chứng chỉ (Verify Certificate):** Admin tra cứu tính xác thực qua cổng thông tin nhà nước (Bộ Tài chính, Tổng cục Thuế, Hội Kiểm toán viên) hoặc kiểm tra nội bộ:
   - Chuyển trạng thái chứng chỉ sang `Verified` hoặc `Rejected` (kèm ghi chú lý do).
3. **Ra quyết định phê duyệt (Approve):**
   - Điều kiện: Các chứng chỉ chuyên môn bắt buộc phải còn hạn tại thời điểm xét duyệt (BR-07).
   - Hệ thống chuyển trạng thái hồ sơ sang **`Approved`**.
   - Hệ thống tự động nâng quyền tài khoản người dùng: `RoleId = 3`, `UserRole = "expert"`.
   - Hệ thống tự động khởi tạo bản ghi hồ sơ chuyên gia chính thức (`ExpertProfile`).
   - Ghi nhận Audit Log và gửi thông báo chúc mừng cho Chuyên gia.
4. **Ra quyết định yêu cầu bổ sung (Request Supplement):**
   - Áp dụng khi hồ sơ mờ thông tin, thiếu mặt sau chứng chỉ, hoặc cần làm rõ kinh nghiệm.
   - Admin bắt buộc nhập nội dung chi tiết cần bổ sung (BR-10).
   - Hệ thống chuyển trạng thái sang **`NeedSupplement`**, gửi thông báo đến ứng viên.
   - Ứng viên truy cập hồ sơ, cập nhật lại thông tin/tài liệu và nhấn nộp lại $\rightarrow$ Hồ sơ chuyển về **`PendingReview`** để Admin tái thẩm định.
5. **Ra quyết định từ chối (Reject):**
   - Áp dụng khi chứng chỉ giả mạo, không đủ tiêu chuẩn chuyên môn nền tảng.
   - Admin bắt buộc nhập lý do từ chối cụ thể (BR-09).
   - Hệ thống chuyển trạng thái sang **`Rejected`**, ghi Audit Log và gửi thông báo kết quả cho ứng viên.
   - Ứng viên giữ nguyên vai trò người dùng bình thường và được quyền tạo hồ sơ mới độc lập sau khi khắc phục (BR-04).

#### 7. Sơ đồ vòng đời trạng thái hồ sơ (Lifecycle State Machine)

```text
       [ Khởi tạo ]
            │
            ▼
       ┌─────────┐         Cập nhật nháp / Tải chứng chỉ
       │  Draft  │ ◄─────────────────────────────────────┐
       └────┬────┘                                       │
            │ Nộp hồ sơ (Submit)                         │
            ▼                                            │
   ┌─────────────────┐       Admin yêu cầu bổ sung       │
   │  PendingReview  ├───────────────────┐               │
   └────────┬────────┘                   ▼               │
            │                   ┌──────────────────┐     │
            │                   │  NeedSupplement  │ ────┘
            │                   └────────┬─────────┘
            │                            │ Ứng viên nộp lại
            │                            ▼
            │                   ┌──────────────────┐
            │ ◄─────────────────┤  PendingReview   │
            │                   └──────────────────┘
            ├────────────────────────────────────┐
            ▼ Phê duyệt                          ▼ Từ chối
    ┌───────────────┐                    ┌──────────────┐
    │   Approved    │                    │   Rejected   │
    └───────┬───────┘                    └───────┬──────┘
            │                                    │
            ▼ Kích hoạt Expert                   ▼ Cho phép nộp mới
   Quản lý hồ sơ chuyên gia             Đăng ký lại phiên mới
   (Expert Profile Management)          (Lưu vết lịch sử cũ)
```

#### 8. Quy tắc nghiệp vụ (Business Rules)
- **BR-01 (Điều kiện tài khoản):** Chỉ tài khoản người dùng hợp lệ, đang hoạt động (`active`) và không có vi phạm bị khóa mới được nộp đơn đăng ký làm chuyên gia.
- **BR-02 (Giới hạn hồ sơ hoạt động):** Tại một thời điểm, mỗi người dùng chỉ được có tối đa một hồ sơ ở trạng thái `PendingReview` hoặc `NeedSupplement`. Không cho phép gửi đơn song song.
- **BR-03 (Lưu vết lịch sử):** Mọi lần đăng ký đều được lưu trữ thành các phiên bản hồ sơ độc lập kèm mã định danh duy nhất (`EXP-yyyyMM-XXXX`) để đối soát và tra cứu lịch sử.
- **BR-04 (Cho phép đăng ký lại):** Khi hồ sơ bị `Rejected`, người dùng được phép tạo một bộ hồ sơ đăng ký mới sau khi hoàn thiện/khắc phục các vấn đề trước đó.
- **BR-05 (Yêu cầu chứng chỉ tối thiểu):** Hồ sơ khi nộp chính thức bắt buộc phải đính kèm ít nhất một chứng chỉ/bằng cấp chuyên môn hợp lệ thuộc danh mục nền tảng chấp thuận (CPA, Chứng chỉ hành nghề đại lý thuế, Bằng Luật, Cử nhân Kế toán - Kiểm toán...).
- **BR-06 (Thời hạn chứng chỉ linh hoạt):** Trường `expiryDate` chỉ bắt buộc đối với loại chứng chỉ có thời hạn (`hasExpiry = true`); các chứng chỉ vĩnh viễn (`hasExpiry = false`) cho phép `expiryDate` mang giá trị rỗng/null.
- **BR-07 (Hiệu lực chứng chỉ khi phê duyệt):** Toàn bộ chứng chỉ chuyên môn bắt buộc phải còn thời hạn hiệu lực tại thời điểm Admin ra quyết định Phê duyệt (`Approved`).
- **BR-08 (Ràng buộc khung phí tư vấn):** Mức phí do ứng viên đề xuất cho từng loại phiên và thời lượng phải nằm trong khoảng sàn - trần được quy định bởi cấu hình hệ thống nền tảng: $\text{MinFee} \le \text{proposedFee} \le \text{MaxFee}$.
- **BR-09 (Bắt buộc lý do từ chối):** Admin bắt buộc phải nhập lý do giải trình cụ thể bằng văn bản khi ra quyết định từ chối (`Rejected`) hồ sơ.
- **BR-10 (Bắt buộc nội dung yêu cầu bổ sung):** Admin bắt buộc phải cung cấp hướng dẫn và yêu cầu chi tiết khi chuyển trạng thái hồ sơ sang `NeedSupplement`.
- **BR-11 (Ghi vết kiểm toán - Audit Trail):** Toàn bộ thao tác tác động lên hồ sơ (người gửi, người duyệt, thời gian, trạng thái cũ/mới, lý do từ chối/bổ sung) phải được tự động ghi nhận vào sổ nhật ký kiểm toán bất biến để phục vụ quản trị và giải quyết khiếu nại.

#### 9. Kết quả sau khi thực hiện
- Hồ sơ chuyển sang `Approved`: Ứng viên chính thức được cấp quyền Chuyên gia (Role `expert`), hệ thống tự động khởi tạo `ExpertProfile`, và chuyển tiếp sang phân hệ Quản lý hồ sơ chuyên gia & Đặt lịch tư vấn.
- Toàn bộ văn bằng, chứng chỉ được lưu trữ an toàn trên dịch vụ lưu trữ đám mây có gắn chữ ký bảo mật.

#### 10. Điểm chưa thống nhất & Phạm vi chuyển tiếp
- **Cơ chế phân cấp chuyên gia tự động:** Việc phân hạng chuyên gia (Junior, Senior, Master) dựa trên số năm kinh nghiệm hay dựa trên tổng số giờ tư vấn và điểm rating thực tế trên sàn sẽ được xử lý tại chức năng Xếp hạng chuyên gia.
- **Phạm vi không thuộc Đặc tả 1:** Các nghiệp vụ cấu hình Slot rảnh, tiếp nhận lịch đặt hẹn, phòng họp trực tuyến, thanh toán ký quỹ (Escrow), giải ngân và đánh giá sau phiên tư vấn thuộc phạm vi của các Đặc tả 2 đến 8 tiếp theo.

---

### ĐẶC TẢ 2: TÌM KIẾM & LỰA CHỌN CHUYÊN GIA (SEARCH & SELECT EXPERT)

#### 1. Tên chức năng
Tìm kiếm, lọc và xem thông tin chuyên gia.

#### 2. Mục đích
Giúp người dùng dễ dàng tìm kiếm, so sánh và lựa chọn đúng chuyên gia kế toán/thuế phù hợp với bài toán thực tế và ngân sách của mình.

#### 3. Actor
- Người dùng (User)
- Hệ thống (System)

#### 4. Điều kiện trước
- User đã đăng nhập vào hệ thống.
- Trong hệ thống có danh sách các chuyên gia đang ở trạng thái hoạt động (Active).

#### 5. Luồng chính
1. User truy cập vào tính năng "Tư vấn chuyên gia".
2. Hệ thống hiển thị danh sách các chuyên gia nổi bật hoặc được đề xuất dựa trên hành vi/nhu cầu phổ biến.
3. User sử dụng thanh công cụ để tìm kiếm và áp dụng các bộ lọc:
   - Theo lĩnh vực/chủ đề (Thuế doanh nghiệp, Kế toán xây dựng, Hộ kinh doanh, Báo cáo tài chính...).
   - Theo mức phí tư vấn (từ thấp đến cao, theo khoảng giá).
   - Theo đánh giá sao (Rating từ 4 sao trở lên).
   - Theo khung thời gian rảnh (Hôm nay, Ngày mai, Cuối tuần).
4. Hệ thống trả về danh sách chuyên gia thỏa mãn điều kiện lọc.
5. User nhấn vào một chuyên gia để xem chi tiết hồ sơ (Profile):
   - Ảnh đại diện, họ tên, danh hiệu/học vị.
   - Số năm kinh nghiệm, các chứng chỉ đã được xác minh.
   - Điểm đánh giá trung bình và số lượng phiên tư vấn đã hoàn thành.
   - Các bài nhận xét, feedback thực tế từ những khách hàng trước.
   - Lịch trống sắp tới và bảng biểu phí tư vấn.
6. User đưa ra quyết định và nhấn nút "Đặt lịch ngay" trên hồ sơ chuyên gia đã chọn.

#### 6. Luồng thay thế / Ngoại lệ
- **Không tìm thấy kết quả phù hợp với bộ lọc:** Hệ thống thông báo không có chuyên gia tương ứng, đồng thời đề xuất: nới lỏng bộ lọc, gợi ý hỏi trước với AI Assistant, hoặc để lại nhu cầu để hệ thống liên hệ hỗ trợ điều phối chuyên gia thủ công.
- **Chuyên gia vừa chuyển sang trạng thái bận/nghỉ phép:** Nếu User đang xem profile mà chuyên gia tắt nhận lịch, khi User nhấn đặt lịch, Hệ thống sẽ thông báo chuyên gia hiện đang tạm ngưng nhận ca và gợi ý danh sách chuyên gia tương đương.

#### 7. Kết quả sau khi thực hiện
- User chọn được chuyên gia ưng ý và sẵn sàng bước vào quy trình chọn khung giờ đặt lịch.

#### 8. Business Rules
- Chỉ những chuyên gia có trạng thái "Đã duyệt" và "Đang mở lịch nhận tư vấn" mới được hiển thị trên kết quả tìm kiếm.
- Thứ tự hiển thị mặc định (Ranking) phải ưu tiên dựa trên: Tỉ lệ phản hồi tốt, điểm rating trung bình, số ca hoàn thành thành công và mức độ sẵn sàng của lịch rảnh (tránh hiện chuyên gia không còn slot).
- Hệ thống làm mờ hoặc ẩn các thông tin định danh cá nhân mang tính riêng tư ngoài phạm vi chuyên môn.

#### 9. Điểm chưa thống nhất
- Người dùng tài khoản thông thường (Free/Basic) có được xem hồ sơ chuyên gia không, hay bắt buộc phải nâng cấp gói Premium mới được mở quyền tìm kiếm và xem chi tiết?
- Có cho phép thuật toán tự động gợi ý/ghép cặp (Auto-matching) dựa trên câu hỏi của User hay để User tự chọn 100% bằng tay?

---

### ĐẶC TẢ 3: ĐẶT LỊCH TƯ VẤN (BOOKING CONSULTATION)

#### 1. Tên chức năng
Khởi tạo và thiết lập lịch hẹn tư vấn (Booking Flow).

#### 2. Mục đích
Cho phép người dùng lựa chọn khung giờ phù hợp trên lịch rảnh của chuyên gia, cung cấp trước thông tin/tài liệu cần tư vấn và gửi yêu cầu đặt lịch hẹn.

#### 3. Actor
- Người dùng (User)
- Chuyên gia (Expert)
- Hệ thống (System)

#### 4. Điều kiện trước
- User đã chọn được một chuyên gia cụ thể.
- User có quyền sử dụng dịch vụ (thuộc gói Premium hoặc chấp nhận trả phí lẻ từng phiên).
- Chuyên gia có các khung giờ trống (Available slots) hợp lệ trong tương lai.

#### 5. Luồng chính
1. User nhấn "Đặt lịch" tại trang hồ sơ của Chuyên gia.
2. Hệ thống hiển thị lịch làm việc trực quan (Calendar view) gồm các ngày và các khung giờ (Slot) còn trống của Chuyên gia đó.
3. User bấm chọn ngày và khung giờ mong muốn (ví dụ: 14:00 - 15:00, ngày 30/09).
4. Hệ thống yêu cầu User điền thông tin tóm tắt cho buổi tư vấn:
   - Chủ đề cần tư vấn (chọn từ danh mục có sẵn).
   - Mô tả chi tiết vấn đề / câu hỏi trọng tâm.
   - Đính kèm chứng từ/báo cáo mẫu (nếu có, ví dụ: bảng cân đối kế toán, thông báo thuế, file Excel/PDF).
5. User kiểm tra thông tin tóm tắt buổi hẹn (Tên chuyên gia, thời gian, thời lượng, chủ đề, tổng chi phí dự kiến).
6. User xác nhận thông tin đặt lịch.
7. Hệ thống tiến hành **tạm khóa khung giờ (Hold slot)** này trong vòng 10 phút để tránh bị người khác đặt trùng, đồng thời chuyển trạng thái Booking thành **"Chờ thanh toán" (Pending Payment)**.
8. Hệ thống điều hướng User sang bước thanh toán.

#### 6. Luồng thay thế / Ngoại lệ
- **Slot vừa bị người khác chọn trước:** Tại thời điểm User ấn xác nhận, nếu slot đó đã bị một User khác giữ chỗ, Hệ thống thông báo: "Khung giờ này vừa có người đặt, vui lòng chọn khung giờ khác" và làm mới lại lịch rảnh.
- **Tệp đính kèm không hợp lệ:** File vượt quá dung lượng quy định (ví dụ > 25MB) hoặc không đúng định dạng cho phép -> Hệ thống cảnh báo yêu cầu tải lại file hợp lệ trước khi tiếp tục.
- **User không hoàn thành thanh toán trong 10 phút:** Quá hạn giữ chỗ, Hệ thống tự động hủy booking tạm thời, giải phóng slot về trạng thái trống cho người khác đặt.
- **User đặt lịch quá sát giờ hẹn:** Hệ thống không cho phép chọn các slot cách thời điểm hiện tại dưới X giờ (theo quy định Lead-time).

#### 7. Kết quả sau khi thực hiện
- Yêu cầu đặt lịch được tạo với mã Booking ID duy nhất.
- Khung giờ được khóa tạm thời chờ thanh toán xác thực.

#### 8. Business Rules
- Thời lượng mỗi phiên tư vấn được chuẩn hóa theo block (ví dụ: 45 phút hoặc 60 phút/phiên).
- Quy định thời gian đặt trước tối thiểu (Minimum Lead-time): User phải đặt trước thời điểm diễn ra phiên tư vấn tối thiểu 4 tiếng (hoặc 12 tiếng) để Chuyên gia kịp sắp xếp công việc và xem trước hồ sơ.
- Một User không được đặt 2 lịch hẹn trùng một khung giờ với 2 chuyên gia khác nhau.

#### 9. Điểm chưa thống nhất
- Cơ chế chấp nhận lịch: Lịch hẹn được **tự động xác nhận ngay sau khi thanh toán** hay Chuyên gia có quyền "Từ chối/Đồng ý tiếp nhận" trong vòng 2 tiếng sau khi User đặt?
- Số lượng tệp đính kèm tối đa và yêu cầu bảo mật mã hóa tệp dữ liệu kế toán nhạy cảm trước khi chuyên gia được phép xem.

---

### ĐẶC TẢ 4: THANH TOÁN & TẠM GIỮ TIỀN (PAYMENT & ESCROW)

#### 1. Tên chức năng
Xử lý thanh toán và cơ chế tạm giữ tiền dịch vụ (Escrow Management).

#### 2. Mục đích
Thu tiền từ người dùng cho phiên tư vấn, giữ khoản tiền này an toàn trong tài khoản trung gian của hệ thống và chỉ giải ngân cho chuyên gia sau khi buổi tư vấn hoàn thành đúng cam kết.

#### 3. Actor
- Người dùng (User)
- Cổng thanh toán / Ngân hàng đối tác (Payment Gateway)
- Hệ thống (System)

#### 4. Điều kiện trước
- Booking đang ở trạng thái "Chờ thanh toán" và còn trong thời gian giữ chỗ (10 phút).
- Hệ thống đã tính toán chính xác tổng chi phí (Bao gồm phí tư vấn của chuyên gia, phí nền tảng, thuế GTGT nếu có, và khấu trừ mã giảm giá nếu áp dụng).

#### 5. Luồng chính
1. Hệ thống hiển thị trang thanh toán với chi tiết đơn vị tiền tệ, các khoản phí cấu thành và các phương thức thanh toán:
   - Thẻ ngân hàng nội địa / Quốc tế (Visa, Mastercard).
   - Quét mã VietQR / Chuyển khoản ngân hàng.
   - Ví điện tử tích hợp (MoMo, ZaloPay...).
   - Trừ số dư Ví tài khoản trên nền tảng (nếu có nạp sẵn tiền).
2. User chọn phương thức thanh toán mong muốn và tiến hành xác thực giao dịch trên cổng thanh toán.
3. Cổng thanh toán gửi phản hồi xác nhận giao dịch thành công về Hệ thống.
4. Hệ thống ghi nhận giao dịch:
   - Chuyển trạng thái khoản tiền sang **"Đang tạm giữ" (Held in Escrow)** trong tài khoản trung gian của nền tảng.
   - Chuyển trạng thái Booking sang **"Đã xác nhận" (Confirmed / Booked)**.
   - Khóa vĩnh viễn slot lịch đó của Chuyên gia cho Booking này.
5. Hệ thống gửi thông báo xác nhận đặt lịch thành công kèm thông tin buổi hẹn (thời gian, đường link vào phòng họp trực tuyến) cho cả User và Chuyên gia qua Notification/Email/SMS.
6. Lịch hẹn được tự động đồng bộ vào lịch cá nhân của cả hai bên trên hệ thống.

#### 6. Luồng thay thế / Ngoại lệ
- **Giao dịch thanh toán thất bại (Tài khoản không đủ tiền, lỗi mạng, User hủy thanh toán):** Cổng thanh toán báo lỗi -> Hệ thống thông báo thanh toán không thành công, cho phép User thử lại với phương thức khác nếu còn trong thời hạn giữ slot.
- **Giao dịch treo / Chậm phản hồi từ ngân hàng:** Tiền đã bị trừ ở phía User nhưng hệ thống chưa nhận được tín hiệu -> Trạng thái chuyển sang "Đang đối soát thanh toán", gửi cảnh báo cho bộ phận CSKH để xác minh và giữ slot cho khách hàng.
- **User đã được cấp quyền miễn phí theo gói Premium:** Nếu gói thuê bao hàng tháng của User có quyền lợi "Tặng 1 phiên tư vấn miễn phí mỗi tháng", Hệ thống sẽ hiển thị tùy chọn: "Sử dụng lượt tư vấn miễn phí" -> Bỏ qua bước thanh toán tiền, trừ 1 lượt quota và xác nhận booking ngay.

#### 7. Kết quả sau khi thực hiện
- Khoản tiền tư vấn nằm trong diện quản lý bảo đảm của nền tảng, chưa được chuyển trực tiếp cho Chuyên gia.
- Lịch tư vấn chính thức được xác lập, phòng họp trực tuyến được chuẩn bị.

#### 8. Business Rules
- **Không thanh toán ngoài sàn:** Mọi giao dịch chuyển khoản cá nhân trực tiếp giữa User và Expert đều bị coi là vi phạm nghiêm trọng chính sách sử dụng dịch vụ.
- **Bảo toàn nguồn vốn tạm giữ:** Khoản tiền Escrow được cô lập trên sổ kế toán của hệ thống, không được ghi nhận vào doanh thu của nền tảng cho đến khi dịch vụ hoàn thành hoặc xử lý xong chính sách hủy.
- Hệ thống xuất biên lai thu tiền/hóa đơn dịch vụ cho User theo đúng quy định tài chính.

#### 9. Điểm chưa thống nhất
- Phí nền tảng (Platform fee) được trừ trực tiếp từ tiền của Chuyên gia (ví dụ: thu 20% phí hoa hồng trên giá trị ca tư vấn) hay cộng thêm vào giá thanh toán của User?
- Xuất hóa đơn GTGT: Nền tảng xuất hóa đơn cho toàn bộ số tiền thu của User, hay chỉ xuất hóa đơn cho phần phí dịch vụ nền tảng (Platform Fee) còn Chuyên gia phải xuất chứng từ phần thù lao?

---

### ĐẶC TẢ 5: THỰC HIỆN TƯ VẤN 1-1 (1-ON-1 CONSULTATION EXECUTION)

#### 1. Tên chức năng
Tiến hành phiên tư vấn trực tuyến (Live Consultation Session).

#### 2. Mục đích
Cung cấp không gian làm việc trực tuyến an toàn (Video call, chia sẻ màn hình, tài liệu) để Chuyên gia và Người dùng trao đổi nghiệp vụ trực tiếp tại khung giờ đã hẹn, đồng thời ghi nhận bằng chứng về sự hiện diện của hai bên.

#### 3. Actor
- Người dùng (User)
- Chuyên gia (Expert)
- Hệ thống (System)

#### 4. Điều kiện trước
- Booking ở trạng thái "Đã xác nhận" (Confirmed).
- Đến thời gian hẹn (hoặc trước giờ hẹn 10 phút).

#### 5. Luồng chính
1. Trước giờ hẹn 30 phút và 10 phút, Hệ thống gửi tin nhắn/thông báo nhắc nhở kèm đường link phòng tư vấn cho cả User và Chuyên gia.
2. User và Chuyên gia nhấn nút "Vào phòng tư vấn" trên giao diện hệ thống.
3. Hệ thống kiểm tra quyền truy cập, xác thực danh tính và kết nối hai bên vào phòng họp trực tuyến bảo mật tích hợp sẵn.
4. Hệ thống ghi nhận mốc thời gian: **"Bắt đầu phiên tư vấn" (Session Started)** ngay khi cả 2 bên cùng có mặt.
5. Hai bên tiến hành làm việc:
   - Trao đổi thoại và video trực tiếp.
   - Chuyên gia hoặc User chia sẻ màn hình để xem xét số liệu kế toán, chứng từ, tờ khai thuế.
   - Ghi chú các điểm quan trọng trong khung ghi chú chung (Shared Notes).
6. Hệ thống hiển thị đồng hồ đếm ngược thời gian phiên làm việc.
7. Trước khi hết giờ 5 phút, Hệ thống phát cảnh báo nhắc nhở hai bên tóm tắt kết luận buổi tư vấn.
8. Khi hết giờ quy định, hai bên chào kết thúc và nhấn "Rời phòng".
9. Hệ thống tự động đóng phòng họp, cập nhật trạng thái Booking sang **"Đã hoàn thành phiên" (Session Completed)**, ghi nhận tổng thời lượng làm việc thực tế.
10. Hệ thống kích hoạt cơ chế đếm ngược thời gian chờ xử lý tranh chấp (Cool-down) trước khi giải ngân.

#### 6. Luồng thay thế / Ngoại lệ
- **Chuyên gia vắng mặt (Expert No-Show):** Quá 15 phút kể từ giờ hẹn mà Chuyên gia không vào phòng -> Hệ thống tự động ghi nhận Chuyên gia vắng mặt không phép, hủy phiên, kích hoạt luồng hoàn tiền 100% cho User và phạt điểm uy tín Chuyên gia.
- **Người dùng vắng mặt (User No-Show):** Chuyên gia đã vào phòng chờ nhưng User không xuất hiện sau 15 phút -> Chuyên gia ấn xác nhận "Khách hàng không tham dự". Hệ thống kiểm tra log phòng họp, đóng ca, tiền vẫn được thanh toán cho Chuyên gia theo chính sách bảo vệ thời gian làm việc.
- **Sự cố mất kết nối mạng:** Một bên bị rớt mạng giữa chừng -> Hệ thống giữ phòng mở thêm 10 phút để người đó kết nối lại. Nếu không thể tiếp tục do sự cố kỹ thuật của hệ thống, cho phép hai bên thỏa thuận dời lịch hoặc hoàn lại tiền.
- **Hai bên muốn gia hạn thêm giờ:** Nếu phiên tư vấn chưa giải quyết xong bài toán và Chuyên gia không vướng ca tiếp theo -> Cho phép kích hoạt tính năng "Gia hạn thêm 30 phút" (Yêu cầu thanh toán bổ sung ngay lập tức).

#### 7. Kết quả sau khi thực hiện
- Phiên tư vấn được hoàn thành.
- Nhật ký phiên họp (Metadata: thời gian vào/ra của các bên, thời lượng thực tế, tình trạng tham dự) được lưu trữ làm căn cứ đối soát.

#### 8. Business Rules
- Phòng tư vấn chỉ mở trước giờ hẹn tối đa 10 phút và tự động đóng sau khi hết giờ hẹn chuẩn tối đa 10 phút (nếu không có lệnh gia hạn).
- **Tính bảo mật thông tin (Confidentiality):** Dữ liệu tài chính, sổ sách trao đổi trong phòng tư vấn là tài sản riêng của User; Chuyên gia có nghĩa vụ tuân thủ cam kết bảo mật (NDA) đã ký khi gia nhập nền tảng.
- Nghiêm cấm mọi hành vi gạ gẫm chuyển đổi giao dịch ra ngoài hệ thống trong suốt thời gian diễn ra cuộc gọi.

#### 9. Điểm chưa thống nhất
- **Ghi âm/Ghi hình (Session Recording):** Có nên tự động ghi lại toàn bộ video cuộc gọi để làm bằng chứng giải quyết tranh chấp sau này không, hay điều này vi phạm quyền riêng tư và bảo mật dữ liệu tài chính của doanh nghiệp?
- Cho phép sử dụng nền tảng video call ngoài (như Zoom, Google Meet) do hệ thống tự sinh link, hay bắt buộc phải chạy trên WebRTC nội bộ của ứng dụng?

---

### ĐẶC TẢ 6: ĐÁNH GIÁ & FEEDBACK (RATING & FEEDBACK)

#### 1. Tên chức năng
Đánh giá chất lượng và gửi phản hồi sau phiên tư vấn.

#### 2. Mục đích
Ghi nhận mức độ hài lòng của khách hàng đối với năng lực chuyên môn và thái độ của chuyên gia; tạo nguồn dữ liệu minh bạch giúp cộng đồng lựa chọn chuyên gia tốt hơn.

#### 3. Actor
- Người dùng (User)
- Chuyên gia (Expert)
- Hệ thống (System)
- Quản trị viên (Admin)

#### 4. Điều kiện trước
- Booking đã ở trạng thái "Đã hoàn thành phiên" (Session Completed).
- Chưa quá thời hạn cho phép đánh giá (ví dụ: trong vòng 7 ngày kể từ khi kết thúc ca).

#### 5. Luồng chính
1. Sau khi buổi tư vấn kết thúc, Hệ thống tự động gửi thông báo và hiển thị pop-up/màn hình mời User đánh giá.
2. User truy cập vào biểu mẫu đánh giá, tiến hành:
   - Chấm điểm số sao tổng quan (từ 1 đến 5 sao).
   - Đánh giá theo các tiêu chí chi tiết (Độ am hiểu chuyên môn, Mức độ đúng giờ, Thái độ giao tiếp, Khả năng giải quyết bài toán thuế/kế toán).
   - Viết nhận xét chi tiết dạng văn bản (tối thiểu 10 ký tự).
   - (Tùy chọn) Chọn các thẻ nhận xét nhanh (ví dụ: "Nhiệt tình", "Giải thích dễ hiểu", "Kiến thức chuyên sâu", "Tiết kiệm chi phí thuế hợp pháp").
3. User nhấn "Gửi đánh giá".
4. Hệ thống tiếp nhận đánh giá:
   - Lưu trữ phản hồi vào hồ sơ của Chuyên gia.
   - Tự động tính toán lại điểm đánh giá trung bình lũy kế (Average Rating) của Chuyên gia.
   - Hiển thị nhận xét công khai trên trang hồ sơ Chuyên gia.
5. Chuyên gia nhận được thông báo về đánh giá mới và có quyền gửi 1 nội dung "Phản hồi lại nhận xét" mang tính lịch sự/cảm ơn.

#### 6. Luồng thay thế / Ngoại lệ
- **Đánh giá tiêu cực bất thường (1 - 2 sao kèm nội dung khiếu nại):** Hệ thống lập tức đánh cờ cảnh báo (Flag for Review), tạm hoãn việc giải ngân tự động và gửi thông báo cho đội ngũ Chăm sóc khách hàng (CSKH) để liên hệ hỗ trợ làm rõ nguyên nhân.
- **Nội dung nhận xét vi phạm tiêu chuẩn cộng đồng:** Đánh giá chứa ngôn từ lăng mạ, vu khống, để lộ số điện thoại cá nhân -> Hệ thống lọc từ cấm tự động hoặc Admin kiểm duyệt ẩn nội dung văn bản (vẫn giữ nguyên số sao đánh giá hoặc xử lý vi phạm).
- **User không đánh giá:** Sau 7 ngày nếu User không gửi đánh giá, Hệ thống tự động đóng quyền đánh giá ca này và coi như người dùng không có ý kiến phản đối.

#### 7. Kết quả sau khi thực hiện
- Điểm uy tín của Chuyên gia được cập nhật.
- Phản hồi thực tế được xuất bản làm tài liệu tham khảo cho người dùng khác.

#### 8. Business Rules
- **Chỉ khách hàng thực tế mới được đánh giá:** Nghiêm cấm hoàn toàn hành vi tạo đánh giá ảo; chỉ tài khoản đã đặt lịch, thanh toán và hoàn thành phiên mới có quyền đánh giá duy nhất 1 lần cho mỗi mã Booking.
- Chuyên gia không có quyền xóa hoặc tự ý chỉnh sửa đánh giá của khách hàng; chỉ có Admin mới có quyền gỡ bỏ đánh giá sau khi chứng minh được đánh giá đó có hành vi phá hoại hoặc cạnh tranh không lành mạnh từ đối thủ.
- Chuyên gia chỉ được phản hồi (Reply) công khai đúng 1 lần cho mỗi review của khách hàng.

#### 9. Điểm chưa thống nhất
- Có áp dụng cơ chế đánh giá 2 chiều (Chuyên gia đánh giá ngược lại độ hợp tác và lịch sự của User) để bảo vệ chuyên gia trước các khách hàng quấy rối hay không?
- Đánh giá ẩn danh: Có cho phép User đăng nhận xét dưới dạng ẩn danh (chỉ hiện "Người dùng ẩn danh") hay bắt buộc phải hiện tên thật?

---

### ĐẶC TẢ 7: GIẢI NGÂN & XỬ LÝ TRANH CHẤP (DISBURSEMENT & DISPUTE HANDLING)

#### 1. Tên chức năng
Giải ngân thù lao chuyên gia, xử lý khiếu nại và hoàn tiền (Disbursement, Cancellation & Dispute Resolution).

#### 2. Mục đích
Thực thi thanh toán số tiền đang tạm giữ (Escrow) cho chuyên gia khi dịch vụ hoàn tất, hoặc can thiệp bồi hoàn, phạt vi phạm khi phát sinh tranh chấp hoặc hủy lịch nhằm đảm bảo quyền lợi công bằng cho các bên.

#### 3. Actor
- Chuyên gia (Expert)
- Người dùng (User)
- Quản trị viên / Đội ngũ giải quyết khiếu nại (Admin / Support)
- Hệ thống (System)

#### 4. Điều kiện trước
- Booking ở trạng thái hoàn thành phiên tư vấn (chờ giải ngân), hoặc có yêu cầu hủy lịch/khiếu nại được gửi lên trước/trong/sau phiên tư vấn.

#### 5. Luồng chính (Giải ngân tự động khi ca thành công)
1. Sau khi phiên tư vấn kết thúc, Hệ thống chuyển Booking sang trạng thái **"Tạm giữ - Chờ khiếu nại" (Holding / Cool-down)** trong vòng 24 giờ.
2. Trong 24 giờ này, nếu User chủ động nhấn "Xác nhận hài lòng" hoặc không có bất kỳ khiếu nại nào được gửi lên:
   - Hệ thống tiến hành quyết toán tài chính cho mã Booking này.
   - Tính toán công thức: `Số tiền Chuyên gia thực nhận = Tổng giá trị ca - Phí hoa hồng nền tảng (Platform fee) - Thuế TNCN (nếu khấu trừ tại nguồn)`.
   - Hệ thống chuyển số tiền thực nhận vào **Ví thu nhập (E-wallet balance)** của Chuyên gia trên nền tảng.
   - Trạng thái Booking chuyển thành **"Đã quyết toán thành công" (Closed / Settled)**.
3. Chuyên gia có thể gửi lệnh rút tiền từ Ví thu nhập về tài khoản ngân hàng cá nhân theo chu kỳ rút tiền của hệ thống.

#### 6. Luồng thay thế / Ngoại lệ

##### A. Luồng Hủy lịch trước giờ hẹn (Cancellation Flow):
- **User chủ động hủy lịch:**
  - Hủy trước giờ hẹn > 24 tiếng: Hệ thống hoàn lại 100% tiền tạm giữ cho User; mở lại slot cho Chuyên gia.
  - Hủy trước giờ hẹn từ 4 đến 24 tiếng: Hoàn lại 50% cho User; 50% còn lại chuyển đền bù thời gian cho Chuyên gia (sau khi trừ phí hệ thống).
  - Hủy trước giờ hẹn < 4 tiếng hoặc vắng mặt (No-Show): Không hoàn tiền; toàn bộ tiền được chuyển cho Chuyên gia để bảo vệ quyền lợi lịch làm việc.
- **Chuyên gia chủ động hủy lịch:**
  - Hoàn tiền 100% ngay lập tức cho User bất kể thời điểm hủy.
  - Chuyên gia bị ghi nhận lỗi vi phạm, bị trừ điểm uy tín hoặc bị phạt tiền vào số dư khả dụng nếu hủy sát giờ (< 12 tiếng).

##### B. Luồng Xử lý tranh chấp chuyên môn / Khiếu nại dịch vụ (Dispute Flow):
1. Trong vòng 24 giờ kể từ khi hết ca, User nhấn nút "Gửi khiếu nại" (Lý do: Chuyên gia tư vấn sai quy định pháp luật rõ ràng, thái độ thiếu chuẩn mực, Chuyên gia tự ý kết thúc sớm, sự cố đường truyền mạng nghiêm trọng).
2. Hệ thống lập tức **đóng băng khoản tiền tạm giữ (Freeze Escrow)**, chuyển trạng thái Booking sang **"Đang tranh chấp" (Under Dispute)**.
3. Chuyên gia nhận thông báo khiếu nại và có 24 giờ để gửi phản hồi/bằng chứng phản biện.
4. Đội ngũ Admin/Support tiếp nhận hồ sơ, kiểm tra nhật ký phiên họp (log thời gian gọi, ghi chú chung, nội dung trao đổi, bằng chứng 2 bên cung cấp).
5. Admin đưa ra phán quyết xử lý dựa trên chính sách:
   - *Khiếu nại hợp lệ hoàn toàn (Lỗi từ Chuyên gia):* Hoàn tiền 100% cho User; không giải ngân cho Chuyên gia; áp dụng chế tài vi phạm.
   - *Khiếu nại không có căn cứ (Chuyên gia đã làm đúng cam kết):* Bác bỏ khiếu nại; tiến hành giải ngân đầy đủ tiền cho Chuyên gia.
   - *Lỗi một phần / Sự cố kỹ thuật khách quan:* Phân chia tỷ lệ (ví dụ: hoàn 50% cho User, thanh toán 50% thù lao cho Chuyên gia hoặc cấp voucher bù 1 buổi tư vấn khác).
6. Hệ thống thực thi giao dịch tài chính theo đúng quyết định cuối cùng của Admin và đóng vụ việc.

#### 7. Kết quả sau khi thực hiện
- Tiền tạm giữ được phân bổ minh bạch: Hoàn trả cho User hoặc chuyển thành thu nhập thực của Chuyên gia.
- Không có hiện tượng thất thoát dòng tiền; tranh chấp được giải quyết có biên bản lưu vết.

#### 8. Business Rules
- Tiền tạm giữ tuyệt đối không được giải ngân trước khi hết thời hạn khiếu nại (24 giờ) trừ khi User chủ động ấn xác nhận hoàn tất sớm.
- Quyết định giải quyết tranh chấp của Admin là phán quyết cuối cùng trên nền tảng dựa trên các điều khoản dịch vụ mà hai bên đã đồng thuận khi tham gia.
- Chuyên gia chỉ được rút tiền từ ví nền tảng về tài khoản ngân hàng khi tài khoản đã hoàn tất định danh công dân (eKYC) và cung cấp Mã số thuế cá nhân.

#### 9. Điểm chưa thống nhất
- Thời gian đóng băng chờ khiếu nại (Cool-down period) nên là 24 giờ hay 48 giờ để đủ thời gian cho User rà soát lại lời khuyên tư vấn?
- Trách nhiệm pháp lý và bảo hiểm rủi ro: Nếu Chuyên gia tư vấn sai dẫn đến việc User bị cơ quan thuế xử phạt hành chính, nền tảng chịu trách nhiệm trung gian đến đâu? Có áp dụng quỹ đền bù rủi ro không?

---

### ĐẶC TẢ 8: QUẢN LÝ TƯ VẤN CỦA CHUYÊN GIA (EXPERT CONSULTATION MANAGEMENT)

#### 1. Tên chức năng
Bàn làm việc và quản trị hoạt động tư vấn của chuyên gia (Expert Workspace / Dashboard).

#### 2. Mục đích
Cung cấp cho chuyên gia công cụ toàn diện để chủ động quản lý lịch rảnh, theo dõi danh sách lịch hẹn sắp tới, xem trước hồ sơ tài liệu của khách hàng, theo dõi lịch sử thu nhập và gửi yêu cầu rút tiền.

#### 3. Actor
- Chuyên gia (Expert)
- Hệ thống (System)

#### 4. Điều kiện trước
- Chuyên gia đã được phê duyệt hồ sơ và có quyền truy cập vào giao diện Chuyên gia (Expert Portal).

#### 5. Luồng chính
1. Chuyên gia đăng nhập và truy cập vào mục "Quản lý tư vấn" (Expert Dashboard).
2. **Quản lý lịch khả dụng (Calendar / Slot Management):**
   - Chuyên gia thiết lập khung giờ rảnh cố định trong tuần (ví dụ: Thứ 3, Thứ 5 từ 19:00 - 21:00; Thứ 7 từ 09:00 - 12:00).
   - Chuyên gia có thể mở thêm các slot linh hoạt hoặc bấm "Khóa/Tắt slot" vào các ngày nghỉ đột xuất.
   - Hệ thống tự động đồng bộ trạng thái các slot này ra danh bạ công khai cho người dùng nhìn thấy.
3. **Quản lý lịch hẹn (Booking Management):**
   - Chuyên gia xem danh sách các buổi hẹn theo các bộ lọc: Sắp diễn ra, Đã hoàn thành, Đã hủy, Đang khiếu nại.
   - Đối với ca "Sắp diễn ra": Chuyên gia nhấn vào để xem chi tiết câu hỏi của khách hàng, tải về các tài liệu/báo cáo thuế mà khách hàng đã đính kèm trước để nghiên cứu trước giải pháp.
4. **Truy cập phòng tư vấn:** Đến giờ hẹn, Chuyên gia nhấn "Tham gia buổi tư vấn" trực tiếp từ danh sách lịch hẹn để chuyển vào phòng họp trực tuyến.
5. **Theo dõi tài chính & Thu nhập (Financial Management):**
   - Chuyên gia xem báo cáo doanh thu: Tổng thu nhập tích lũy, Số tiền đang tạm giữ (Escrow chưa giải ngân), Số dư khả dụng có thể rút (Available Balance).
   - Xem chi tiết bảng phân tích từng ca (Doanh thu gộp, Phí hoa hồng sàn bị trừ, Thuế TNCN khấu trừ, Số tiền thực nhận).
6. **Yêu cầu rút tiền:**
   - Chuyên gia nhập số tiền muốn rút về tài khoản ngân hàng chính chủ đã đăng ký.
   - Hệ thống kiểm tra số dư khả dụng, ghi nhận lệnh rút tiền và xử lý chuyển khoản theo kỳ thanh toán.

#### 6. Luồng thay thế / Ngoại lệ
- **Chuyên gia muốn hủy/đóng một slot đã có người đặt trước:** Hệ thống cảnh báo việc hủy lịch đã xác nhận sẽ ảnh hưởng xấu đến uy tín và có thể bị phạt; yêu cầu Chuyên gia nhập lý do chính đáng và kích hoạt quy trình bồi hoàn/thông báo khẩn cấp cho User.
- **Yêu cầu rút tiền vượt quá số dư khả dụng:** Hệ thống báo lỗi và từ chối tạo lệnh rút tiền.
- **Thông tin ngân hàng rút tiền không trùng khớp với hồ sơ danh tính:** Hệ thống từ chối chuyển tiền nhằm chống rửa tiền và gian lận tài chính.

#### 7. Kết quả sau khi thực hiện
- Lịch làm việc của Chuyên gia luôn được cập nhật chính xác, tránh xung đột thời gian cá nhân.
- Chuyên gia chủ động nắm bắt bài toán của khách hàng để chuẩn bị buổi tư vấn có chất lượng cao nhất.
- Doanh thu và dòng tiền của Chuyên gia được theo dõi minh bạch.

#### 8. Business Rules
- Chuyên gia không được mở quá số lượng ca tối đa quy định trong một ngày (ví dụ tối đa 6 ca/ngày) để tránh kiệt sức và giảm chất lượng tư vấn chuyên môn.
- Mọi tài liệu của khách hàng mà Chuyên gia tải xuống chỉ được lưu hành phục vụ cho buổi tư vấn đó; nghiêm cấm việc chia sẻ cho bên thứ ba hoặc sử dụng vào mục đích thương mại khác.
- Lệnh rút tiền chỉ được tạo khi số dư khả dụng đạt mức tối thiểu theo quy định (ví dụ tối thiểu 500.000 VNĐ/lần rút).

#### 9. Điểm chưa thống nhất
- Quy định số lần tối đa Chuyên gia được phép dời/hủy lịch đã đặt trong một tháng mà không bị áp dụng hình thức kỷ luật (khóa tài khoản tạm thời).
- Chu kỳ duyệt lệnh rút tiền: Tiền về tài khoản ngân hàng của Chuyên gia theo thời gian thực (24/7 tức thì) hay cố định vào một ngày cụ thể trong tuần/tháng (ví dụ ngày 15 và 30 hàng tháng) để kế toán nền tảng làm thủ tục đối soát thuế?

---

## 3. BẢNG TỔNG HỢP VÀ ÁNH XẠ TRẠNG THÁI (MAPPING MATRIX)

| STT | Tên đặc tả nghiệp vụ | Trọng tâm giải quyết | Trạng thái luồng tiền / Dữ liệu |
| :--- | :--- | :--- | :--- |
| **1** | Đăng ký & Thẩm định chuyên gia | Tiếp nhận hồ sơ, thẩm định văn bằng/chứng chỉ, cấp quyền Chuyên gia | Hồ sơ: Draft -> PendingReview -> NeedSupplement / Rejected / Approved |
| **2** | Tìm kiếm & lựa chọn chuyên gia | Khám phá, so sánh, minh bạch thông tin | Hiển thị hồ sơ công khai & Lọc theo tiêu chí |
| **3** | Đặt lịch tư vấn | Điều phối thời gian, khớp nhu cầu | Tạm khóa Slot (Hold 10 phút) -> Chờ thanh toán |
| **4** | Thanh toán & tạm giữ tiền | Bảo đảm giao dịch an toàn | Tiền: **Tạm giữ (Held in Escrow)** -> Xác nhận Booking |
| **5** | Thực hiện tư vấn 1-1 | Không gian làm việc, giám sát hiện diện | Buổi hẹn: Đang diễn ra -> Hoàn thành phiên |
| **6** | Đánh giá & feedback | Kiểm soát chất lượng, xếp hạng uy tín | Tạo Review -> Cập nhật điểm Rating lũy kế |
| **7** | Giải ngân & xử lý tranh chấp | Công bằng tài chính, bảo vệ người dùng | Tiền: Escrow -> **Ví Chuyên gia / Hoàn trả User** |
| **8** | Quản lý tư vấn của chuyên gia | Nâng cao hiệu suất làm việc chuyên gia | Quản trị Slot rảnh, xem tài liệu & Ví thu nhập cá nhân |
