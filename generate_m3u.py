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
            
            # Quét thêm các slug html để lấy link chi tiết trận
            slugs = re.findall(r'href="/([a-z0-9-]+-([a-f0-9]{24})\.html)"', res.text)
            for full_slug, m_id in slugs:
                match_ids.add(m_id)
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

def get_tokenized_streams(slug):
    """Truy cập trang chi tiết trận đấu để bóc tách link HLS có gắn token động thực tế"""
    if not slug:
        return []
    
    page_url = f"{HOME_DOMAIN}/{slug}.html"
    html_headers = HEADERS.copy()
    html_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    
    try:
        res = requests.get(page_url, headers=html_headers, impersonate="chrome120", timeout=8)
        if res.status_code == 200:
            # Quét các đường dẫn m3u8 có chứa token 100ycdn hoặc mediastation
            found_hls = re.findall(r'(https://[^\s<>"]+?playlist\.m3u8[^\s<>"]*?)["\']', res.text)
            return list(set(found_hls))
    except Exception:
        pass
    return []

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
        slug = match.get("slug")

        # Thử quét link token động từ trang html chi tiết
        tokenized_links = get_tokenized_streams(slug)

        hls_list = match.get("hlsUrls", [])
        if not hls_list and "blvs" in match:
            for b in match.get("blvs", []):
                if b.get("hlsUrls"):
                    hls_list.extend(b["hlsUrls"])

        if not hls_list and not tokenized_links:
            continue

        match_count += 1

        # Xử lý đưa các luồng vào M3U (cả SD và HD)
        processed_urls = set()

        # 1. Ưu tiên đưa các link token động quét được từ trang web vào trước (đảm bảo luồng HD sống)
        for t_url in tokenized_links:
            if t_url in processed_urls:
                continue
            processed_urls.add(t_url)
            
            quality = "HD" if "edgemax" in t_url or "100ycdn" in t_url else "SD"
            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name} - {quality}) [hls]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV" , {title}\n')
            m3u_lines.append(f'#EXTVLCOPT:http-referrer={HOME_DOMAIN}/\n')
            m3u_lines.append(f'{t_url}\n\n')
            stream_count += 1

        # 2. Đưa các link từ API chuẩn (SD / HD dự phòng)
        for stream in hls_list:
            stream_url = stream.get("url", "")
            quality = stream.get("name", "SD").upper()
            
            if not stream_url or stream_url in processed_urls:
                continue
            processed_urls.add(stream_url)

            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name} - {quality}) [hls]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV" , {title}\n')
            m3u_lines.append(f'#EXTVLCOPT:http-referrer={HOME_DOMAIN}/\n')
            m3u_lines.append(f'{stream_url}\n\n')
            stream_count += 1

    print(f"Đã xử lý {match_count} trận đấu -> Xuất tổng cộng {stream_count} luồng (Đã bao gồm SD và HD có token).")
    return "".join(m3u_lines)

def main():
    m3u_content = build_m3u()
    with open("saoketv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print("-> CẬP NHẬT FILE saoketv.m3u THÀNH CÔNG!")

if __name__ == "__main__":
    main()
    
