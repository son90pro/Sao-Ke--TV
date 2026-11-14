import os
import re
import json
from datetime import datetime, timedelta, timezone
from curl_cffi import requests

# Khai báo múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Các domain API và trang chủ
HOME_DOMAIN = "https://vip5.saoketv40.xyz"
API_DOMAINS = [
    "https://skapi.66887979.xyz",
    "https://redirect-live.66887979.xyz"
]

# Danh sách ID trận đấu mẫu dự phòng mới nhất
DEFAULT_MATCH_IDS = [
    "6af5749a557c041f8f59a283",
    "6af5749a557c041f8f59a291",
    "6af667fff617d1cc4b47ed28",
    "6af5749a557c041f8f59a289",
    "6af6cd0bd8e709b6af895165",
    "6af6cd9155fc8f37f85be720",
    "6af6cd9155fc8f37f85be71d",
    "6af6cd0bd8e709b6af895184",
    "6af6cd9155fc8f37f85be71e",
    "6af6cd0bd8e709b6af895188",
    "6af6cd9155fc8f37f85be71f"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": HOME_DOMAIN,
    "Referer": f"{HOME_DOMAIN}/"
}

def get_match_ids_from_web():
    """Quét mã định danh Mongo ID 24 ký tự từ trang chủ mới"""
    match_ids = set(DEFAULT_MATCH_IDS)
    try:
        html_headers = HEADERS.copy()
        html_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        res = requests.get(HOME_DOMAIN, headers=html_headers, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            # Quét các chuỗi ID hex 24 ký tự đặc trưng của MongoDB
            found_ids = re.findall(r'[a-f0-9]{24}', res.text)
            for fid in found_ids:
                match_ids.add(fid)
    except Exception as e:
        print(f"Lỗi quét trang chủ: {e}")
        
    return list(match_ids)

def fetch_live_data(match_ids):
    """Truy vấn API live-data xoay vòng qua các domain để lấy danh sách trận đấu"""
    all_lives = []
    
    for mid in match_ids:
        success = False
        for api_domain in API_DOMAINS:
            api_url = f"{api_domain}/v2/saoke/live-data/{mid}?link=1"
            try:
                res = requests.get(api_url, headers=HEADERS, impersonate="chrome120", timeout=6)
                if res.status_code == 200:
                    data = res.json()
                    if not data.get("error"):
                        lives = data.get("data", {}).get("lives", [])
                        if lives:
                            all_lives.extend(lives)
                            success = True
                            break
            except Exception:
                continue
        if success:
            continue
            
    # Loại bỏ trùng lặp dựa trên _id của trận đấu
    unique_lives = {}
    for match in all_lives:
        m_id = match.get("_id")
        if m_id:
            unique_lives[m_id] = match
            
    return list(unique_lives.values())

def build_m3u():
    m3u_lines = ["#EXTM3U\n\n"]
    
    now_vn = datetime.now(VN_TZ)
    today = now_vn.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    match_ids = get_match_ids_from_web()
    print(f"Tổng số ID trận đấu tiến hành quét API: {len(match_ids)}")
    
    matches = fetch_live_data(match_ids)
    print(f"Tổng số trận đấu lấy được từ API: {len(matches)}")

    for match in matches:
        time_ms = match.get("time", 0)
        if time_ms > 0:
            
