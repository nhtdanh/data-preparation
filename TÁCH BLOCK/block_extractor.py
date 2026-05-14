import re

# Hằng số regex

VIET_DIACRITIC = re.compile(
    r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]',
    re.IGNORECASE
)

LATIN1_AUTHOR = re.compile(r'[éèëêàâîïôûüùñçœæßÉÈËÊÀÂÎÏÔÛÜÙÑÇŒÆ]')

DOUBLE_DOT_RE = re.compile(r'\.\s*\.')

INDEX_RE = re.compile(r'^(\d+(?:[.,]\d+)*)([a-zA-Z*](?!\w))?\s*[-.]?\s*', re.IGNORECASE)

# Tập các từ khóa tiếng Anh (EN anchors) — dùng để phát hiện phần mô tả EN/FR
_EN_ANCHORS = (
    r'[Tt]ree(?:let)?|[Ss]hrub|[Hh]erb|[Bb]ush|[Tt]uft'
    r'|[Cc]limb(?:er|ing)|[Vv]olubile|[Tt]wining|[Ss]preading'
    r'|[Ff]ern|[Ff]rond|[Ss]tem|[Ll]imb'
    r'|[Ll]eaf(?:lets?)?|[Ll]eaves|[Rr]hizome'
    r'|[Pp]lant|[Ss]pike(?:let)?|[Tt]errestrial|[Ee]piphytic'
    r'|[Aa]nnual|[Pp]erennial|[Ee]rect|[Ss]candent|[Pp]rostrate'
    r'|[Ss]aprophytic|[Bb]amboo|[Cc]ulm|[Oo]rnamental|[Cc]ultivated'
    r'|[Cc]reeping|[Mm]ain\s+(?:stem|rhizome)|[Ss]tipe|[Bb]ranch(?:es)?'
    r'|[Rr]achis|[Ss]pore|[Ss]porangi|[Ss]trobile'
    r'|[Ff]loating|[Hh]alophytic|[Rr]oot(?:less)?|[Dd]ecumbent'
    r'|[Ss]armentous|[Ss]mall\s+(?:tree|shrub|herb)|[Bb]ig\s+(?:tree|climber|twiner|fern|shrub)'
    r'|[Ww]oody\s+climber|[Ss]ubshrub|[Hh]alophyte|[Aa]quatic'
    r'|[Ll]iana|[Aa]scending|[Dd]eciduous|[Ll]imnophyte'
    r'|[Hh]ooked|[Tt]horny|[Ss]pinous|[Ss]pinescent'
    r'|[Gg]rass|[Ll]atex|[Tt]hallus|[Rr]obust'
    r'|[Cc]apitulae?|[Cc]apitulum'
    r'|[Ff]rutex|[Dd]ioecious|[Bb]iennial'
    r'|[Ii]nferior\s+pinn(?:ae|a)|[Pp]inn(?:ae|a)\b|[Vv]eins?\s+form'
    r'|[Ss]porophyll(?:s)?|[Cc]yathium|[Gg]eophyte'
    r'|[Cc]ommon(?:ly)?|[Ff]ine\s+(?:tree|shrub|herb)|[Rr]are\s+herb'
    r'|[Pp]eltate'
)

# Một dòng được coi là tóm tắt EN/FR nếu:
#   A: bắt đầu bằng "- " hoặc "-" hoặc "*" theo sau anchor hoặc chữ hoa
#   B: bắt đầu trực tiếp bằng một từ anchor tiếng Anh
#   C: toàn bộ dòng chỉ là "Cultivated." hoặc "Ornamental." (dòng độc lập)
EN_LINE_RE = re.compile(
    rf'^[\*\-]\s*(?:[A-Z].*|(?:{_EN_ANCHORS})\b.*)'
    rf'|^(?:{_EN_ANCHORS})\b',
    re.IGNORECASE
)

# Dòng chỉ chứa "Cultivated." / "Ornamental." (không có văn bản khác)
_CULTIVATED_RE = re.compile(r'^-?\s*(?:Cultivated|Ornamental)\.?\s*(?:\([^)]+\)\.?)?\s*$', re.IGNORECASE)

