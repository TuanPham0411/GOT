# XiaoZhi Copper Robot

Project được tích hợp vào portal tại `/projects/xiaozhi-esp32`.

- Backend và API `/api/xiaozhi`: `portal/xiaozhi_tools.py`.
- Trang project, trình biên tập, hướng dẫn cài đặt: `portal/templates/xiaozhi_*.html`, `portal/static/xiaozhi-*.{js,css}`.
- Firmware installer công khai: `portal/static/xiaozhi/manifest.json`, binary ESP32-S3 2.4.0 và hướng dẫn kèm theo, được lưu bằng Git LFS.
- GPT/YouTube cần `OPENAI_API_KEY`/`YOUTUBE_API_KEY`; robot tools cần `XIAOZHI_TOOLS_TOKEN` hiện có. Không lưu giá trị trong Git.
- Phiên nhạc, binding robot, giấy phép, lịch sử download: private `/data` của portal. ffmpeg được cài trong image.
- ZIP phát hành riêng tư được giữ trong `/data/files`, phục hồi từ bản cũ của SIKA.

Không tìm thấy source ESP32/ESP-IDF hoặc project firmware gốc trên các thư mục ứng dụng đang chạy của SIKA. Binary hiện có không đủ để build lại firmware. Cần bổ sung repository firmware gốc nếu muốn CI build firmware từ nguồn.
