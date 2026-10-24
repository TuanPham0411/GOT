# Thiên Hạ Platform

Repository cho `thienha.io.vn`, portal tài khoản/dự án, Game Of Thiên và dịch vụ web XiaoZhi Copper Robot. Mã portal được nhập từ SIKA1; game giữ lịch sử và thư viện Git LFS của repository GOT. Ứng dụng `th.io.vn` trong repository `Thien-Ha` là hệ thống riêng.

| Thành phần | Mã nguồn | Runtime |
| --- | --- | --- |
| Portal: tài khoản Google, catalog, quản trị, tải xuống, đơn hàng, giấy phép, phiên chơi | `portal/` | Flask, Gunicorn, SQLite |
| Game Of Thiên: 18 trò, 10 chủ đề, 30 cảnh tìm đồ | `game/` | Flask, Pillow, espeak-ng |
| XiaoZhi: quản lý robot, giấy phép, công cụ Internet, GPT, YouTube, luồng nhạc | `portal/xiaozhi_tools.py` | Flask blueprint, ffmpeg |
| XiaoZhi ESP32-S3 | `portal/static/xiaozhi/` | Firmware đã biên dịch và manifest web installer |

**Giới hạn nguồn firmware:** SIKA chỉ có binary XiaoZhi, chưa tìm thấy source/build toolchain ESP32. Repository này build lại đầy đủ hai dịch vụ web, không tuyên bố build lại được firmware. Các file phát hành có kiểm soát và dữ liệu tài khoản nằm trong state riêng tư, không ở Git hay image.

## Chạy thử toàn bộ nền tảng

Cần Docker Engine + Compose v2, Git LFS; Linux AMD64 hoặc ARM64.

```sh
git clone https://github.com/TuanPham0411/GOT.git
cd GOT
git lfs install --local
git lfs pull
cp portal/.env.example .env.portal
# Điền FLASK_SECRET_KEY cố định, ngẫu nhiên và OAuth của bạn vào .env.portal.
mkdir -p state/portal
sudo chown 10001:10001 state/portal
docker compose -f compose.platform.yaml build
docker compose -f compose.platform.yaml run --rm --no-deps portal python seed.py
docker compose -f compose.platform.yaml up -d --no-build --wait --wait-timeout 180
python3 deploy/smoke.py
```

Portal ở `127.0.0.1:15050`, game ở `127.0.0.1:15080` (preview game: `/?preview=1`). OAuth và cookie Secure cần HTTPS/reverse proxy để dùng tài khoản; smoke test công khai không chứng minh đăng nhập Google thật. Cấu hình production SIKA giữ nguyên hostname và callback đang dùng. Các API ngoài cần khóa và kết nối tương ứng; không có khóa thì tính năng đó chưa hoạt động.

`seed.py` chỉ thêm nội dung công khai của hai project nếu slug chưa có; không ghi đè catalog đã chỉnh sửa, không tạo tài khoản hay dữ liệu thanh toán. Firmware ZIP tải xuống và asset có kiểm soát cần phục hồi từ private backup vào `/data/files`. Không thay private database production bằng database seed.

Đọc [triển khai và rollback SIKA](docs/PLATFORM-SIKA.md), [game](docs/GAME.md), [phạm vi XiaoZhi](projects/xiaozhi/README.md).

Game Of Thiên mở cả 18 trò trong một phiên. Thời lượng chung: 10, 20, 30, 40, 50 hoặc 60 phút, tính từ lúc mở phiên; đổi trò hoặc tải lại trang không đặt lại đồng hồ.

## Kiểm thử và image

```sh
python3 -m venv .venv
.venv/bin/pip install -r game/requirements.txt -r portal/requirements.txt
.venv/bin/python -m unittest discover -s game/tests -v
.venv/bin/python -m unittest discover -s portal/tests -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python game/tools/audit_v88_complete.py
.venv/bin/python game/tools/audit_v89_ui.py
node --check game/static/js/app-v89.js
node --test game/tests-js/session-clock.test.cjs
```

GitHub Actions kiểm thử cả hai dịch vụ và Docker smoke test trước khi build/publish image AMD64/ARM64 tới `ghcr.io/tuanpham0411/got/{portal,game}:COMMIT_SHA`. Dùng SHA cố định khi triển khai; không phụ thuộc `latest`. Việc source công khai không tự chứng minh GHCR package đã công khai: kiểm tra quyền package hoặc dùng image build tại máy đích.

Dockerfile hỗ trợ BuildKit secret `proxy_ca` cho môi trường có HTTPS proxy; kiểm tra TLS luôn bật. Không copy CA phiên hay thông tin xác thực vào image. Các phiên bản trực tiếp được pin trong requirements; hiện chưa có lockfile transitive.