# Mẫu: dấu chấm + khoảng trắng cuối cùng trước khả năng bắt đầu tên Việt
# Dùng để tách sci/viet trong trường hợp chỉ có một dấu chấm.
LAST_PERIOD_SPACE_RE = re.compile(r'\.\s+(?=[A-Z\u00C0-\u024F])')


def _find_inline_en_boundary(line: str):
    """
    Phát hiện EN bắt đầu giữa dòng sau phần tiếng Việt.
    Trả về (vi_part, en_part) nếu tìm được, ngược lại None.
    """
    if len(VIET_DIACRITIC.findall(line)) < 2:
        return None

    # Tìm mọi từ khóa anchor tiếng Anh trong dòng
    anchors_regex = rf'\b(?:{_EN_ANCHORS})\b'
    for m in re.finditer(anchors_regex, line, re.IGNORECASE):
        # Mở rộng vị trí tách sang trái để bao gồm dấu '-' hoặc khoảng trắng
        boundary = m.start()
        while boundary > 0 and line[boundary-1] in ' \t-*':
            boundary -= 1

        prefix = line[:boundary]
        suffix = line[boundary:]

        # Hậu tố nên có ít dấu tiếng Việt (<=2)
        if len(VIET_DIACRITIC.findall(suffix)) <= 2:
            # Tiền tố nên có nhiều dấu tiếng Việt (>=2)
            if len(VIET_DIACRITIC.findall(prefix)) >= 2:
                suffix_clean = re.sub(r'^[\*\-\s]+', '', suffix)
                if not suffix_clean:
                    continue
                if suffix_clean[0].isupper() or prefix.rstrip().endswith('.'):
                    return prefix.strip(), suffix.strip()

    # Dự phòng: tìm '. ' làm ranh giới nếu không có anchor
    for m in reversed(list(re.finditer(r'\.\s+', line))):
        suffix = line[m.end():]
        prefix = line[:m.end()-1]
        prefix_full = line[:m.end()].strip()

        if not suffix:
            continue
        suffix_clean = re.sub(r'^[\*\-\s]+', '', suffix)
        if not suffix_clean:
            continue

        if (suffix_clean[0].isupper()
                and len(VIET_DIACRITIC.findall(suffix)) <= 2
                and len(VIET_DIACRITIC.findall(prefix_full)) >= 2):
            return prefix_full, suffix.strip()

    return None


def split_foreign(text: str) -> tuple[str, str]:
    """
    Tách phần tiếng Anh/ngoại ngữ (từ dòng EN đầu tiên tới cuối) ra khỏi phần
    tiếng Việt. Cũng phát hiện các dòng "Cultivated." / "Ornamental.".
    """
    lines = text.split('\n')
    if not lines:
        return text, ''

    en_start_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Dòng EN nên có ít hoặc không có dấu tiếng Việt
        if EN_LINE_RE.match(stripped) or _CULTIVATED_RE.match(stripped):
            viet_count = len(VIET_DIACRITIC.findall(stripped))
            if viet_count / max(len(stripped), 1) < 0.15:
                en_start_idx = i
                break

    if en_start_idx == -1:
        vi_lines = lines
        foreign = ''
    else:
        vi_lines = lines[:en_start_idx]
        foreign_lines = lines[en_start_idx:]
        raw_foreign = '\n'.join(foreign_lines).strip()
        foreign = re.sub(r'^[\*\-]\s*', '', raw_foreign).strip()

    # Hậu xử lý: kiểm tra EN bắt đầu ngay trong dòng cuối của phần viet
    last_nonempty_idx = None
    for idx in range(len(vi_lines) - 1, -1, -1):
        if vi_lines[idx].strip():
            last_nonempty_idx = idx
            break

    if last_nonempty_idx is not None:
        last_line = vi_lines[last_nonempty_idx].strip()
        result = _find_inline_en_boundary(last_line)
        if result:
            vi_part, en_part = result
            vi_lines[last_nonempty_idx] = vi_part
            foreign = (en_part + '\n' + foreign).strip() if foreign else en_part

    vi = '\n'.join(vi_lines).strip()
    return vi, foreign


# ── Step 2: Tách header (1–2 dòng) và phần mô tả ───────────────────────────

