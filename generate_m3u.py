from curl_cffi import requests
import json
import re
from datetime import datetime, timedelta

# API cấu hình gốc của Sao Kê TV
CONFIG_API = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"

# Danh sách các API trận đấu phổ biến của hệ thống Sao Kê TV
POSSIBLE_MATCH_APIS = [
    "https://skapi.66887979.xyz/v2/match/list",
    "https://skapi.66887979.xyz/v2/matches",
    "https://skapi.66887979.xyz/v1/match/list",
    "https://skapi.66887979.xyz/v2/live-list"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://vip3.saoketv40.xyz",
    "Referer": "https://vip3.saoketv40.xyz/"
}

def get_domain_and_api():
    current_domain = "https://vip3.saoketv40.xyz/"
    try:
        res = requests.get(CONFIG_API, headers=HEADERS, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            data = res.json()
            current_domain = data.get("current", current_domain)
            print(f"Domain hoạt động hiện tại: {current_domain}")
    except Exception as e:
        print(f"Không lấy được config domain, dùng mặc định: {e}")
    return current_domain

def fetch_matches_data(domain):
    HEADERS["Referer"] = domain
    HEADERS["Origin"] = domain.rstrip('/')

    # Cách 1: Thử các Endpoint API JSON trực tiếp
    for api_url in POSSIBLE_MATCH_APIS:
        try:
            res = requests.get(api_url, headers=HEADERS, impersonate="chrome120", timeout=8)
            if res.status_code == 200:
                try:
                    json_data = res.json()
                    if json_data and (isinstance(json_data, list) or "data" in json_data or "matches" in json_data):
                        print(f"Lấy thành công trận đấu từ API: {api_url}")
                        return json_data
                except Exception:
                    pass
        except Exception:
            continue

    # Cách 2: Tải HTML trang chủ và quét tìm link API ẩn trong file JS
    print("Đang quét tìm link API ẩn trong mã nguồn HTML...")
    try:
        html_res = requests.get(domain, headers=HEADERS, impersonate="chrome120", timeout=12)
        if html_res.status_code == 200:
            html = html_res.text
            
            # Tìm các đường dẫn API có dạng http... match hoặc list trong file JS
            found_urls = re.findall(r'https?://[^\s"\'<>]+(?:match|list|live)[^\s"\'<>]*', html)
            for url in set(found_urls):
                try:
                    res = requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=5)
                    if res.status_code == 200:
                        json_data = res.json()
                        if json_data:
                            print(f"Tìm thấy API trận đấu ẩn: {url}")
                            return json_data
                except Exception:
                    continue
    except Exception as e:
        print(f"Lỗi khi quét HTML: {e}")

    return None

def extract_match_list(data):
    if not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data", data.get("matches", data.get("list", [])))
    return []

def format_m3u(raw_matches, domain):
    m3u_content = "#EXTM3U x-tvg-url=\"\"\n\n"
    count = 0
    
    now = datetime.now()
    today_str = now.strftime("%d/%m")
    tomorrow_str = (now + timedelta(days=1)).strftime("%d/%m")

    for match in raw_matches:
        if not isinstance(match, dict):
            continue
            
        team_a = match.get("home_name", match.get("home_team", match.get("home", "")))
        team_b = match.get("away_name", match.get("away_team", match.get("away", "")))
        
        if not team_a or not team_b:
            continue

        logo = match.get("home_logo", match.get("logo", ""))
        caster = match.get("commentator", match.get("blv", match.get("caster", "BLV")))
        quality = match.get("quality", "hls")
        stream_url = match.get("play_url", match.get("stream_url", match.get("url", "")))
        
        # Xử lý thời gian
        time_str = match.get("match_time_str", match.get("time", ""))
        timestamp = match.get("match_time", match.get("timestamp", 0))
        
        if timestamp and isinstance(timestamp, (int, float)) and timestamp > 0:
            match_dt = datetime.fromtimestamp(timestamp)
            time_str = match_dt.strftime("%H:%M %d/%m")
        elif not time_str:
            time_str = now.strftime("%H:%M %d/%m")

        # Chuẩn hóa đường dẫn link phát
        if stream_url and not stream_url.startswith("http"):
            stream_url = domain.rstrip('/') + '/' + stream_url.lstrip('/')
        if not stream_url:
            stream_url = domain

        # Định dạng chuẩn: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [hls]
        title = f"{time_str} ⚽ {team_a} vs {team_b} ({caster}) [{quality}]"

        m3u_content += f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV",{title}\n'
        m3u_content += f'{stream_url}\n\n'
        count += 1

    print(f"Tổng số trận đấu xuất ra file M3U: {count}")
    return m3u_content

def main():
    domain = get_domain_and_api()
    data = fetch_matches_data(domain)
    matches = extract_match_list(data)
    
    m3u_content = format_m3u(matches, domain)
    
    with open("saoketv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print("Đã hoàn tất cập nhật saoketv.m3u!")

if __name__ == "__main__":
    main()
    
