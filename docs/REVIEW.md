> Tài liệu lịch sử của bản game riêng. Với toàn bộ portal và lần chuyển Docker mới, xem [PLATFORM-SIKA.md](PLATFORM-SIKA.md).

# Rà soát 2026-10-24

## Đã sửa

- Tôn trọng `gzip;q=0`, thêm `Vary: Accept-Encoding` cho cả phản hồi gốc và nén, ETag theo nội dung nén.
- Giữ cache TTS thay vì bị middleware ghi đè thành `no-cache`.
- Bỏ static cache một năm `immutable` vì file v89 có thể thay đổi mà không đổi URL. Lỗi HTTP dùng `no-store`.
- File tạm thumbnail riêng cho từng worker, atomic replace và dọn khi lỗi; trả 415 cho ảnh không xử lý được.
- Đặt `--` trước văn bản espeak-ng để chuỗi bắt đầu bằng dấu gạch không trở thành tùy chọn.
- Thêm readiness kiểm tra ba file catalog bắt buộc.
- Docker dùng user riêng, filesystem chỉ đọc, bỏ capabilities, volume cache, healthcheck và giới hạn log.

## Bằng chứng cục bộ

- Sáu bài kiểm thử HTTP đạt: readiness, gzip, traversal, TTS arguments/cache, catalog/template, Range.
- Audit v88 đạt: dữ liệu song ngữ, checksum, ảnh, phân loại và 30 cảnh khác nhau.
- Audit cấu trúc UI v89 đạt; JavaScript v89 qua kiểm tra cú pháp Node.

## Chưa xác minh

- Chưa build/chạy Docker cục bộ vì máy chưa cài Docker. Workflow sẽ kiểm thử trên Linux thật.
- Chưa có mã nguồn portal đầy đủ để rà soát tài khoản, thanh toán, phiên và database.
- Chưa truy cập được RPI Sika; chưa thay dịch vụ hoặc Cloudflare/nginx production.
- Chưa kiểm thử tương tác trình duyệt, cảm ứng và toàn bộ 18 trò chơi. Không coi đây là đã sửa mọi lỗi hoặc nâng cấp mọi chức năng.