def split_header_body(text: str) -> tuple[str, str]:
    """
    Header = dòng đầu (có thể kèm dòng 2 nếu là tên Việt).
    Body = mọi dòng còn lại.
    """
    lines = text.split('\n')
    if not lines:
        return text, ''

    body_start = 1

    if len(lines) >= 2:
        first = lines[0].rstrip()
        second = lines[1].strip()

        first_ends_sentence = first.endswith('.') or first.endswith(';')
        second_short = bool(second) and len(second) <= 60

        if not first_ends_sentence and second_short:
            viet_ratio = len(VIET_DIACRITIC.findall(second)) / max(len(second), 1)
            if viet_ratio < 0.5:
                body_start = 2
            else:
                body_start = 2
        elif (first_ends_sentence and second_short
              and second.endswith('.')
              and len(second.split()) <= 7
              and ',' not in second
              and ';' not in second):
            body_start = 2

    header = ' '.join(lines[i].strip() for i in range(body_start) if lines[i].strip())
    body = '\n'.join(lines[body_start:]).strip()
    return header, body


# ── Step 3: Tách tên khoa học và tên tiếng Việt trong header ───────────────

def split_sci_viet(header: str) -> tuple[str, str, str]:
    """
    Trả về (sci_name, viet_name, sep_method).
    sep_method: 'double_dot' | 'last_period' | 'none'
    """
    if not header:
        return '', '', 'none'

    # Tín hiệu A: dấu chấm đôi/ba — quy ước nhà xuất bản
    m_dd = DOUBLE_DOT_RE.search(header[:250])
    if m_dd:
        sci = header[:m_dd.end()].strip()
        vn = header[m_dd.end():].strip().strip('.,;:')
        return sci, vn, 'double_dot'

    # Tín hiệu B: dấu ". " cuối cùng trong ~180 ký tự
    search_zone = header[:180]
    matches = list(LAST_PERIOD_SPACE_RE.finditer(search_zone))
    if matches:
        m = matches[-1]
        sci = header[:m.start() + 1].strip()
        vn = header[m.end():].strip().strip('.,;:')
        sci_words = sci.split()
        if len(sci_words) >= 2 and sci_words[0][0].isupper():
            return sci, vn, 'last_period'

    return header.strip(), '', 'none'


# ── Step 4: Đánh giá độ tin cậy tách ───────────────────────────────────────

def _confidence(sep: str, vn: str) -> str:
    if sep == 'double_dot' and VIET_DIACRITIC.search(vn):
        return 'high'
    if sep == 'last_period' and (VIET_DIACRITIC.search(vn) or vn):
        return 'medium'
    if sep == 'last_period' and not vn:
        return 'low'
    return 'low'


# ── Pipeline chính: phân tích một block thành dict ─────────────────────────

def parse_species_block(raw_block: str) -> dict | None:
    """Phân tích một block thô thành 4 trường có cấu trúc."""
    text = raw_block.strip()
    if not text:
        return None

    # 1. Bỏ phần số chỉ mục ở đầu
    m = INDEX_RE.match(text)
    if not m:
        return None
    index = re.sub(r'[^\w]', '', m.group(1) + (m.group(2) or '')).lower()
    rest = text[m.end():].strip()

    # 2. Tách phần foreign (EN/FR)
    vi_full, foreign = split_foreign(rest)

    # 3. Tách header và phần mô tả tiếng Việt
    header, desc_vi = split_header_body(vi_full)

    # 4. Tách tên khoa học và tên Việt
    sci_name, viet_name, sep = split_sci_viet(header)

    # 5. Chuẩn hóa khoảng trắng trong mô tả tiếng Việt
    desc_vi = re.sub(r'\s+', ' ', desc_vi).strip()

    # 6. Loại bỏ ký tự thừa ở cuối mô tả
    desc_vi = desc_vi.rstrip(' -').strip()

    # 7. Chuẩn hóa phần EN
    desc_en = re.sub(r'\s*\n\s*', ' ', foreign).strip()
    desc_en = re.sub(r'  +', ' ', desc_en)

    return {
        'index':            index,
        'scientific_name':  sci_name,
        'vietnamese_name':  viet_name,
        'description_vi':   desc_vi,
        'description_en':   desc_en,
        '_sep':             sep,
        '_confidence':      _confidence(sep, viet_name),
    }


