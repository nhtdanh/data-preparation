import re
import unicodedata
from collections import Counter

# Đọc file
with open('../full_clean2.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Ll, Lu, Lo = chữ cái
# Mn, Mc, Me = dấu
# Nd = số
# Pc, Pd, Po = punctuation/symbols
# Z = whitespace/separators
# C = control/format

latin_base = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
vietnamese_marks = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ')
vietnamese_marks |= set(char.upper() for char in vietnamese_marks if char.upper() != char)

# Ký tự được phép khác
allowed_extras = set('0123456789 \n\r\t.-,;:()[]{}\'\"')

# Tìm ký tự lạ
unusual_chars = {}
lines_with_unusual = {}

for line_num, line in enumerate(content.split('\n'), 1):
    for char in line:
        if not (char in latin_base or 
                char in vietnamese_marks or 
                char in allowed_extras or
                char.isspace()):
            
            if char not in unusual_chars:
                unusual_chars[char] = {
                    'count': 0,
                    'unicode': f'U+{ord(char):04X}',
                    'name': unicodedata.name(char, 'UNKNOWN'),
                    'category': unicodedata.category(char),
                    'examples': []
                }
            
            unusual_chars[char]['count'] += 1
            
            if len(unusual_chars[char]['examples']) < 3:
                start = max(0, line.find(char) - 20)
                end = min(len(line), line.find(char) + 21)
                context = line[start:end].replace('\n', ' ').strip()
                unusual_chars[char]['examples'].append((line_num, context))

# Sắp xếp theo tần suất
sorted_chars = sorted(unusual_chars.items(), key=lambda x: x[1]['count'], reverse=True)

# Report
with open('../unusual_chars_report.txt', 'w', encoding='utf-8') as f:
    f.write(f"Tổng ký tự lạ: {len(unusual_chars)}\n")
    f.write(f"Tổng xuất hiện: {sum(c['count'] for c in unusual_chars.values())}\n\n")
    
    for char, info in sorted_chars:
        f.write(f"\n{'─' * 100}\n")
        f.write(f"Ký tự: '{char}'\n")
        f.write(f"  Unicode: {info['unicode']}\n")
        f.write(f"  Tên: {info['name']}\n")
        f.write(f"  Category: {info['category']}\n")
        f.write(f"  Tần suất: {info['count']}\n")
        f.write(f"  Ví dụ:\n")
        
        for line_num, context in info['examples']:
            f.write(f"    Line {line_num}: ...{context}...\n")
