# Nhạc nền (background music)

Thư mục này chứa nhạc nền royalty-free dùng cho video. `CollageEngine`
(`styles/collage_broll/collage_engine.py::_find_background_music`) tự lấy file
`*.mp3`/`*.wav` trong thư mục này; âm lượng mặc định 0.07–0.08 theo
`config/settings.yaml` → `video.background_music`.

## Danh sách & giấy phép

Cả 3 bản nhạc đều của **Kevin MacLeod** (incompetech.com), phát hành qua
Wikimedia Commons. Giấy phép CC BY **bắt buộc ghi credit** khi dùng trong video
(hệ thống tự ghi nguồn asset vào mô tả/export — xem Giai đoạn 5.3 provenance;
khi đăng video nơi khác hãy giữ dòng credit dưới đây).

| File | Tác phẩm | Giấy phép | Nguồn gốc |
|---|---|---|---|
| `kevin_macleod_cattails.mp3` | "Cattails" — Kevin MacLeod | CC BY 3.0 | https://commons.wikimedia.org/wiki/File:Kevin_MacLeod_-_Cattails.mp3 |
| `kevin_macleod_holiday_weasel.mp3` | "Holiday Weasel" — Kevin MacLeod | CC BY 2.0 | https://commons.wikimedia.org/wiki/File:Kevin_MacLeod_-_Holiday_Weasel_(cc-by)_(filmmusic).mp3 |
| `kevin_macleod_stay_the_course.mp3` | "Stay The Course" — Kevin MacLeod | CC BY 4.0 | https://commons.wikimedia.org/wiki/File:Kevin_MacLeod_-_Stay_The_Course_(cc-by)_(filmmusic).mp3 |

Dòng credit mẫu:

> Music: "Cattails", "Holiday Weasel", "Stay The Course" by Kevin MacLeod
> (incompetech.com), licensed under CC BY — via Wikimedia Commons.

## Ghi chú kỹ thuật

- File trong repo đã được re-encode từ bản gốc 320kbps xuống **128kbps**
  (giữ nguyên thời lượng/nội dung) để nhẹ repo; bản gốc tải lại bằng
  `python scripts/download_assets.py`.
- Muốn thêm nhạc mới: chỉ thêm file có license rõ ràng (CC0/CC BY/public domain)
  và ghi bổ sung vào bảng trên.
