import os
import re
from datetime import datetime, timedelta, timezone
from curl_cffi import requests

# Khai báo múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

HOME_DOMAIN = "https://vip5.saoketv40.xyz"
API_DOMAINS = [
    "https://skapi.66887979.xyz",
    "https://redirect-live.66887979.xyz"
]

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
    match_ids = set(DEFAULT_MATCH_IDS)
    try:
        html_headers = HEADERS.copy()
        html_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        res = requests.get(HOME_DOMAIN, headers=html_headers, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            found_ids = re.findall(r'[a-f0-9]{24}', res.text)
            for fid in found_ids:
                match_ids.add(fid)
    except Exception as e:
        print(f"Lỗi quét trang chủ: {e}")
        
    return list(match_ids)

def fetch_live_data(match_ids):
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
    matches = fetch_live_data(match_ids)

    for match in matches:
        time_ms = match.get("time", 0)
        if time_ms > 0:
            match_dt_vn = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).astimezone(VN_TZ)
        else:
            match_dt_vn = now_vn

        # Lọc các trận diễn ra trong ngày hôm nay và ngày mai theo giờ Việt Nam (UTC+7)
        if match_dt_vn.date() not in [today, tomorrow]:
            continue

        time_str = match_dt_vn.strftime("%H:%M %d/%m")
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

        # Chỉ lọc lấy duy nhất luồng phát ổn định (ưu tiên hdplaylink / bỏ qua edgemaxcdn gây lỗi)
        valid_stream = None
        for stream in hls_list:
            url = stream.get("url", "")
            if "edgemaxcdn.org" not in url:
                valid_stream = stream
                break
        
        if not valid_stream and hls_list:
            valid_stream = hls_list[0]

        stream_url = valid_stream.get("url", "") if valid_stream else ""
        if not stream_url:
            continue

        match_count += 1
        title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name} - SD)"

        m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV" , {title}\n')
        m3u_lines.append(f'#EXTVLCOPT:http-referrer={HOME_DOMAIN}/\n')
        m3u_lines.append(f'{stream_url}\n\n')
        stream_count += 1

    print(f"Đã xử lý {match_count} trận đấu -> Xuất {stream_count} luồng phát ổn định tuyệt đối.")
    return "".join(m3u_lines)

def main():
    m3u_content = build_m3u()
    with open("saoketv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print("-> CẬP NHẬT FILE saoketv.m3u THÀNH CÔNG!")

if __name__ == "__main__":
    main()
    
