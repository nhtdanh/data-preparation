import os
import json
import re
import sys
import time
from jiwer import wer, cer

# Thêm path dự án
sys.path.append(os.getcwd())
try:
    from main.corrector import Corrector
except ImportError:
    from corrector import Corrector

# Hỗ trợ UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIG ---
DATA_PATH = "main/data/grouth_truth_prepared.json"
OUTPUT_REPORT = "main/results/full_grid_search_results.txt"

# Dải tham số Tinh chỉnh (36 combos)
GRID_PARAMS = []
for err in [-3.5, -4.0, -4.5]:
    for ctx in [2.0, 2.25, 2.5, 2.75]:
        for ph in [2.0, 2.5, 3.0]:
            GRID_PARAMS.append({"error": err, "domain": 0.0, "context": ctx, "phonetic": ph})

def clean_for_metric(text):
    if not text: return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def run_full_search():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] ĐANG QUÉT 36 TỔ HỢP TRÊN TOÀN BỘ {len(data)} MẪU...", flush=True)
    
    corrector = Corrector()
    results = []

    start_time = time.time()
    for idx, p in enumerate(GRID_PARAMS):
        corrector.set_weights(**p)
        total_wer = 0
        total_cer = 0
        
        for item in data:
            truth = clean_for_metric(item["truth"].replace("_", ""))
            pred = clean_for_metric(corrector.process_text(item["original"], passes=2, expand_compounds=False))
            total_wer += wer(truth, pred)
            total_cer += cer(truth, pred)
            
        avg_wer = total_wer / len(data)
        avg_cer = total_cer / len(data)
        results.append((avg_wer, avg_cer, p))
        
        # In tiến độ mỗi 3 tổ hợp để theo dõi trực tiếp
        if (idx + 1) % 3 == 0:
            elapsed = time.time() - start_time
            print(f"    -> {idx + 1}/36: WER={avg_wer:.4f} | {p['error']}, {p['context']}, {p['phonetic']} ({elapsed:.1f}s)", flush=True)

    # Sắp xếp theo WER tăng dần
    results.sort(key=lambda x: x[0])

    # Ghi báo cáo
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("BÁO CÁO FULL GRID SEARCH (TẬP TRUNG VÙNG TRỌNG TÂM)\n")
        f.write("="*60 + "\n")
        f.write(f"{'Hạng':<5} | {'WER':<8} | {'CER':<8} | {'Tham số (Error, Context, Phonetic)':<30}\n")
        f.write("-" * 60 + "\n")
        for i, (w, c, p) in enumerate(results):
            f.write(f"{i+1:<5} | {w:.6f} | {c:.6f} | {p['error']}, {p['context']}, {p['phonetic']}\n")
    
    print(f"\n[OK] Đã xong! Top 1: {results[0][2]} với WER={results[0][0]:.6f}", flush=True)
    print(f"[*] Báo cáo lưu tại: {OUTPUT_REPORT}", flush=True)

if __name__ == "__main__":
    run_full_search()
