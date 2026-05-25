# Dữ liệu chính

Thư mục này lưu trữ các file dữ liệu trung gian và file kết quả cuối cùng (có chỉnh sửa thủ công)

## Các file dữ liệu theo luồng xử lý

Dưới đây là mô tả chi tiết của từng file, được sắp xếp theo đúng thứ tự các bước xử lý dữ liệu:

1. **`01_species_raw.txt`**:
   Dữ liệu văn bản thô ban đầu, được trích xuất (thông qua OCR) từ file PDF của bộ sách. Đây là đầu vào nguyên bản của toàn bộ hệ thống.

2. **`02_extracted_blocks.json`**:
   Dữ liệu sau giai đoạn trích xuất khối ban đầu từ văn bản thô. Các khối (block) được tách ra nhưng chưa được xử lý và sửa lỗi.

3. **`03_species_blocks.json`**:
   Dữ liệu sau khi đã trải qua giai đoạn cắt và tách khối. Trong file này,mỗi block được chia thành các trường nhỏ hơn (index, scientific_name...).

4. **`04_species_blocks_corrected.json`**:
   Dữ liệu sau khi các block đã được chạy qua quy trình kiểm tra và sửa các lỗi chính tả (những lỗi này thường phát sinh trong quá trình nhận dạng ký tự quang học - OCR).

5. **`05_species_parsed_and_mapped.json`**:
   Dữ liệu sau khi mô tả tiếng Việt được tách thành cấu trúc rõ ràng (dạng sống, sinh sản, phân bố...) và thực hiện ánh xạ thuật ngữ.

6. **`06_species_final.jsonl`**:
   **Dữ liệu hoàn chỉnh cuối cùng của cấp Loài (Species).** File này chứa dữ liệu đã được tổng hợp, chuẩn hóa và làm giàu thêm thông tin từ các nguồn dữ liệu sinh học bên ngoài (như GBIF, iNaturalist, Wikipedia). Định dạng JSONL được sử dụng để tối ưu cho các tập dữ liệu lớn. Đây là file sẵn sàng để import trực tiếp vào cơ sở dữ liệu của website.

## Lưu ý

- Các file này có can thiệp và sửa thủ công bằng tay để đảm bảo độ chính xác nên sẽ có sự khác biệt so với file đầu ra của các script ở thư mục khác
