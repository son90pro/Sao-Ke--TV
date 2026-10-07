import os
import re
import json
from datetime import datetime, timedelta, timezone
from curl_cffi import requests

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

DEFAULT_MATCH_IDS = [
    "6ac5952bf54928d5ed64013e",
    "6ac4d7b72454ab5c04d29b0c",
    "6ac4d7b72454ab5c04d29b10",
    "6ac59574bf3ed6c99566dc1d"
]

API_DOMAINS = [
    "https://skapi.66887979.xyz",
    "https://redirect-live.66887979.xyz"
]

IMPERSONATE_TARGETS = ["chrome124", "chrome120", "safari15_5", "edge101"]

REFERER_URL = "https://vip3.saoketv40.xyz/"
USER_AGENT_STR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": USER_AGENT_STR,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://vip3.saoketv40.xyz",
    "Referer": REFERER_URL
}

def get_match_ids_from_web():
    domain = "https://vip3.saoketv40.xyz/"
    ids = []
    for target in IMPERSONATE_TARGETS:
        try:
            res = requests.get(domain, headers=HEADERS, impersonate=target, timeout=6)
            if res.status_code == 200:
                found_ids = re.findall(r'[a-f0-9]{24}', res.text)
                ids = list(set(found_ids))
                if ids:
                    break
        except Exception:
            continue
    return ids

def fetch_live_data(match_ids):
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
                            return data
                except Exception:
                    continue
    return None

def process_stream_url(raw_url):
    """Chuyển đổi link HD edgemaxcdn sang CDN gateway 100ycdn"""
    if not raw_url:
        return ""
        
    url = raw_url.strip()
    
    if "edgemaxcdn.org" in url and "100ycdn.com" not in url:
        clean_path = url.replace("https://", "").replace("http://", "")
        url = f"https://100ycdn.com/{clean_path}"
        
    return url

def build_m3u(json_data):
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

        # Sắp xếp SD lên đầu (luồng ổn định không dính token CDN), HD xếp sau
        sorted_hls = sorted(hls_list, key=lambda x: 0 if x.get("name") == "SD" else 1)

        for stream in sorted_hls:
            quality = stream.get("name", "HD")
            raw_url = stream.get("url", "")
            
            if not raw_url:
                continue

            processed_url = process_stream_url(raw_url)
            final_stream_url = f"{processed_url}|Referer={REFERER_URL}&User-Agent={USER_AGENT_STR}"

            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name}) [{quality}]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV",{title}\n')
            m3u_lines.append(f'#EXTVLCOPT:http-referrer={REFERER_URL}\n')
            m3u_lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT_STR}\n')
            m3u_lines.append(f'{final_stream_url}\n\n')
            stream_count += 1

    print(f"Đã xử lý {match_count} trận đấu -> Xuất {stream_count} luồng M3U.")
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
        if not os.path.exists("saoketv.m3u"):
            with open("saoketv.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U x-tvg-url=\"\"\n")

if __name__ == "__main__":
    main()
    
