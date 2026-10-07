from curl_cffi import requests
from datetime import datetime, timedelta
import re
import json
import urllib.parse

# Danh sách ID trận đấu dự phòng
DEFAULT_MATCH_IDS = [
    "6ac5952bf54928d5ed64013e",
    "6ac4d7b72454ab5c04d29b0c",
    "6ac4d7b72454ab5c04d29b10",
    "6ac59574bf3ed6c99566dc1d"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://vip3.saoketv40.xyz",
    "Referer": "https://vip3.saoketv40.xyz/",
    "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site"
}

def fetch_json_with_bypass(url):
    """Hàm gửi request tự động bypass 403 Cloudflare trên GitHub Actions"""
    # 1. Thử gọi trực tiếp
    try:
        res = requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=8)
        if res.status_code == 200:
            return res.json()
        print(f"-> Gọi trực tiếp {url} nhận mã: {res.status_code}")
    except Exception as e:
        print(f"-> Lỗi gọi trực tiếp: {e}")

    # 2. Dự phòng 1: Chạy qua CORS Proxy để đổi IP Client
    proxy_url = f"https://corsproxy.io/?{url}"
    try:
        print("-> Đang thử vượt 403 qua CorsProxy...")
        res = requests.get(proxy_url, headers=HEADERS, impersonate="chrome120", timeout=12)
        if res.status_code == 200:
            print("-> Bypass 403 THÀNH CÔNG qua CorsProxy!")
            return res.json()
    except Exception as e:
        print(f"-> Lỗi CorsProxy: {e}")

    # 3. Dự phòng 2: Chạy qua AllOrigins Proxy
    encoded_url = urllib.parse.quote(url)
    proxy_url2 = f"https://api.allorigins.win/raw?url={encoded_url}"
    try:
        print("-> Đang thử vượt 403 qua AllOrigins Proxy...")
        res = requests.get(proxy_url2, headers=HEADERS, impersonate="chrome120", timeout=12)
        if res.status_code == 200:
            print("-> Bypass 403 THÀNH CÔNG qua AllOrigins!")
            return res.json()
    except Exception as e:
        print(f"-> Lỗi AllOrigins Proxy: {e}")

    return None

def get_match_ids_from_web():
    """Tải trang chủ lấy các Mongo ID trận đấu tươi mới nhất"""
    domain = "https://vip3.saoketv40.xyz/"
    ids = []
    try:
        print(f"[Bước 1/3] Quét ID trận đấu từ trang chủ ({domain})...")
        res = requests.get(domain, headers=HEADERS, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            found_ids = re.findall(r'[a-f0-9]{24}', res.text)
            ids = list(set(found_ids))
            print(f"-> Tìm thấy {len(ids)} ID trận đấu trên trang chủ.")
    except Exception as e:
        print(f"-> Lỗi quét trang chủ: {e}")
    return ids

def fetch_live_data(match_ids):
    """Lấy dữ liệu danh sách trận đấu từ API live-data"""
    test_ids = match_ids + [i for i in DEFAULT_MATCH_IDS if i not in match_ids]
    print(f"[Bước 2/3] Truy vấn API live-data với {len(test_ids)} ID...")

    for mid in test_ids:
        api_url = f"https://skapi.66887979.xyz/v2/saoke/live-data/{mid}?link=1"
        data = fetch_json_with_bypass(api_url)
        if data and data.get("data", {}).get("lives"):
            lives = data["data"]["lives"]
            print(f"-> THÀNH CÔNG! Lấy được mảng {len(lives)} trận từ API ID: {mid}")
            return data

    return None

def build_m3u(json_data):
    """Xuất danh sách m3u chuẩn định dạng hình mẫu"""
    m3u_lines = ["#EXTM3U x-tvg-url=\"\"\n\n"]
    
    if not json_data or "data" not in json_data or "lives" not in json_data["data"]:
        print("Dữ liệu JSON không chứa danh sách trận đấu.")
        return "".join(m3u_lines)

    lives = json_data["data"]["lives"]
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    for match in lives:
        time_ms = match.get("time", 0)
        match_dt = datetime.fromtimestamp(time_ms / 1000) if time_ms > 0 else now

        # Lọc các trận diễn ra trong ngày hôm nay và ngày mai
        if match_dt.date() not in [today, tomorrow]:
            continue

        time_str = match_dt.strftime("%H:%M %d/%m")
        team_a = match.get("teamA", {}).get("name", "Đội A")
        team_b = match.get("teamB", {}).get("name", "Đội B")
        logo_a = match.get("teamA", {}).get("picture", "")
        blv_name = match.get("blv", "BLV")

        # Lấy luồng HLS m3u8
        hls_list = match.get("hlsUrls", [])
        if not hls_list and "blvs" in match:
            for b in match.get("blvs", []):
                if b.get("hlsUrls"):
                    hls_list.extend(b["hlsUrls"])

        if not hls_list:
            continue

        match_count += 1

        for stream in hls_list:
            quality = stream.get("name", "HD")
            stream_url = stream.get("url", "")
            
            if not stream_url:
                continue

            # Định dạng: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [Quality]
            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name}) [{quality}]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV",{title}\n')
            m3u_lines.append(f'{stream_url}\n\n')
            stream_count += 1

    print(f"[Bước 3/3] Lọc {match_count} trận đấu -> Xuất {stream_count} luồng stream M3U thành công.")
    return "".join(m3u_lines)

def main():
    match_ids = get_match_ids_from_web()
    data = fetch_live_data(match_ids)
    
    if data:
        m3u_content = build_m3u(data)
        with open("saoketv.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print("-> CẬP NHẬT FILE saoketv.m3u THÀNH CÔNG!")
    else:
        print("-> LỖI: Không thể lấy dữ liệu từ hệ thống Sao Kê TV.")

if __name__ == "__main__":
    main()
    
