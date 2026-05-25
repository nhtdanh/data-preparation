import json
import os
import regex
from tqdm import tqdm
import concurrent.futures
import multiprocessing
import sys

# Biến toàn cục cho các tiến trình con (worker) để tránh truyền dữ liệu lớn qua IPC liên tục
global_ocr_data = []

def init_worker(ocr_data):
    """Hàm khởi tạo cho mỗi worker, nạp ocr_data vào bộ nhớ của tiến trình con"""
    global global_ocr_data
    global_ocr_data = ocr_data

def process_name(item):
    """Hàm xử lý một tên khoa học duy nhất"""
    # Lấy canonical_name để dò
    name = item.get('canonical_name')
        
    if not name:
        # Giữ nguyên item và báo page là None nếu không có tên
        result = item.copy()
        result["page"] = None
        return result
        
    escaped_name = regex.escape(name)
    
    # 3 mức edit distance để tránh sửa quá lố
    if len(name) > 15:
        max_errors = 3
    elif len(name) > 8:
        max_errors = 2
    else:
        max_errors = 1
        
    pattern = regex.compile(rf'({escaped_name}){{e<={max_errors}}}', regex.IGNORECASE)
    
    found_page = None
    
    for page_data in global_ocr_data:
        if pattern.search(page_data["content"]):
            found_page = page_data["page"]
            break
            
    # Gắn thêm trường page vào record ban đầu
    result = item.copy()
    result["page"] = found_page
    return result

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    # Đường dẫn
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ocr_file = os.path.join(SCRIPT_DIR, 'pages.json')
    names_file = os.path.join(SCRIPT_DIR, 'species.json')
    output_file = os.path.join(SCRIPT_DIR, 'species_with_pages.json')

    if not os.path.exists(ocr_file):
        print(f"Lỗi: Không tìm thấy {ocr_file}")
        return
    if not os.path.exists(names_file):
        print(f"Lỗi: Không tìm thấy {names_file}")
        return

    print("Đang tải dữ liệu...")
    with open(ocr_file, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    with open(names_file, 'r', encoding='utf-8') as f:
        names_data = json.load(f)

    print(f"Tổng số trang OCR: {len(ocr_data)}")
    print(f"Tổng số tên khoa học cần tìm: {len(names_data)}")

    matched_results = []
    
    # 5 luồng
    max_workers = 5
    print(f"Bắt đầu xử lý với {max_workers} luồng CPU...")

    # Mở file để ghi liên tục dạng chuẩn JSON mảng [...]
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("[\n")
        first_item = True
        
        # Sử dụng ProcessPoolExecutor
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers, 
            initializer=init_worker, 
            initargs=(ocr_data,)
        ) as executor:
            
            # Dùng executor.map để đảm bảo kết quả ghi ra đúng y xì thứ tự của species.json
            results_generator = executor.map(process_name, names_data)
            
            for result in tqdm(results_generator, total=len(names_data), desc="Đang so khớp tên"):
                if result:
                    matched_results.append(result)
                    
                    if not first_item:
                        outfile.write(",\n")
                    first_item = False
                    
                    # Thêm thắt lùi lề (indent=4) để giống định dạng của species.json
                    outfile.write("    " + json.dumps(result, ensure_ascii=False, indent=4).replace("\n", "\n    "))
                    outfile.flush()
                    
        outfile.write("\n]\n")
        
    print(f"\nHoàn tất! Đã lưu kết quả ánh xạ vào:\n{output_file}")
    
    # Báo cáo thống kê chi tiết
    success_results = [r for r in matched_results if r.get("page") is not None]
    missing_results = [r for r in matched_results if r.get("page") is None]
    
    success_count = len(success_results)
    missing_count = len(missing_results)
    
    print(f"\n" + "="*30)
    print(f"      BÁO CÁO KẾT QUẢ")
    print(f"+" + "="*28)
    print(f"Tỷ lệ tìm thấy: {success_count}/{len(names_data)} ({success_count/len(names_data)*100:.2f}%)")
    print(f"Số lượng không tìm thấy: {missing_count}")
    
    if missing_count > 0:
        missing_file = os.path.join(SCRIPT_DIR, 'missing_pages.json')
        with open(missing_file, 'w', encoding='utf-8') as f:
            json.dump(missing_results, f, ensure_ascii=False, indent=2)
        
        print(f"\nĐã lưu danh sách các index không tìm thấy vào:")
        print(f"   {missing_file}") 
    
    print("="*30 + "\n")

if __name__ == "__main__":
    main()
