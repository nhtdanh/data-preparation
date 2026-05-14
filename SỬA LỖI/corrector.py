import re
import os
import json
import math
import ahocorasick
from symspellpy import SymSpell, Verbosity

class Corrector:
    def __init__(self, 
                 unigram_path="main/data/unigram.txt", 
                 bigram_path="main/data/bigram.txt", 
                 whitelist_path="main/data/whitelist.txt",
                 compounds_path="main/data/compounds.json",
                 error_weight=-4.0,
                 domain_weight=0.0,
                 context_weight=2.5,
                 phonetic_weight=2.5):
        
        # Tham số cấu hình
        self.error_weight = error_weight
        self.domain_weight = domain_weight
        self.context_weight = context_weight
        self.phonetic_weight = phonetic_weight
        
        # 2. Xử lý đường dẫn linh hoạt (Tự động tìm folder data)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        def resolve_path(p, default_name):
            if os.path.isabs(p): return p
            # Thử tìm trong folder data cùng cấp với file corrector.py
            local_path = os.path.join(base_dir, "data", os.path.basename(p))
            if os.path.exists(local_path): return local_path
            return p

        unigram_path = resolve_path(unigram_path, "unigram.txt")
        bigram_path = resolve_path(bigram_path, "bigram.txt")
        whitelist_path = resolve_path(whitelist_path, "whitelist.txt")
        compounds_path = resolve_path(compounds_path, "compounds.json")

        # 3. Nạp từ điển SymSpell
        self.sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=12)
        if not os.path.exists(unigram_path):
            print(f"CẢNH BÁO: Không tìm thấy từ điển tại {unigram_path}")
        else:
            self.sym_spell.load_dictionary(unigram_path, term_index=0, count_index=1, encoding="utf-8")
        
        # 4. Nạp các mô hình bổ trợ
        self.bigram_model = self.load_bigram(bigram_path)
        self.unigram_counts = self.load_unigram_counts(unigram_path)
        self.whitelist = self.load_whitelist(whitelist_path)
        
        # Load mapping từ ghép
        self.compounds_map = {}
        if os.path.exists(compounds_path):
            with open(compounds_path, "r", encoding="utf-8") as f:
                self.compounds_map = json.load(f)

        # Build automaton để quét từ ghép
        self.automaton = ahocorasick.Automaton()
        if isinstance(self.compounds_map, dict):
            for joined, spaced in self.compounds_map.items():
                self.automaton.add_word(spaced, joined)
        self.automaton.make_automaton()
        
        # 7. Regex và quy tắc ngôn ngữ
        self.regex_sci = r"(\d*n|[nx])\s*[=≈]\s*\d+[.,]?\d*"
        self.regex_unit = r"(\b\d+[.,]?\d*\s*-\s*\d+[.,]?\d*|\b\d+[.,]?\d*)\s*((?:cm|mm|m\b|km|kg|g\b|ml|l\b|μm|µm|dm|µ\b|μ\b|°C)\s*)+"
        self.regex_roman = r"\b(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b"
        self.regex_num = r"\b\d+[.,]?\d*(?:-\d+[.,]?\d*)?\b"
        self.units_whitelist = ['cm', 'mm', 'm', 'km', 'kg', 'g', 'ml', 'l', 'µm', 'dm', '°C', 'μm', 'μ']
        self.vowel_map = {
            "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
            "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
            "uè": "uè", "ué": "ué", "uẻ": "uẻ", "uẽ": "uẽ", "uẹ": "uẹ"
        }
        self.temp_map = {}

    def set_weights(self, error=None, domain=None, context=None, phonetic=None):
        if error is not None: self.error_weight = error
        if domain is not None: self.domain_weight = domain
        if context is not None: self.context_weight = context
        if phonetic is not None: self.phonetic_weight = phonetic

    def _normalize_vowels(self, text):
        result = text
        vowels = "aàáảãạeèéẻẽẹiìíỉĩịoòóỏõọuùúủũụyỳýỷỹỵ"
        for old, new in self.vowel_map.items():
            pattern = re.compile(f"(?<![qQgG]){old}(?![{vowels}])")
            result = pattern.sub(new, result)
        return result

    def load_bigram(self, path):
        model = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 3: 
                        model[(parts[0].lower(), parts[1].lower())] = int(parts[2])
        return model

    def load_unigram_counts(self, path):
        counts = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 2: 
                        counts[parts[0].lower()] = int(parts[1])
        return counts

    def load_whitelist(self, path):
        if not os.path.exists(path): return []
        with open(path, "r", encoding="utf-8") as f:
            wl = [line.strip().lower() for line in f if line.strip()]
            return sorted(wl, key=len, reverse=True)

    def _get_case_style(self, word):
        if word.isupper(): return "upper"
        if word[0].isupper(): return "title"
        return "lower"

    def _normalize_tag(self, tag):
        tag = tag.strip(" []")
        match = re.search(r"([A-Z]+)", tag)
        if match:
            prefix = match.group(1)
            if prefix in ["NUM", "UNIT", "WL", "SCI", "ROMAN", "PUNC"]:
                return f"[{prefix.lower()}]"
        return tag.lower()

    def _apply_case_style(self, word, style):
        if style == "upper": return word.upper()
        if style == "title": return (word[0].upper() + word[1:]) if len(word) > 1 else word.upper()
        return word.lower()

    def mask_text(self, text):
        self.temp_map = {}
        idx = 0
        def store(val, label):
            nonlocal idx
            tag = f"{label}{chr(65+idx//26)}{chr(65+idx%26)}"
            self.temp_map[tag] = val
            idx += 1
            return f" [{tag}] "
        
        math_pattern = r"(\d+[.,]?\d*(?:[-\s]*\d+[.,]?\d*)?)\s*[xX×]\s*(\d+[.,]?\d*(?:[-\s]*\d+[.,]?\d*)?)\s*(?:cm|mm|m\b|km|kg|g\b|ml|l\b|μm|µm|dm|°C)?"
        text = re.sub(math_pattern, lambda m: store(m.group(0), "MATH"), text)
        text = re.sub(self.regex_unit, lambda m: store(m.group(0), "UNIT"), text)
        combined_wl = self.whitelist + self.units_whitelist
        for name in combined_wl:
            pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.I)
            text = pattern.sub(lambda m: store(m.group(0), "WL"), text)
        text = re.sub(self.regex_sci, lambda m: store(m.group(0), "SCI"), text)
        text = re.sub(self.regex_roman, lambda m: store(m.group(0), "ROMAN"), text)
        text = re.sub(self.regex_num, lambda m: store(m.group(0), "NUM"), text)     
        return text

    def _remove_diacritics(self, text):
        s1 = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
        s0 = "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
        return text.translate(str.maketrans(s1, s0))

    def unmask_text(self, masked_text):
        def restore(match):
            tag = re.sub(r"[\[\]\s]", '', match.group(0)).upper()
            return self.temp_map.get(tag, match.group(0))
        result = re.sub(r"\[[A-Za-z0-9\s]+\]", restore, masked_text)
        return re.sub(r"\s+", " ", result).strip()

    def calculate_score(self, dist, ug_count, bg_prev, bg_next, is_domain, is_phonetic):
        f_error = dist * self.error_weight
        f_lang = math.log10(ug_count + 1) + (math.log10(bg_prev + bg_next + 1) * self.context_weight)
        f_knowledge = (self.domain_weight if is_domain else 0.0) + (self.phonetic_weight if is_phonetic else 0.0)
        return f_error + f_lang + f_knowledge

    def _rank_with_lookahead(self, suggestions, original_word, prev_token, next_token):
        if not suggestions: return ""
        if len(suggestions) == 1:
            return suggestions[0].term if suggestions[0].distance <= 2 else ""

        best_term, max_score = "", -1e9
        prev_low = self._normalize_tag(prev_token) if prev_token else ""
        next_low = self._normalize_tag(next_token) if next_token else ""
        orig_low_no_accent = self._remove_diacritics(original_word.lower())

        for sug in suggestions:
            term = sug.term
            dist = sug.distance
            if dist > 2: continue

            ug_count = self.unigram_counts.get(term, 1)
            bg_prev = self.bigram_model.get((prev_low, term), 0)
            bg_next = self.bigram_model.get((term, next_low), 0)
            is_domain = term in self.compounds_map
            is_phonetic = (dist > 0 and self._remove_diacritics(term.lower()) == orig_low_no_accent)

            bg_boost = 3.0 if (prev_low in ["[num]", "[unit]"] or next_low in ["[num]", "[unit]"]) else 1.0
            score = self.calculate_score(dist, ug_count, bg_prev * bg_boost, bg_next * bg_boost, is_domain, is_phonetic)

            if score > max_score:
                max_score, best_term = score, term
        return best_term

    def correct_sentence(self, sentence):
        words = re.findall(r'\[[A-Z0-9]{4,}\]|[\wà-ỹ]+|[^\w\s/]', sentence)
        new_words = list(words)
        word_indices = [i for i, w in enumerate(words) if re.match(r"^[a-zA-Zà-ỹ]+$", w)]
        
        i = 0
        while i < len(word_indices):
            matched = False
            for sz in [3, 2]:
                if i + sz <= len(word_indices):
                    indices = word_indices[i:i+sz]
                    valid_interstitial = True
                    for k in range(indices[0] + 1, indices[-1]):
                        if k in word_indices: continue
                        if not re.match(r"^\[PUNC[A-Z]{2}\]$", words[k]):
                            valid_interstitial = False
                            break
                    if not valid_interstitial: continue
                    window = [words[idx] for idx in indices]
                    combined = ''.join(w.lower() for w in window)
                    is_window_valid = True
                    for w in window:
                        if not self.sym_spell.lookup(w.lower(), Verbosity.TOP, max_edit_distance=0):
                            is_window_valid = False
                            break
                    suggestions = self.sym_spell.lookup(combined, Verbosity.TOP, max_edit_distance=1)
                    if suggestions and suggestions[0].distance <= 1:
                        if is_window_valid and suggestions[0].distance > 0: continue
                        best_word = suggestions[0].term
                        style = self._get_case_style(window[0])
                        new_words[indices[0]] = self._apply_case_style(best_word, style)
                        for k in range(indices[0] + 1, indices[-1] + 1): new_words[k] = ''
                        i += sz
                        matched = True
                        break
            if not matched: i += 1
                
        tokens = re.findall(r'\[[A-Z0-9]{4,}\]|[\wà-ỹ]+|[^\w\s/]', ' '.join([w for w in new_words if w]))
        corrected, n = [], len(tokens)
        for i in range(len(tokens)):
            t = tokens[i].strip()
            if not t or (t.startswith('[') and t.endswith(']')):
                if t: corrected.append(t)
                continue
            if re.match(r"^\d+$", t) or not re.match(r"^[\wà-ỹ]+$", t):
                corrected.append(t)
                continue
                
            next_token = ''
            for j in range(i + 1, n):
                nt = tokens[j].strip(' []')
                if not nt: continue
                tag_val = self.temp_map.get(nt, nt)
                if tag_val in '.!?:': break
                if nt in self.temp_map:
                    next_token = self._normalize_tag(nt)
                    break
                clean_nt = nt.strip()
                if clean_nt and re.match(r"^[\wà-ỹ]+$", clean_nt):
                    quick_sug = self.sym_spell.lookup(clean_nt.lower(), Verbosity.TOP, max_edit_distance=2)
                    next_token = quick_sug[0].term if quick_sug else clean_nt.lower()
                    break
            
            actual_prev = ''
            for j in range(i - 1, -1, -1):
                pt = tokens[j].strip(' []')
                if not pt: continue
                tag_val = self.temp_map.get(pt, pt)
                if tag_val in '.!?:': break
                if pt in self.temp_map:
                    actual_prev = self._normalize_tag(pt)
                    break
                clean_pt = pt.strip()
                if clean_pt and re.match(r"^[\wà-ỹ]+$", clean_pt):
                    actual_prev = clean_pt.lower()
                    break

            style, t_low = self._get_case_style(t), t.lower()
            if t.startswith('[') and t.endswith(']'):
                corrected.append(t)
                continue
            t_norm = self._normalize_vowels(t_low)
            # Check spelling
            suggestions = self.sym_spell.lookup(t_norm, Verbosity.ALL, max_edit_distance=2)
            if not suggestions: best = t_norm
            else:
                best = self._rank_with_lookahead(suggestions, t_norm, actual_prev, next_token)
                if not best: best = t_norm
            corrected.append(self._apply_case_style(best, style))

        text = ' '.join(corrected)
        text = re.sub(r'\s+([,.!?:;])', r'\1', text)
        text = re.sub(r'([([{])\s+', r'\1', text)
        text = re.sub(r'\s+([)\]}])', r'\1', text)
        return text.strip()

    def _restore_compounds(self, text):
        tokens = text.split()
        restored = []
        for t in tokens:
            style, t_low = self._get_case_style(t), t.lower()
            if t_low in self.compounds_map:
                restored.append(self._apply_case_style(self.compounds_map[t_low], style))
            else: restored.append(t)
        return " ".join(restored)

    def process_text(self, text, passes=2, expand_compounds=True):
        current_text = re.sub(r'\s+', ' ', text).strip()
        for p in range(passes):
            # Lượt 0: Dính chữ tự động dựa trên từ điển thực vật
            if p == 0:
                matches = list(self.automaton.iter(current_text.lower()))
                if matches:
                    valid_matches, last_end = [], -1
                    for end_idx, joined_value in sorted(matches, key=lambda x: (x[0], -len(x[1]))):
                        original_spaced = self.compounds_map.get(joined_value, "")
                        if not original_spaced: continue
                        start_idx = end_idx - len(original_spaced) + 1
                        if start_idx > last_end:
                            valid_matches.append((start_idx, end_idx, joined_value))  
                            last_end = end_idx
                    if valid_matches:
                        new_text, idx = [], 0
                        for start, end, joined_val in valid_matches:
                            new_text.append(current_text[idx:start])
                            original_val = current_text[start:end+1]
                            new_text.append(self._apply_case_style(joined_val, self._get_case_style(original_val)))
                            idx = end + 1
                        new_text.append(current_text[idx:])
                        current_text = "".join(new_text)

            # Sửa lỗi chính tả bằng SymSpell + Language Model
            masked = self.mask_text(current_text)
            current_text = self.correct_sentence(masked)
            current_text = self.unmask_text(current_text)

            # Khôi phục khoảng trắng nếu cần xử lý đa luồng
            if p < passes - 1 and expand_compounds:
                current_text = re.sub(r'\s+', ' ', self._restore_compounds(current_text)).strip()
        
        # Hậu xử lý văn bản
        current_text = re.sub(r'\s+([,.!?:;])', r'\1', current_text)
        current_text = re.sub(r'([([{])\s+', r'\1', current_text)
        current_text = re.sub(r'\s+([)\]}])', r'\1', current_text)
        current_text = re.sub(r'(\d+)\s*(cm|mm|m|km|kg|g|ml|l|µm|dm|°C)\b', r'\1 \2', current_text)
        current_text = re.sub(r'(\d+),\s+(\d+)', r'\1,\2', current_text)
        current_text = re.sub(r'([a-zA-Z0-9à-ỹ])\s*-\s*([a-zA-Z0-9à-ỹ])', r'\1-\2', current_text)

        # Khôi phục khoảng trắng ở bước cuối nếu người dùng yêu cầu (Spaced mode)
        if expand_compounds: 
            current_text = self._restore_compounds(current_text)
            
        return current_text.strip()
