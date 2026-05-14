import requests
import json
import os
import time
import re
import sys
import io
import hashlib
from urllib.parse import quote, unquote
from PIL import Image
from io import BytesIO


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

GLOBAL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def is_url_reachable(url):
    """Kiểm tra URL có sống không bằng phương thức GET(stream=True) để lách luật chặn HEAD của các CDN như Cloudfront."""
    try:
        resp = requests.get(url, headers=GLOBAL_HEADERS, timeout=5, stream=True, allow_redirects=True)
        resp.close() # Đóng luồng ngay lập tức
        return resp.status_code == 200
    except Exception:
        return False

def slugify(text):
    if not text: return ""
    return text.lower().replace(' ', '-').replace('.', '').replace('(', '').replace(')', '')

def fetch_wikidata_info(canonical_name):
    """Tìm Wikidata ID và tên trang Wikipedia (VI/EN)."""
    search_url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": canonical_name,
        "language": "en",
        "format": "json",
        "limit": 1
    }
    result = {"vi_name": None, "vi_title": None, "en_title": None, "inat_id": None}
    try:
        resp = requests.get(search_url, params=params, headers=GLOBAL_HEADERS, timeout=10)
        data = resp.json()
        if data.get('search'):
            qid = data['search'][0]['id']
            entity_params = {
                "action": "wbgetentities",
                "ids": qid,
                "props": "labels|sitelinks|claims",
                "languages": "vi",
                "format": "json"
            }
            e_resp = requests.get(search_url, params=entity_params, headers=GLOBAL_HEADERS, timeout=10)
            entity = e_resp.json().get('entities', {}).get(qid, {})
            
            # P4151: iNaturalist taxon ID
            claims = entity.get('claims', {})
            if 'P4151' in claims:
                result['inat_id'] = claims['P4151'][0].get('mainsnak', {}).get('datavalue', {}).get('value')
                
            # Lấy sitelinks để biết tên trang Wikipedia
            viwiki = entity.get('sitelinks', {}).get('viwiki', {}).get('title')
            enwiki = entity.get('sitelinks', {}).get('enwiki', {}).get('title')
            result['vi_title'] = viwiki
            result['en_title'] = enwiki
            result['vi_name'] = viwiki or entity.get('labels', {}).get('vi', {}).get('value')

    except Exception: pass
    return result

