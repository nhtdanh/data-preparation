import re
import json

input_file = "full_clean2.txt"
output_file = "extracted_blocks.json"

# Do dùng [a-z] (chữ cái ASCII không dấu), nó sẽ tự động bỏ qua toàn bộ Tiếng Việt có dấu
# re.MULTILINE để ký tự ^ hiểu là đầu mỗi dòng.
regex = r"^(\d+(?:\.\d+)?[a-z]?)\s*[-.]?\s*([A-Z][a-z]{3,}(?:\s+[a-z\-]+)+)"
header_pattern = re.compile(regex, re.MULTILINE)

blocks = []


try:
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    matches = list(header_pattern.finditer(text))
    for i, match in enumerate(matches):
        start_pos = match.start()
        # Điểm kết thúc của block nay là điểm bắt đầu của block tiếp theo
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
        # Cắt text, trim space và \n ở 2 đầu
        block_text = text[start_pos:end_pos].strip()
        blocks.append(block_text)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(blocks, f, ensure_ascii=False, indent=4)
    print(f"Lưu vào: {output_file}")

except FileNotFoundError:
    print("Lỗi")
