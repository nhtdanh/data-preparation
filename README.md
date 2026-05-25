# Xử lý dữ liệu từ bộ sách Cây Cỏ Việt Nam

Xử lý thêm dữ liệu về vị trí của loài trong bộ sách - sẵn sàng cho việc nhập vào website

## Cấu trúc

**Thư mục:**

- [OCR (Google Drive)](https://drive.google.com/drive/folders/1GBdYO42hNUY8vqYAfFbuPYdzh25rxtE8?usp=sharing): Chứa các file và kết quả quá trình nhận dạng ký tự quang học (OCR) ban đầu. Do kích thước dữ liệu quá lớn nên phần này được lưu trữ ngoài trên Google Drive.
- [enrich_data](enrich_data/): Chứa dữ liệu đã được làm giàu từ các nguồn bên ngoài cho các cấp phân loại từ Loài đến Ngành.
- [main_data_files](main_data_files/): Chứa các file dữ liệu trung gian và kết quả cuối cùng.

**File:**

- [pages.json](pages.json): File JSON tổng hợp từ thư mục OCR, mỗi phần tử là 1 trang sách với `page` và `content`
- [species.json](species.json): File JSON dữ liệu loài gần như hoàn chỉnh, lấy ra trường `canonical_name` (danh pháp 2 phần) để tra cứu trong `content` của `pages.json`.
- [match_species_to_pages.py](match_species_to_pages.py): Script thực hiện việc so khớp `canonical_name` với `content` để lấy ra `page`.
- [species_with_pages.json](species_with_pages.json): File kết quả hoàn chỉnh gồm dữ liệu loài và vị trí trong bộ sách.
- [missing_pages.json](missing_pages.json): những loài không tìm thấy nếu chỉ chạy Script, cần xử lý thủ công
