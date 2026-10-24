# XiaoZhi Copper Robot ESP32-S3 2.4.0

## Cấu hình bản phát hành

- Chip: ESP32-S3
- Flash: 16 MB, DIO, 80 MHz
- Board profile: `COPPER_ROBOT_S3`
- ESP-IDF: 6.0.2
- Firmware hợp nhất: ghi tại offset `0x0`
- SHA-256: `34AC924ACBEAF7BAE25381D6C9961F69A61DD978434DD58868A729C160C27586`

## Cài trực tuyến

1. Dùng Chrome hoặc Edge trên máy tính và cáp USB có truyền dữ liệu.
2. Ngắt các chương trình đang dùng cổng COM. Giữ nguồn ổn định.
3. Mở trang dự án trên thienha.io.vn, đăng nhập và chọn **Cài firmware trực tuyến**.
4. Chọn đúng cổng USB/JTAG hoặc UART của ESP32-S3, xác nhận xóa flash và chờ hoàn tất.
5. Không rút cáp trong khi đang ghi. Khi hoàn tất, nhấn Reset nếu thiết bị chưa tự khởi động.

## Cài bằng dòng lệnh

```powershell
py -m pip install --upgrade esptool
py -m esptool --chip esp32s3 erase-flash
py -m esptool --chip esp32s3 --baud 460800 write-flash 0x0 xiaozhi-copper-robot-v2.4.0-esp32s3.bin
```

## Khởi động và vận hành

1. Lần đầu khởi động, thiết bị vào chế độ cấu hình Wi-Fi khi chưa có mạng đã lưu.
2. Làm theo thông báo trên màn hình/âm thanh để kết nối mạng 2.4 GHz.
3. Sau khi kết nối, thiết bị đăng ký dịch vụ, đồng bộ cấu hình và chuyển sang trạng thái chờ.
4. Dùng từ đánh thức hoặc nút tương tác theo cấu hình phần cứng Copper Robot.
5. Theo dõi log ở 115200 baud khi cần chẩn đoán.

## Driver và phần mềm

- Windows 10/11 thường nhận USB Serial/JTAG của ESP32-S3 tự động.
- Nếu board dùng cầu USB-UART rời, xác định chip trên board rồi cài đúng driver CP210x hoặc CH34x; không cài ngẫu nhiên cả hai.
- Công cụ khuyến nghị: Chrome/Edge cho Web Serial, Espressif ESP-IDF 6.0.2 cho phát triển, esptool cho flash dòng lệnh, Git và Visual Studio Code + ESP-IDF extension.

## Khắc phục nhanh

- Không thấy cổng: đổi cáp dữ liệu, cổng USB, kiểm tra Device Manager và đóng Serial Monitor.
- Không vào bootloader: giữ BOOT, nhấn RESET, thả RESET rồi thả BOOT.
- Flash thất bại giữa chừng: giữ nguyên kết nối, giảm baud xuống 115200 và thử lại.
- Khởi động lặp: xóa toàn bộ flash rồi cài lại đúng bản ESP32-S3/Copper Robot.

Không dùng firmware này cho board khác dù cùng chip ESP32-S3; pin, codec, màn hình và định danh OTA có thể khác.
