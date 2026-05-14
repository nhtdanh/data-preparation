import re

with open('../full_clean1.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
pattern_book_title = r'^(?:\d{1,4}\s*[-.]?\s*)?(?:C[âaậyanyhy]+|Chy)\s*c[ỏoóọõ]\s*V[iệeê]+t\s*n[aâ]m(?:\s*[-.]?\s*\d{1,4})?\s*$'
pattern_family_header = r'^\s*[a-z]+(?:aceae|idae|ales|eae|iferae|oideae)\s*[-.]?\s*\d{1,4}\b'
pattern_appendix = r'^Phụ\s*trang\s*\d+$'
pattern_notes = r'xem\s*(?:chú|thêm)'

cleaned_lines = []
deleted_lines = []

for line_num, line in enumerate(lines, 1):
    line_stripped = line.strip()
    
    if re.match(pattern_book_title, line_stripped, re.IGNORECASE):
        deleted_lines.append((line_num, "Book Title", line.rstrip()))
    elif re.match(pattern_family_header, line_stripped, re.IGNORECASE):
        deleted_lines.append((line_num, "Family Header", line.rstrip()))
    elif re.match(pattern_appendix, line_stripped, re.IGNORECASE):
        deleted_lines.append((line_num, "Appendix", line.rstrip()))
    elif re.search(pattern_notes, line_stripped, re.IGNORECASE):
        deleted_lines.append((line_num, "Notes Reference", line.rstrip()))
    else:
        cleaned_lines.append(line)

with open('../full_clean2.txt', 'w', encoding='utf-8') as f:
    f.writelines(cleaned_lines)
with open('../deleted_lines_log.txt', 'w', encoding='utf-8') as f:
    f.write(f"Tổng dòng đã xóa: {len(deleted_lines)}\n")
    f.write("=" * 80 + "\n\n")
    for line_num, pattern_type, content in deleted_lines:
        f.write(f"Line {line_num} [{pattern_type}]: {content}\n")
