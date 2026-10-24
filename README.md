# GOT — Game Of Thien

Bản đóng gói game từ workspace ngày 2026-10-24: giao diện v8.9, 10 chủ đề trong danh mục, 1.043 mục, 18 trò chơi và 30 cảnh tìm đồ vật. Thư viện ảnh gốc dùng Git LFS; bỏ archive triển khai cũ và cache.

**Phạm vi hiện tại:** game và cấu hình Docker. Mã nguồn đầy đủ của portal `thienha.io.vn` chưa có trong bản này; chưa thể đóng gói hay rà soát toàn bộ portal. Kho `Thien-Ha` phục vụ `th.io.vn` là ứng dụng khác, không được ghép vào đây. Chưa đối chiếu với phiên bản đang chạy trên Sika.

## Chạy bằng Docker

Cần Docker Engine + Compose plugin trên Linux, hoặc Docker Desktop với Linux containers trên Windows/macOS. Image nhắm Linux AMD64 và ARM64; chưa hỗ trợ ARM 32 bit.

```sh
git lfs install
git clone https://github.com/TuanPham0411/GOT.git
cd GOT
git lfs pull
docker compose up -d --build --wait
```

Mở http://127.0.0.1:5080. Để máy khác trong LAN truy cập, đặt `GOT_BIND=0.0.0.0` trong `.env` (chép từ `.env.example`) rồi khởi động lại Compose. Mặc định chỉ mở localhost để dùng với reverse proxy/tunnel.

Container chạy Gunicorn bằng user riêng, filesystem chỉ đọc, cache ảnh trong volume, healthcheck và có `espeak-ng` cho tiếng Việt/Anh. Cổng 5080 cho phép kiểm thử song song dịch vụ cũ ở cổng 5000.

Game giữ cơ chế phiên hiện tại qua `https://thienha.io.vn`. Khi chưa có portal, giao diện dùng preview hiện có. Cần kiểm thử tích hợp tài khoản/phiên trước khi chuyển production.

## Kiểm thử

```sh
pip install -r game/requirements.txt
python -m unittest discover -s game/tests -v
python game/tools/audit_v88_complete.py
python game/tools/audit_v89_ui.py
node --check game/static/js/app-v89.js
```

Nên chạy trong virtualenv. Gunicorn dùng trong Linux container; kiểm thử Flask/Pillow chạy được trên Windows. Audit v88 kiểm tra dữ liệu, checksum, ảnh, phân loại và 30 cảnh; audit v89 kiểm tra cấu trúc UI. Chưa kiểm thử tương tác toàn bộ 18 trò chơi.

GitHub Actions kiểm thử mã/dữ liệu, build và smoke test container, sau đó xuất bản image AMD64/ARM64 lên GHCR. Xem [hướng dẫn Sika](docs/RPI-SIKA.md) và [báo cáo rà soát](docs/REVIEW.md).
