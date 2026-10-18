# Daily Quirk Agent

Mỗi ngày 3 lần: tự chọn một chủ đề kỳ quặc trên Internet, research 2–3 nguồn,
viết bài Markdown ngắn tiếng Việt, gửi vào Telegram.

## Cài đặt
1. Push repo này lên GitHub.
2. Vào **Settings → Secrets and variables → Actions**, thêm 3 secrets:
   - `ORTHOGONAL_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. (Tuỳ chọn) thêm variables `ORTHOGONAL_BASE`, `ORTHOGONAL_MODEL` nếu API
   của bạn khác default.
4. Vào tab **Actions → Daily Quirk Agent → Run workflow** để test thủ công.
5. Lịch tự chạy: 07:00, 13:00, 20:00 (giờ VN).
