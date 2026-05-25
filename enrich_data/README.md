# Làm giàu và Ánh xạ dữ liệu

Thư mục này chứa các file dữ liệu đã được làm giàu từ các nguồn bên ngoài (GBIF, iNaturalist, Wikipedia) và các file ánh xạ tên khoa học.

## Cấu trúc dữ liệu

Các file `.jsonl` chứa dữ liệu chi tiết cho từng cấp phân loại:

- **phylum_data.jsonl**: Dữ liệu cấp Ngành.
- **class_data.jsonl**: Dữ liệu cấp Lớp.
- **order_data.jsonl**: Dữ liệu cấp Bộ.
- **family_data.jsonl**: Dữ liệu cấp Họ.
- **genus_data.jsonl**: Dữ liệu cấp Chi.
- **species_data.jsonl**: Dữ liệu cấp Loài.

Dữ liệu trong mỗi dòng JSONL (đặc biệt là đối với cấp loài) bao gồm các trường chi tiết sau:

- `index`: Số thự tự trong sách (với cấp Loài) hoặc ID tham chiếu từ dữ liệu gốc.
- `scientificName`: Tên khoa học đầy đủ của taxon (bao gồm cả danh xưng tác giả).
- `canonicalName`: Tên khoa học rút gọn (không bao gồm danh xưng tác giả).
- `authorship`: Tên tác giả công bố danh pháp.
- `rank`: Cấp bậc phân loại sinh học (ví dụ: `phylum`, `class`, `order`, `family`, `genus`, `species`).
- `slug`: Chuỗi định danh URL thân thiện (URL-friendly string) được tạo từ tên khoa học.
- `description`: Mô tả chi tiết về sinh thái, hình thái hoặc đặc điểm ( Wikipedia).
- `description_lang`: Mã ngôn ngữ của phần mô tả (ví dụ: `vie`, `eng`).
- `distribution_vi`: Trạng thái phân bố tại Việt Nam (ví dụ: `recorded`, `unrecorded`).
- `confidence`: Điểm số độ tin cậy của quá trình đối chiếu/làm giàu dữ liệu (từ 0 đến 100).
- `externalIds`: Đối tượng (Object) chứa ID tham chiếu đến các cơ sở dữ liệu bên ngoài (ví dụ: `{"gbif": 123456}`).
- `status`: Trạng thái của danh pháp (ví dụ: `accepted` - tên được chấp nhận, `synonym` - tên đồng nghĩa).
- `parent`: Thông tin về taxon cha trực tiếp, bao gồm `scientificName`, `canonicalName`, `authorship`, `rank` và `externalIds`.
- `names`: Mảng (Array) các danh pháp đồng nghĩa (synonyms). Mỗi mục bao gồm `scientificName`, `canonicalName`, `authorship`, `status`, `rank` và `externalIds`.
- `common_names`: Mảng các tên thường gọi/tên địa phương. Mỗi mục bao gồm `name` (tên gọi), `language` (ngôn ngữ, ví dụ: `vie`, `eng`) và `source` (nguồn trích xuất, ví dụ: Wikipedia, TAXREF).
- `images`: Mảng các hình ảnh liên quan đến taxon. Mỗi mục bao gồm:
  - `url`: Đường dẫn tới hình ảnh.
  - `license`: Giấy phép bản quyền của hình ảnh.
  - `author`: Tác giả/người chụp.
  - `source`: Nguồn cung cấp ảnh (ví dụ: iNaturalist, GBIF PRESERVED_SPECIMEN, Wikipedia).
  - `source_url`: Link trang gốc chứa hình ảnh.
  - `label`: Phân loại hình ảnh (ví dụ: `representative` cho ảnh chụp ngoài tự nhiên, `specimen` cho ảnh mẫu vật).
  - `primary`: Giá trị boolean (`true`/`false`) đánh dấu hình ảnh đại diện chính.