if __name__ == '__main__':
    import sys, json
    sys.stdout.reconfigure(encoding='utf-8')

    tests = [
        ("Block 1 - double_dot",
         "1 - Psilotum nudum (L.) Beauv.. Lõatùng trần.\n"
         "Bụi nhỏ, thường ở đất, không lông.\n"
         "- Terrestrial; stem rootless, dichotomous."),
        ("Block 3 - viet spans newline",
         "3 - Huperzia cancellata (Spring) Trevis. Thạchtùng\n"
         "bôi.\n"
         "Cô phụsinh thông, dài đến 40 cm.\n"
         "- Epiphytic, stem dichotomous; leaves 3-4mm long."),
        ("Block 1901 - single dot same line",
         "1901 Elaeocarpus poilanei Gagn. Tô.\n"
         "Đạimộc cao 10-12 m; thân to đến 30 cm.\n"
         "- Tree 12 m high; leaves glabrous; racemes short."),
        ("Block 1800 - viet_name on next line",
         "1887 - Elaeocarpus harmandii Pierre. Côm\n"
         "Harmand.\n"
         "Đạimộc cao 15 m; thân có rễ càkhêu.\n"
         "- Tree 15 m high; leaves glabrous."),
        ("Block 1912 - transliterated viet name",
         "1912 Sloanea hemsleyana (Ito) Rehder & Wilson.\n"
         "So-loan Hemsley.\n"
         "Đạimộc; nhánh có bìkhẩu xoan tròndài.\n"
         "- Tree; leaves membranous."),
        ("Block bush - EN anchor",
         "1910 - Elaeocarpus viguieri Gagn.. Nhôi.\n"
         "Bụi; nhánh kịchcơm, có lông hoe lúc non.\n"
         "Ninhbình.\n"
         "- Shrub; branches rufous pubescent."),
        ("Block no-dash tree",
         "1855 Grewia langsonensis Gagn.. Còke Lạngsơn.\n"
         "Đạimộc cao 11 m; nhánh không lông.\n"
         "Lạngsơn.\n"
         "Tree 7-11 m, glabrous; petals 2,5-3 mm;\n"
         "androgynophore short; ovary 4-celled."),
        ("Block 1806 - stub",
         "1893 - Elaeocarpus laoticus Gagn."),
        ("Block 1925 - English names in viet",
         "1925 Corchorus capsularis L.. Bó, Đai; White Jute;\n"
         "Jute.\n"
         "Cỏ nhấtniên, cao 1-2 m. Lá có phiến thon.\n"
         "Cultivated; leaves ovate lanceolate; capsules globulous."),
        ("Block 2640 - dash_no_space",
         "2640 Styrax crotonoides Clarke. Antức cùđèn.\n"
         "Đạimộc cao 13(30) m; thân to 8-13 cm.\n"
         "Bình và trungnguyên: Hàtuyên; IV.\n"
         "-Tree 13(30) m high; leaves with long stellate\nhairs on nerves; seeds tomentose."),
        ("Block 5680 - standalone cultivated",
         "5680 - Poncirus trifoliatus (L.) Raf... Chi; Trifoliate\n"
         "Orange.\n"
         "Tiểumộc cao đến 5 m, có nhiều nhánh; gai to.\n"
         "Cultivated (Citrus trifoliatus L.)."),
        ("Block 9213 - ascending",
         "9213 Floscopa glabratus Hassk.. Dầu-riều không-lông.\n"
         "Cỏ bò rồi đứng; thân ít nhánh.\n"
         "Chợgành.\n"
         "Ascending herb; limb rough; flowers white."),
        ("Block 10.633 - dot index",
         "10.633 - Cymbopogon caesius (Nees) Stapf.. Sả lam.\n"
         "Bụi cao 1 m, rất thơm; thân có nhánh.\n"
         "Hoang ở rừng thưa: Quảngtrị.\n"
         "- Tuft to 1 m high; awn 1 cm long."),
    ]

    for label, raw in tests:
        print(f'\n=== {label} ===')
        r = parse_species_block(raw)
        if r:
            print(f'  sci  [{r["_sep"]}/{r["_confidence"]}]: {r["scientific_name"]}')
            print(f'  vn   : {r["vietnamese_name"]}')
            print(f'  vi   : {r["description_vi"][:90]}')
            print(f'  en   : {r["description_en"][:80]}')
        else:
            print('  FAILED TO PARSE')