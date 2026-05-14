import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from comprehensive_enricher_single import enrich_single_species

# --- CẤU HÌNH ---
INPUT_FILE = "names.json"
OUTPUT_FILE = "output_data.jsonl"
FAILED_LOG = "failed_species.log"
MAX_WORKERS = 5

write_lock = threading.Lock()

def ensure_newline_at_eof(filename):
    """Đảm bảo file kết thúc bằng một dấu xuống dòng trước khi append dữ liệu mới để tránh lỗi }{ """
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'rb+') as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b'\n':
                f.write(b'\n')
                print(f"[*] Đã tự động chèn dấu xuống dòng còn thiếu vào cuối file {filename}")

def load_processed_species():
    processed = set()
    
    # 1. Đọc các con đã có trong file output để bỏ qua (Skip)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        # CHẾ ĐỘ TIẾT KIỆM: Đã có index là bỏ qua, không quan tâm 0 ảnh hay nhiều ảnh
                        if "original_data" in record and "clean_scientific_name" in record["original_data"]:
                            processed.add(record["original_data"]["clean_scientific_name"].lower())
                    except Exception: pass

    # YÊU CẦU MỚI: XÓA ÁN TÍCH CHO CÁC CON BỊ LỖI TRƯỚC ĐÂY!
    # Không đọc file failed_species.log nữa để kịch bản xử lý lại các file lỗi bằng thuật toán Cứu nét.
    return processed

import time
import random

def process_single(item):
    species_name = item["clean_scientific_name"]
    species_index = item.get("index", "N/A")
    # Áp dụng Jitter (Ngủ ngẫu nhiên 0.5 - 2.5 giây) 
    # Giúp 3 luồng vĩnh viễn chạy lệch pha, không bao giờ "nã đạn" cùng 1 miligiây
    time.sleep(random.uniform(0.5, 2.5))
    
    try:
        res = enrich_single_species(species_name)
        
        if "error" in res:
            with write_lock:
                with open(FAILED_LOG, 'a', encoding='utf-8') as f:
                    f.write(f"[{species_index}] {species_name} | {res['error']}\n")
            return f"[{species_index}] {species_name} (Error: {res['error']})"
            
        final_res = {"original_data": item}
        final_res.update(res)
            
        with write_lock:
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(final_res, ensure_ascii=False) + "\n")
        return f"✅ {species_name} (Images: {len(res.get('images', []))})"
        
    except Exception as e:
        if str(e) == "429_TOO_MANY_REQUESTS":
            raise e # Bắn thẳng ra ngoài để ThreadPool chộp lấy
        with write_lock:
            with open(FAILED_LOG, 'a', encoding='utf-8') as f:
                f.write(f"[{species_index}] {species_name} | FATAL EXCEPTION: {str(e)}\n")
        return f"❌ [{species_index}] {species_name} (FATAL EXCEPTION)"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[!] Không tìm thấy tệp '{INPUT_FILE}'. Vui lòng để chung trong cùng thư mục.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Nhúng nguyên vẹn object thay vì chỉ lấy tên
        all_items = [item for item in data if "clean_scientific_name" in item]

    processed = load_processed_species()
    pending_items = [item for item in all_items if item["clean_scientific_name"].lower() not in processed]

    # Đảm bảo file output không bị dính dòng với lần chạy cũ
    ensure_newline_at_eof(OUTPUT_FILE)

    print(f"=== HỆ THỐNG BATCH PROCESSING THỰC VẬT ===")
    print(f"Tổng số loài: {len(all_items)}")
    print(f"Đã xử lý (Skip): {len(processed)}")
    print(f"Cần xử lý: {len(pending_items)}")
    print(f"Khởi động với {MAX_WORKERS} luồng...\n")

    if not pending_items:
        print("Hoàn tất! Không còn loài nào cần xử lý.")
        return

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Quăng toàn bộ danh sách pending vào bể bơi ThreadPool
            future_to_sp = {executor.submit(process_single, item): item["clean_scientific_name"] for item in pending_items}
            
            for index, future in enumerate(as_completed(future_to_sp), 1):
                sp = future_to_sp[future]
                try:
                    result_msg = future.result()
                    print(f"[{index}/{len(pending_items)}] {result_msg}")
                except Exception as exc:
                    if str(exc) == "429_TOO_MANY_REQUESTS":
                        print(f"\n[!!!] BÁO ĐỘNG ĐỎ: iNaturalist trả về 429 TOO MANY REQUESTS tại loài '{sp}'")
                        print("[!!!] Hệ thống đang bị khóa IP. Đang cưỡng chế dừng toàn bộ tiến trình...")
                        print("=========================================================")
                        print("=> HÃY BẬT VPN ĐỔI IP VÀ CHẠY LẠI SCRIPT NÀY!")
                        print("Hệ thống sẽ tự nhận diện những loài đã làm và bỏ qua.")
                        print("=========================================================\n")
                        # Ép Node thoát khẩn cấp để hãm phanh ngay lập tức
                        os._exit(1)
                    else:
                        print(f"[{index}/{len(pending_items)}] Lỗi kịch bản tại {sp}: {exc}")
                        
    except KeyboardInterrupt:
        print("\n[!] Bạn vừa bấm Ctrl+C. Hệ thống dừng an toàn.")
        os._exit(0)

if __name__ == "__main__":
    main()
