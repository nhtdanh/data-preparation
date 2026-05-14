import sys
import os
import io
sys.path.append(os.getcwd())
try:
    from main.corrector import Corrector
except ImportError:
    from corrector import Corrector

def main():
    input_text = "manhnangw" 
    # False: Trả về dạng dính chữ, True: Trả về dạng cách chữ
    is_spaced = True 
    print(f"Gốc:   {input_text}")
    print(f"Chế độ: {'Dính chữ (Joined)' if not is_spaced else 'Cách chữ (Spaced)'}")

    try:
        c = Corrector(
            unigram_path="main/data/unigram.txt",
            bigram_path="main/data/bigram.txt"
        )
        
        c.set_weights(error=-4.0, domain=0.0, context=2.5, phonetic=2.5)
        
        res = c.process_text(input_text, passes=2, expand_compounds=is_spaced)
        
        print(f"Sửa:   {res}")
        
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    main()
