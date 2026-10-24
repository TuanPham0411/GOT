# Thiên Hạ Platform trên SIKA

## Kiến trúc

SIKA1: Debian 13 ARM64, khoảng 905 MiB RAM. Cloudflare Tunnel hiện chuyển `thienha.io.vn` và `www.thienha.io.vn` tới `127.0.0.1:5050`; `gameofthien.thienha.io.vn` tới `127.0.0.1:5000`. Không thay đổi tuyến SSH.

Trước khi chuyển Docker, portal nằm tại `/home/sika1/thienha-home` (unit `thienha-home`), game tại `/home/sika1/Game_Of_Thien/Game_Of_Thien` (unit `game-of-thien`). Giữ nguyên các thư mục này để rollback. File secret `/etc/thienha-home.env` được dùng lại, không copy vào Git/image.

## Chuẩn bị bản chạy

1. Kiểm tra OS/kiến trúc, dung lượng, RAM, cổng và trạng thái hai dịch vụ cũ.
2. Trên Debian 13 ARM64, Docker/Compose được cài từ APT có xác thực: `sudo apt-get update && sudo apt-get install -y docker.io docker-compose`. Không đổi iptables hay mở cổng public để xử lý build.
3. Checkout đúng commit, tải đầy đủ Git LFS và chạy các kiểm thử trong README. Có thể tái sử dụng asset trên SIKA khi SHA-256 khớp chính xác với object LFS. Không tái sử dụng asset chỉ vì trùng tên.
4. Build từng image trên Pi để giới hạn tải/RAM, hoặc pull image ARM64 đã qua CI. Không chạy hai build song song trên SIKA. Image không chứa dữ liệu production hay secrets.
5. Tạo snapshot riêng tư bằng SQLite backup API, không chỉ copy file `users.db` đang chạy (có WAL). Ví dụ:

```sh
sudo python3 deploy/snapshot_data.py /home/sika1/thienha-home/data /opt/thienha-platform/state/stage --legacy-files /home/sika1/thienha-home/files
sudo chown -R 10001:10001 /opt/thienha-platform/state/stage
```

Destination phải chưa tồn tại. Script giữ private state, bỏ DB backup cũ và kết hợp ZIP legacy đang nằm ở `files/` ngoài data. Không đưa snapshot lên GitHub. Cần kiểm tra mọi liên kết file trước khi di chuyển nếu bố cục nguồn thay đổi.

6. Dùng Compose project `thienha-stage`, cổng `15050`/`15080`, data staging; env file vẫn chỉ tham chiếu `/etc/thienha-home.env`. Các giá trị không bí mật trong env file Compose:

```dotenv
PORTAL_ENV_FILE=/etc/thienha-home.env
PORTAL_DATA_DIR=/opt/thienha-platform/state/stage
PORTAL_PORT=15050
GOT_PORT=15080
PORTAL_IMAGE=thienha-portal:COMMIT_SHA
GOT_IMAGE=got-game:COMMIT_SHA
```

```sh
sudo docker compose --env-file /opt/thienha-platform/config/stage.env -p thienha-stage -f compose.platform.yaml up -d --no-build --wait --wait-timeout 180
python3 deploy/smoke.py
```

Chạy kiểm thử phiên chơi/xác thực trên DB staging, không tạo tài khoản thử trong DB production. Kiểm tra `ffmpeg`, WAV Việt/Anh, asset và firmware. OAuth Google thật, robot vật lý và các API có phí cần kiểm thử riêng với tài khoản/thiết bị hợp lệ.

## Chuyển dịch vụ

Script `deploy/cutover-sika.sh` thực hiện: kiểm tra staging, lưu unit/secret/tunnel riêng tư, dừng hai dịch vụ cũ, chụp DB mới sau khi dừng, chuyển port về 5050/5000, khởi động Compose production và kiểm tra. Nếu thất bại, script dừng container production và bật lại dịch vụ cũ. Không thay Cloudflare origin.

Các bản triển khai và config nằm dưới `/opt/thienha-platform`. Chỉ disable hai unit cũ sau khi kiểm tra thành công; container có restart policy và Docker service bật cùng máy. Không xóa code/data cũ hoặc volume cache.

## Rollback sau khi bản mới đã nhận ghi

Không bật ngay DB cũ vì có thể mất các thay đổi tài khoản/đơn hàng phát sinh sau cutover. Dừng portal container, chụp snapshot private state mới, kiểm tra tương thích schema, rồi phục hồi `users.db` nhất quán và release files vào vị trí cũ trước khi khởi động unit cũ. Hai phiên bản dùng cùng schema hiện có; vẫn phải kiểm tra integrity và giữ backup trước khi copy.

Rollback ngay trong cutover thất bại được script xử lý tự động. Rollback muộn sau khi đã phục vụ traffic cần xử lý state như trên.

## Giữ dữ liệu firmware và cập nhật mã nhỏ

Trong state private, `/data/files` chứa ZIP tải xuống của portal; `/data/firmware` chứa BIN/ZIP cho endpoint tải firmware có kiểm tra giấy phép. Khi di chuyển từ SIKA cũ, chép firmware công khai từ `portal/static/xiaozhi/` và ZIP được phép phát hành vào `data/firmware` (không ghi đè tệp đã có), rồi mới snapshot. Hai thư mục này không nằm trong Git/image và phải được giữ trong private backup.

Khi chỉ sửa Python/template/JS/CSS, có thể dùng `deploy/Dockerfile.{portal,game}-update` với `BASE_IMAGE` là image baseline đã build/kiểm thử và `APP_REVISION` là SHA mã mới. Trước đó phải xác nhận requirements, Dockerfile gốc, thư viện resource và ảnh game không thay đổi. Các recipe này giữ các lớp dependency đã xác minh để Pi không phải tải/cài lại; nếu dependency hoặc asset thay đổi, dùng build đầy đủ. CI luôn build image đầy đủ từ Dockerfile chính.