def fetch_wikipedia_description(wiki_title, lang="vi"):
    """Lấy mô tả từ Wikipedia theo ngôn ngữ chỉ định."""
    if not wiki_title: return None
    wiki_api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(wiki_title)}"
    try:
        resp = requests.get(wiki_api, headers=GLOBAL_HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('extract')
    except Exception: pass
    return None

def fetch_vietnam_distribution(usage_key, gbif_details):
    """Kiểm tra sự hiện diện của loài tại Việt Nam thông qua GBIF Occurrence."""
    occ_url = "https://api.gbif.org/v1/occurrence/search"
    params = {"taxonKey": usage_key, "country": "VN", "limit": 0}
    try:
        resp = requests.get(occ_url, params=params, headers=GLOBAL_HEADERS, timeout=10)
        if resp.status_code == 200:
            count = resp.json().get('count', 0)
            if count > 0: return "recorded"
    except Exception: pass
    return "unrecorded"

def fetch_inaturalist_featured_photos(scientific_name, passed_inat_id=None):
    """Lấy CHÍNH XÁC ảnh đại diện (Default) và Gallery (Tối ưu 1-2 calls)."""
    images = []
    taxon_id = passed_inat_id
    
    try:
        if not taxon_id:
            search_url = "https://api.inaturalist.org/v1/taxa"
            search_params = {"q": scientific_name, "per_page": 10}
            s_resp = requests.get(search_url, params=search_params, headers=GLOBAL_HEADERS, timeout=10)
            if s_resp.status_code == 429: raise Exception("429_TOO_MANY_REQUESTS")
            if s_resp.status_code == 200:
                results = s_resp.json().get('results', [])
                for r in results:
                    # So khớp mềm: Chấp nhận nếu tên iNat là một phần của tên scientific_name hoặc ngược lại
                    # Điều này giúp khớp được ngay cả khi có hoặc không có tên tác giả
                    inat_name = r.get('name', '').lower()
                    target_name = scientific_name.lower()
                    if inat_name == target_name or inat_name in target_name or target_name in inat_name:
                        taxon_id = r.get('id')
                        print(f"   + Đã khớp iNaturalist Taxon: {r.get('name')} (ID: {taxon_id})")
                        break
        
        if not taxon_id: return []

        # Bước 2: Truy vấn chi tiết Taxon ID để lấy Default Photo và Gallery chuẩn
        detail_url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
        d_resp = requests.get(detail_url, params={"all_names": "true", "locale": "en"}, headers=GLOBAL_HEADERS, timeout=10)
        
        if d_resp.status_code == 429: raise Exception("429_TOO_MANY_REQUESTS")
        
        if d_resp.status_code == 200:
            taxon_data = d_resp.json().get('results', [{}])[0]
            
            seen_photo_ids = set()
            
            # --- 1. Lấy ẢNH MẶC ĐỊNH (Default Photo) ---
            photo = taxon_data.get('default_photo', {})
            if photo:
                raw_url = photo.get('large_url') or photo.get('medium_url', '')
                url = raw_url.replace('medium', 'large').replace('square', 'large').replace('original', 'large')
                photo_id = photo.get('id')
                license_str = photo.get('license_code')
                if url and record_license_check(license_str):
                    images.append({
                        "url": url,
                        "license": license_str,
                        "author": photo.get('attribution') or "(c) iNaturalist Contributor",
                        "source": "iNaturalist (Default)",
                        "source_url": f"https://www.inaturalist.org/taxa/{taxon_id}",
                        "label": "representative",
                        "primary": False
                    })
                    if photo_id: seen_photo_ids.add(photo_id)

            # --- 2. Lấy GALLERY (Featured Gallery) ---
            taxon_photos = taxon_data.get('taxon_photos', [])
            for photo_item in taxon_photos:
                photo = photo_item.get('photo', {})
                photo_id = photo.get('id')
                
                # Tránh trùng lặp do khác size (large vs original)
                if photo_id in seen_photo_ids: continue
                
                raw_url = photo.get('large_url') or photo.get('medium_url', '')
                url = raw_url.replace('medium', 'large').replace('square', 'large').replace('original', 'large')
                license_str = photo.get('license_code')
                if url and record_license_check(license_str):
                    images.append({
                        "url": url,
                        "license": license_str,
                        "author": photo.get('attribution') or "(c) iNaturalist Contributor",
                        "source": "iNaturalist (Featured Gallery)",
                        "source_url": f"https://www.inaturalist.org/taxa/{taxon_id}",
                        "label": "representative",
                        "primary": False
                    })
                    if photo_id: seen_photo_ids.add(photo_id)
                if len(images) >= 8: break 
                
    except Exception as e:
        if str(e) == "429_TOO_MANY_REQUESTS":
            raise e
        pass
        
    return images

def fetch_gbif_occurrence_images(usage_key, needed_general=0):
    """Lấy 1 ảnh Specimen, và BÙ ĐẮP thêm ảnh thường nếu hụt nguồn."""
    occ_url = "https://api.gbif.org/v1/occurrence/search"
    images = []
    seen_urls = set()
    
    search_passes = [
        ({"taxonKey": usage_key, "basisOfRecord": "PRESERVED_SPECIMEN", "mediaType": "StillImage", "limit": 5}, 1), # Khóa chặt 1 ảnh specimen
        ({"taxonKey": usage_key, "basisOfRecord": "HUMAN_OBSERVATION", "mediaType": "StillImage", "limit": 50}, needed_general) # Chỉ lấy ảnh thiên nhiên
    ]
    
    for params, target_limit in search_passes:
        if target_limit <= 0: continue
        
        pass_images = 0
        try:
            resp = requests.get(occ_url, params=params, headers=GLOBAL_HEADERS, timeout=10)
            if resp.status_code != 200: continue
            results = resp.json().get('results', [])
            for r in results:
                # Ưu tiên lấy từ array media chuẩn, nếu không có mới tìm trong extensions
                media_list = r.get('media', [])
                if not media_list and 'extensions' in r:
                    media_list = r.get('extensions', {}).get('http://rs.gbif.org/terms/1.0/Multimedia', [])
                
                if not media_list: continue

                for m in media_list:
                    url = m.get('identifier') or m.get('http://purl.org/dc/terms/identifier')
                    if not url or url in seen_urls: continue
                    
                    license_str = m.get('license') or m.get('http://purl.org/dc/terms/license') or r.get('license')
                    
                    # Dùng GBIF Image Proxy thay vì link gốc bảo tàng để tránh timeout/die
                    gbif_id = r.get('key')
                    md5_hash = hashlib.md5(url.encode()).hexdigest()
                    proxy_url_hq = f"https://api.gbif.org/v1/image/cache/1200x/occurrence/{gbif_id}/media/{md5_hash}"
                    proxy_url_std = f"https://api.gbif.org/v1/image/cache/occurrence/{gbif_id}/media/{md5_hash}"
                    
                    # Chấp nhận ảnh nếu license ổn hoặc nếu đang quá khan hiếm ảnh
                    is_license_ok = record_license_check(license_str)
                    
                    # Thử lấy bản HQ trước (Timeout ngắn 3s), nếu không được thì trả về bản chuẩn
                    final_url = proxy_url_std
                    if is_url_reachable(proxy_url_hq):
                        final_url = proxy_url_hq
                    
                    # Chỉ lấy ảnh nếu license sạch (CC)
                    if is_license_ok:
                        basis = r.get('basisOfRecord')
                        author = m.get('rightsHolder') or m.get('http://purl.org/dc/terms/rightsHolder') or r.get('recordedBy') or "Museum/Herbarium"
                        images.append({
                            "url": final_url,
                            "license": license_str or "All Rights Reserved (Check Source)",
                            "author": author,
                            "source": f"GBIF {basis}",
                            "source_url": f"https://www.gbif.org/occurrence/{gbif_id}",
                            "label": "specimen" if basis == "PRESERVED_SPECIMEN" else "general"
                        })
                        seen_urls.add(url)
                        pass_images += 1
                        if pass_images >= target_limit: break
                if pass_images >= target_limit: break
        except Exception: continue
    return images

def record_license_check(license_str):
    """
    KIỂM TRA LICENSE NGHIÊM NGẶT: Chỉ chấp nhận các loại bản quyền mở (CC, Public Domain).
    """
    if not license_str: return False
    l = str(license_str).lower()
    
    # Các từ khóa vàng của bản quyền mở
    keywords = ["by", "zero", "cc0", "public domain", "publicdomain", "pdm", "creative", "cc-", "unrestricted"]
    
    is_cc = any(kw in l for kw in keywords)
    if not is_cc:
        print(f"   [!] Loại bỏ ảnh do bản quyền không cho phép: {license_str}")
    return is_cc

def fetch_gbif_details(usage_key):
    """Lấy thông tin lõi từ GBIF."""
    base_url = f"https://api.gbif.org/v1/species/{usage_key}"
    details = {}
    try:
        details['core'] = requests.get(base_url, headers=GLOBAL_HEADERS, timeout=10).json()
        for sub in ['vernacularNames', 'synonyms']:
            details[sub] = requests.get(f"{base_url}/{sub}", headers=GLOBAL_HEADERS, timeout=10).json().get('results', [])
    except Exception: pass
    return details

def enrich_single_species(original_name):
    print(f"Đang tra cứu GBIF cho: {original_name}...")
    match_url = "https://api.gbif.org/v1/species/match"
    match_resp = requests.get(match_url, params={'name': original_name}, timeout=10)
    if match_resp.status_code != 200: return {"error": "GBIF connection failed"}
    
    match_data = match_resp.json()
    accepted_key = None
    
    # 1. Xử lý ca rớt hạng sâu
    if match_data.get('matchType') == 'HIGHERRANK' and match_data.get('rank') not in ['SPECIES', 'SUBSPECIES', 'VARIETY', 'FORM']:
        search_url = "https://api.gbif.org/v1/species/search"
        # Khoanh vùng đúng GBIF Backbone (datasetKey) 
        # Nâng limit lên 5 để tránh bị Genus "đè" mà vẫn giữ tốc độ cao
        s_params = {"q": original_name, "datasetKey": "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c", "limit": 5}
        try:
            s_resp = requests.get(search_url, params=s_params, timeout=10)
            if s_resp.status_code == 200:
                s_results = s_resp.json().get('results', [])
                # Duyệt tìm kết quả khớp nhất là SPECIES/SUBSPECIES thay vì vớt ngay thằng đầu tiên
                for candidate in s_results:
                    # Nếu tìm thấy một Đồng danh (Synonym) ở cấp độ loài trở xuống
                    if candidate.get('rank') in ['SPECIES', 'SUBSPECIES', 'VARIETY', 'FORM']:
                        if candidate.get('taxonomicStatus') in ['SYNONYM', 'HOMOTYPIC_SYNONYM', 'HETEROTYPIC_SYNONYM']:
                            accepted_key = candidate.get('acceptedKey')
                            if accepted_key: 
                                print(f"   + Tìm thấy Accepted Key từ Synonym: {candidate.get('scientificName')} -> {accepted_key}")
                                break
                    # Nếu tìm thấy chính nó nhưng trạng thái là ACCEPTED (mà /match bỏ sót)
                    elif candidate.get('taxonomicStatus') == 'ACCEPTED' and candidate.get('rank') in ['SPECIES', 'SUBSPECIES', 'VARIETY', 'FORM']:
                        accepted_key = candidate.get('key')
                        break
        except Exception: pass
        
        # Nếu tên bị giáng cấp do vừa là Synonym cũ vừa Sai chính tả
        # Ta lấy Tên Chi (Genus) đã được API xác nhận + Tên Loài lỗi của người dùng để ép API /match tra lại lần 2
        if not accepted_key and match_data.get('genus'):
            parts = original_name.split()
            if len(parts) >= 2:
                hybrid_name = f"{match_data.get('genus')} {parts[1]}"
                try:
                    h_resp = requests.get(match_url, params={'name': hybrid_name}, timeout=10)
                    if h_resp.status_code == 200:
                        h_data = h_resp.json()
                        # Nếu nó chỉ huy động Fuzzy Match để sửa sai chính tả thì tha bổng
                        if h_data.get('rank') in ['SPECIES', 'SUBSPECIES', 'VARIETY', 'FORM'] and h_data.get('confidence', 0) >= 80:
                            accepted_key = h_data.get('acceptedUsageKey', h_data.get('usageKey'))
                except Exception: pass

        if not accepted_key:
            return {"error": f"Bị giáng cấp xuống {match_data.get('rank')}", "details": "Danh pháp quá cũ, hệ thống cứu nét tự động cũng bó tay."}
    else:
        # Nếu không bị rớt hạng sâu, phải đáp ứng điểm tự tin >= 80
        if match_data.get('confidence', 0) < 80:
            return {"error": "Low confidence match", "details": f"Confidence: {match_data.get('confidence')}"}
        accepted_key = match_data.get('acceptedUsageKey', match_data.get('usageKey'))

    if not accepted_key:
        return {"error": "Missing usage key"}
    accepted_details = fetch_gbif_details(accepted_key)
    core = accepted_details.get('core', {})
    
    # Parent data
    parent_details = {}
    if core.get('parentKey'):
        p_resp = requests.get(f"https://api.gbif.org/v1/species/{core['parentKey']}", timeout=10)
        if p_resp.status_code == 200: parent_details = p_resp.json()

    # Wikidata/Wikipedia
    canonical_name = core.get('canonicalName', original_name)
    wiki_info = fetch_wikidata_info(canonical_name)
    
    # Tóm tắt logic mô tả: VI -> EN -> null
    description = fetch_wikipedia_description(wiki_info.get('vi_title'), "vi")
    lang = "vie" if description else None
    
    if not description:
        description = fetch_wikipedia_description(wiki_info.get('en_title'), "en")
        if description:
            lang = "eng"

    # Vietnam Distribution
    vietnam_status = fetch_vietnam_distribution(accepted_key, accepted_details)

    # JSON Result Construction
    res = {
        "taxon": {
            "scientificName": core.get('scientificName'),
            "canonicalName": canonical_name,
            "authorship": core.get('authorship'),
            "rank": core.get('rank', '').lower(),
            "slug": slugify(canonical_name),
            "description": description,
            "description_lang": lang,
            "distribution_vi": vietnam_status,
            "confidence": match_data.get('confidence'),
            "externalIds": {"gbif": accepted_key},
            "status": core.get('taxonomicStatus', '').lower(),
            "parent": {
                "scientificName": parent_details.get('scientificName'),
                "canonicalName": parent_details.get('canonicalName'),
                "authorship": parent_details.get('authorship'),
                "rank": parent_details.get('rank', '').lower(),
                "externalIds": {"gbif": parent_details.get('key')}
            } if parent_details else None
        },
        "names": [],
        "common_names": [],
        "images": []
    }

    # Common Names (Lọc rác trùng tên Latinh)
    def clean_name_add(name, language, source):
        if not name: return
        # Nếu tên trùng khớp với tên Latinh rút gọn -> Bỏ qua
        if name.strip().lower() == canonical_name.lower(): return
        # Nếu đã có trong danh sách -> Bỏ qua
        if any(cn['name'].lower() == name.strip().lower() for cn in res['common_names']): return
        res['common_names'].append({"name": name.strip(), "language": language, "source": source})

    clean_name_add(wiki_info.get('vi_name'), "vie", "Wikipedia")
    for n in accepted_details.get('vernacularNames', []):
        lang_map = {"eng": "eng", "vie": "vie", "en": "eng", "vi": "vie"}
        glang = n.get('language')
        if glang in lang_map:
            clean_name_add(n.get('vernacularName'), lang_map[glang], n.get('source'))
    # Synonyms (Mỗi định danh đủ 3 trường + GBIF ID)
    for s in accepted_details.get('synonyms', []):
        res['names'].append({
            "scientificName": s.get('scientificName'),
            "canonicalName": s.get('canonicalName'),
            "authorship": s.get('authorship'),
            "status": "synonym",
            "rank": s.get('rank', '').lower(),
            "externalIds": {"gbif": s.get('key')}
        })

    # Images (Hợp nhất từ các nguồn)
    # 1. Wikipedia representative
    if wiki_info.get('vi_title') or wiki_info.get('en_title'):
        title = wiki_info.get('vi_title') or wiki_info.get('en_title')
        lang = "vi" if wiki_info.get('vi_title') else "en"
        wiki_api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
        try:
            w_resp = requests.get(wiki_api, headers=GLOBAL_HEADERS, timeout=10)
            if w_resp.status_code == 200:
                img_url = w_resp.json().get('thumbnail', {}).get('source')
                if img_url and is_url_reachable(img_url):
                    res['images'].append({
                        "url": img_url,
                        "license": "Wikipedia",
                        "author": "Contributor",
                        "source": "Wikipedia",
                        "source_url": w_resp.json().get('content_urls', {}).get('desktop', {}).get('page'),
                        "label": "representative",
                        "primary": False
                    })
        except Exception: pass
    
    # 2. iNaturalist Items
    res['images'].extend(fetch_inaturalist_featured_photos(canonical_name, wiki_info.get('inat_id')))
    
    # 3. GBIF Items (Chính sách Bù đắp: Nếu tổng ảnh Wiki + iNat < 5, mạn phép kéo thêm GBIF General)
    current_img_count = len(res['images'])
    needed_general = max(0, 5 - current_img_count)
    res['images'].extend(fetch_gbif_occurrence_images(accepted_key, needed_general))

    # --- LOGIC GÁN ẢNH CHÍNH (PRIMARY) & LỌC TRÙNG ---
    seen_urls = set()
    unique_images = []
    
    for img in res['images']:
        if img['url'] not in seen_urls:
            img['primary'] = False 
            unique_images.append(img)
            seen_urls.add(img['url'])

    # Gán Primary theo thứ tự ưu tiên: iNaturalist -> Wikipedia -> GBIF
    primary_assigned = False
    for img in unique_images:
        if img['source'] == "iNaturalist (Default)":
            img['primary'] = True
            primary_assigned = True
            unique_images.remove(img)
            unique_images.insert(0, img)
            break
            
    if not primary_assigned:
        for img in unique_images:
            if img['source'].startswith("iNaturalist") or img['source'] == "Wikipedia":
                img['primary'] = True
                primary_assigned = True
                unique_images.remove(img)
                unique_images.insert(0, img)
                break
    
    if not primary_assigned and unique_images:
        unique_images[0]['primary'] = True

    # Cuối cùng là giới hạn số lượng ảnh
    res['images'] = unique_images[:10]
    return res

if __name__ == "__main__":
    ip_path = os.path.join('enrich_data', 'input.txt')
    test_sp = "Nelumbo nucifera"
    if os.path.exists(ip_path):
        with open(ip_path, 'r', encoding='utf-8') as f:
            test_sp = f.read().strip() or test_sp
            
    print(f"Bắt đầu: {test_sp}")
    final_result = enrich_single_species(test_sp)
    
    op_path = os.path.join('enrich_data', 'single_species_full.json')
    with open(op_path, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)
    
    print(f"Xong! Lưu tại: {op_path}")
    print(f"Số ảnh thu được: {len(final_result.get('images', []))}")
