# Triển khai Raspberry Pi Sika

Chưa triển khai thực tế: chưa truy cập được SSH của Sika. Không dừng dịch vụ hiện tại trước khi đối chiếu mã nguồn và sao lưu.

## Chuẩn bị

Trên Pi chạy `uname -m`, `cat /etc/os-release`, `df -h`, `free -h`, `ss -lntp`; kiểm tra systemd, Cloudflare/nginx hiện tại. Image cần Linux ARM64 (`aarch64`) hoặc AMD64. Chưa kiểm thử ARM 32 bit.

Cài Docker Engine và Compose theo hệ điều hành:

- Debian / Raspberry Pi OS 64 bit: https://docs.docker.com/engine/install/debian/
- Raspberry Pi OS 32 bit: https://docs.docker.com/engine/install/raspberry-pi-os/

Chỉ chọn gói sau khi xác định OS. Windows/macOS dùng Docker Desktop với Linux containers.

## Chạy song song và chuyển dịch vụ

1. Sao lưu riêng tư mã nguồn, systemd, nginx/Cloudflare và dữ liệu ứng dụng. Không đưa database, `.env`, khóa hoặc token lên GitHub.
2. Cài Git LFS, clone kho vào thư mục mới và chạy `git lfs pull`. Không chép đè bản đang chạy.
3. Chạy `docker compose up -d --build --wait`. Container ở `127.0.0.1:5080`, không chiếm cổng 5000.
4. Kiểm tra `/healthz`, `/api/bootstrap`, ảnh, âm thanh Việt/Anh và phiên tạo từ portal.
5. Sau khi đạt, đổi origin hiện có của game sang `http://127.0.0.1:5080`. Giữ origin portal. Kiểm tra lại tên miền công khai và phiên chơi.
6. Giữ dịch vụ cũ để rollback. Nếu lỗi, khôi phục origin cũ rồi `docker compose stop game`. Không dùng `down -v` vì sẽ xóa volume cache.

## Dùng image đã kiểm thử

Workflow chỉ xuất bản image sau khi kiểm thử đạt:

```sh
export GOT_IMAGE=ghcr.io/tuanpham0411/got/game:COMMIT_SHA_DA_KIEM_THU
docker compose -f compose.yaml -f compose.registry.yaml pull
docker compose -f compose.yaml -f compose.registry.yaml up -d --no-build --wait
```

Nếu GHCR chưa công khai, cần `docker login ghcr.io` với quyền đọc package. Không lưu token vào kho. Dùng commit SHA để rollback chính xác.
