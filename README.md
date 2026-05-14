# Xử lý dữ liệu từ bộ sách Cây Cỏ Việt Nam

## Giới thiệu

Tổng quan về dự án: Xử lý dữ liệu từ file pdf để thu được dữ liệu hoàn chỉnh - sẵn sàng cho việc nhập vào website

## Cấu trúc

**Thư mục:**

- OCR/: Sử dụng tesseract để OCR từ file pdf -> file txt
- TÁCH BLOCK/: làm sạch và tách file txt thành các khối và lưu thành file json
- SỬA LỖI/: Sửa lỗi chính tả
- THU THẬP DỮ LIỆU/: gọi api/crawl dữ liệu và hình ảnh cho Loài và cao hơn loài (cho tới Ngành)

**Files:**
- species_raw.txt: dữ liệu ban đầu OCR từ file pdf
- species_blocks.json: dữ liệu được tách thành các block
- species_blocks_corrected.json: dữ liệu đã sửa lỗi chính tả
- species_parsed_and_mapped.json: dữ liệu đã tách nhỏ ra các trường và ánh xạ thuật ngữ
- species_final.jsonl: dữ liệu hoàn chỉnh của Loài
