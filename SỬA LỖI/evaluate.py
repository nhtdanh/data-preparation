import sys
# Cấu hình mã hóa UTF-8 để in tiếng Việt trên Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import re
import os
import sys
import time
from jiwer import wer, cer

# Import bộ công cụ
sys.path.append(os.getcwd())
try:
    from main.corrector import Corrector
except ImportError:
    from corrector import Corrector

# Hỗ trợ hiển thị tiếng Việt trên Terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# --- THÔNG SỐ CẤU HÌNH ---
BEST_PARAMS = {
    "error": -4.0,
    "domain": 0.0,
    "context": 2.5,
    "phonetic": 2.5
}
PASSES = 2 # Chạy 2 lượt để tối ưu độ chính xác

DATASET_PATH = "main/data/grouth_truth_prepared.json"
SUMMARY_FILE = "main/results/thesis_summary.txt"
DETAIL_FILE = "main/results/evaluation_detail.txt"

def clean_for_metric(text):
    """
    Chuẩn hóa văn bản để đánh giá chỉ số WER/CER.
    """
    if not text: return ""
    text = text.lower().strip()
    # Normalize Decimals: "1, 5" -> "1,5"
    text = re.sub(r'(\d+),\s+(\d+)', r'\1,\2', text)
    # Normalize Hyphens: "II - III" -> "II-III"
    text = re.sub(r'([a-z0-9à-ỹ])\s*-\s*([a-z0-9à-ỹ])', r'\1-\2', text)
    # Remove extra space around punctuation
    text = re.sub(r'\s+([,.!?:;])', r'\1', text)
    # Fix multiplication sign: "10 x 3" -> "10x3"
    text = re.sub(r'(\d+)\s*[xX×]\s*(\d+)', r'\1x\2', text)
    # Flatten spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    print("="*50)
    print("CHƯƠNG TRÌNH ĐÁNH GIÁ (LUẬN VĂN)")
    print("="*50)
    
    if not os.path.exists("main/results"):
        os.makedirs("main/results")
        
    corrector = Corrector()
    # error=-4.0, domain=0.0, context=2.5, phonetic=2.5
    corrector.set_weights(error=-4.0, domain=0.0, context=2.5, phonetic=2.5)
    
    if not os.path.exists(DATASET_PATH):
        print(f"Lỗi: Không tìm thấy file {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Đang xử lý {len(data)} mẫu...")
    raw_wer_sum = 0
    pred_wer_sum = 0
    raw_cer_sum = 0
    pred_cer_sum = 0
    
    detail_lines = []
    
    start_time = time.time()
    
    for i, item in enumerate(data):
        raw_ocr = item.get("original", "")
        truth = item.get("truth", "").replace("_", "")
        
        # Thực hiện sửa lỗi với 2 lượt quét
        pred = corrector.process_text(raw_ocr, passes=PASSES, expand_compounds=False)
        
        # Clean for standardized metrics
        c_raw = clean_for_metric(raw_ocr)
        c_truth = clean_for_metric(truth)
        c_pred = clean_for_metric(pred)
        
        # Calculate WER/CER
        w_raw = wer(c_truth, c_raw)
        w_pred = wer(c_truth, c_pred)
        ce_raw = cer(c_truth, c_raw)
        ce_pred = cer(c_truth, c_pred)
        
        raw_wer_sum += w_raw
        pred_wer_sum += w_pred
        raw_cer_sum += ce_raw
        pred_cer_sum += ce_pred
        
        # Lưu chi tiết để kiểm tra sau
        detail_lines.append(f"Mẫu #{i+1}")
        detail_lines.append(f"Gốc:    {raw_ocr}")
        detail_lines.append(f"Sửa:    {pred}")
        detail_lines.append(f"Chuẩn:  {truth}")
        detail_lines.append(f"WER: {w_raw:.4f} -> {w_pred:.4f} | CER: {ce_raw:.4f} -> {ce_pred:.4f}")
        detail_lines.append("-" * 30)
        
        if (i+1) % 50 == 0:
            print(f"-> Đã xong {i+1} mẫu")

    duration = time.time() - start_time
    avg_raw_wer = raw_wer_sum / len(data)
    avg_pred_wer = pred_wer_sum / len(data)
    avg_raw_cer = raw_cer_sum / len(data)
    avg_pred_cer = pred_cer_sum / len(data)
    
    summary = [
        "="*50,
        "KẾT QUẢ ĐÁNH GIÁ CUỐI CÙNG",
        "="*50,
        f"Tổng số mẫu: {len(data)}",
        f"Thời gian:   {duration:.2f}s",
        f"Tham số:     {corrector.error_weight}, {corrector.domain_weight}, {corrector.context_weight}, {corrector.phonetic_weight}",
        "",
        "CHỈ SỐ TỔNG HỢP:",
        f"- WER gốc: {avg_raw_wer:.4f}",
        f"- WER mới: {avg_pred_wer:.4f} (Cải thiện {((avg_raw_wer - avg_pred_wer)/avg_raw_wer)*100:.2f}%)",
        f"- CER gốc: {avg_raw_cer:.4f}",
        f"- CER mới: {avg_pred_cer:.4f} (Cải thiện {((avg_raw_cer - avg_pred_cer)/avg_raw_cer)*100:.2f}%)",
        "="*50
    ]
    
    summary_text = "\n".join(summary)
    
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(summary_text)
        
    with open(DETAIL_FILE, "w", encoding="utf-8") as f:
        f.write(summary_text + "\n\n" + "\n".join(report_lines))
    
if __name__ == "__main__":
    main()
