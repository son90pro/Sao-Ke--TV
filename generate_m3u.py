import os
import re
import json
from datetime import datetime, timedelta, timezone
from curl_cffi import requests

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Danh sách ID trận đấu mặc định
DEFAULT_MATCH_IDS = [
    "6ac5952bf54928d5ed64013e",
    "6ac4d7b72454ab5c04d29b0c",
    "6ac4d7b72454ab5c04d29b10",
    "6ac59574bf3ed6c99566dc1d"
]

# Các tên miền API của hệ thống Sao Kê TV
API_DOMAINS = [
    "https://skapi.66887979.xyz",
    "https://redirect-live.66887979.xyz"
]

# Danh sách dấu ấn trình duyệt để xoay vòng thử nghiệm
IMPERSONATE_TARGETS = ["chrome124", "chrome120", "safari15_5", "edge101"]

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

def get_match_ids_from_web():
    """Tải trang chủ lấy Mongo ID trận đấu mới nhất"""
    domain = "https://vip3.saoketv40.xyz/"
    ids = []
    for target in IMPERSONATE_TARGETS:
        try:
            res = requests.get(domain, headers=HEADERS, impersonate=target, timeout=6)
            if res.status_code == 200:
                found_ids = re.findall(r'[a-f0-9]{24}', res.text)
                ids = list(set(found_ids))
                if ids:
                    print(f"-> Quét thành công {len(ids)} ID trận đấu từ trang chủ ({target}).")
                    break
        except Exception:
            continue
    return ids

def fetch_live_data(match_ids):
    """Truy vấn API live-data xoay vòng qua các domain và target trình duyệt"""
    test_ids = match_ids + [i for i in DEFAULT_MATCH_IDS if i not in match_ids]

    for mid in test_ids:
        for api_domain in API_DOMAINS:
            api_url = f"{api_domain}/v2/saoke/live-data/{mid}?link=1"
            for target in IMPERSONATE_TARGETS:
                try:
                    res = requests.get(api_url, headers=HEADERS, impersonate=target, timeout=5)
                    if res.status_code == 200:
                        data = res.json()
                        if data and data.get("data", {}).get("lives"):
                            print(f"-> THÀNH CÔNG! Lấy dữ liệu trận đấu từ {api_domain} ({target})")
                            return data
                except Exception:
                    continue
    return None

def build_m3u(json_data):
    """Xuất danh sách m3u theo chuẩn múi giờ Việt Nam (UTC+7)"""
    m3u_lines = ["#EXTM3U x-tvg-url=\"\"\n\n"]
    
    if not json_data or "data" not in json_data or "lives" not in json_data["data"]:
        return "".join(m3u_lines)

    lives = json_data["data"]["lives"]
    now_vn = datetime.now(VN_TZ)
    today = now_vn.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    for match in lives:
        time_ms = match.get("time", 0)
        
        if time_ms > 0:
            match_dt = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).astimezone(VN_TZ)
        else:
            match_dt = now_vn

        # Lọc các trận đấu trong ngày hôm nay và ngày mai (giờ VN)
        if match_dt.date() not in [today, tomorrow]:
            continue

        time_str = match_dt.strftime("%H:%M %d/%m")
        team_a = match.get("teamA", {}).get("name", "Đội A")
        team_b = match.get("teamB", {}).get("name", "Đội B")
        logo_a = match.get("teamA", {}).get("picture", "")
        blv_name = match.get("blv", "BLV")

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

            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name}) [{quality}]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV",{title}\n')
            m3u_lines.append(f'{stream_url}\n\n')
            stream_count += 1

    print(f"Đã xử lý {match_count} trận đấu (Giờ VN) -> Xuất {stream_count} luồng stream M3U thành công.")
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
        print("-> CẢNH BÁO: Chưa lấy được dữ liệu từ API. Bảo toàn file saoketv.m3u cũ.")
        # Nếu chưa có file saoketv.m3u thì tạo file mặc định để không làm gãy bước Git Commit
        if not os.path.exists("saoketv.m3u"):
            with open("saoketv.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U x-tvg-url=\"\"\n")

if __name__ == "__main__":
    main()
    
