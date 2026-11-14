import os
from datetime import datetime, timedelta, timezone
from curl_cffi import requests

# Khai báo múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))
BASE_DOMAIN = "https://live.tamilians.in"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": BASE_DOMAIN,
    "Referer": f"{BASE_DOMAIN}/"
}

def fetch_matches_from_api():
    """Gọi trực tiếp API danh sách trận đấu với dải thời gian linh hoạt"""
    now_vn = datetime.now(VN_TZ)
    from_date = (now_vn - timedelta(days=1)).strftime("%Y-%m-%dT00%3A00%3A00%2B07%3A00")
    to_date = (now_vn + timedelta(days=2)).strftime("%Y-%m-%dT23%3A59%3A59%2B07%3A00")

    api_url = (
        f"{BASE_DOMAIN}/api/matches/?lang=vi"
        "&returnList=info&returnList=livestreams"
        "&isIncludedRelation=true&sortMatchTime=asc"
        f"&fromDate={from_date}&toDate={to_date}"
        "&statuses=LIVE&statuses=UPCOMING"
        "&livestreamsStatuses=LIVE&livestreamsStatuses=UPCOMING"
        "&page=1&limit=100"
    )
    
    try:
        print(f"Đang gọi API danh sách trận đấu: {api_url}")
        res = requests.get(api_url, headers=HEADERS, impersonate="chrome120", timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                matches = data.get("data", {}).get("matches", [])
                print(f"-> Lấy thành công {len(matches)} trận đấu từ API.")
                return matches
    except Exception as e:
        print(f"Lỗi gọi API matches: {e}")
        
    return []

def build_m3u():
    m3u_lines = ["#EXTM3U x-tvg-url=\"\"\n\n"]
    
    now_vn = datetime.now(VN_TZ)
    today = now_vn.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    matches = fetch_match_from_api_wrapper = fetch_matches_from_api()

    for item in matches:
        info = item.get("info", {})
        livestreams = item.get("livestreams", {})
        
        match_time_str = info.get("matchTime")
        if not match_time_str:
            continue

        try:
            # Parse thời gian chuẩn từ API (e.g. 2026-11-15T21:00:00+07:00)
            match_dt_vn = datetime.fromisoformat(match_time_str)
        except Exception:
            try:
                match_dt_utc = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                match_dt_vn = match_dt_utc.astimezone(VN_TZ)
            except Exception:
                continue

        # Lọc các trận diễn ra trong ngày hôm nay và ngày mai theo múi giờ Việt Nam (UTC+7)
        if match_dt_vn.date() not in [today, tomorrow]:
            continue

        time_str = match_dt_vn.strftime("%H:%M %d/%m")

        # Lấy tên đội bóng từ info hoặc giả lập nếu thiếu
        team_a_name = info.get("homeTeamName", "Đội nhà")
        team_b_name = info.get("awayTeamName", "Đội khách")
        logo = info.get("homeTeamLogo", "")

        links = livestreams.get("links", [])
        if not links:
            continue

        match_count += 1

        for idx, link_info in enumerate(links):
            commentator = link_info.get("commentator", "BLV")
            stream_url = link_info.get("linkHls") or link_info.get("url")
            if not stream_url:
                continue

            quality = "HD" if idx == 0 else f"SD{idx}"
            title = f"{time_str} ⚽ {team_a_name} vs {team_b_name} ({commentator}) [{quality}]"

            final_url = f"{stream_url}|Referer={BASE_DOMAIN}/&User-Agent={HEADERS['User-Agent']}"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV",{title}\n')
            m3u_lines.append(f'#EXTVLCOPT:http-referrer={BASE_DOMAIN}/\n')
            m3u_lines.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n')
            m3u_lines.append(f'{final_url}\n\n')
            stream_count += 1

    print(f"Đã xử lý {match_count} trận đấu -> Xuất {stream_count} luồng M3U thành công.")
    return "".join(m3u_lines)

def main():
    m3u_content = build_m3u()
    with open("saoketv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print("-> CẬP NHẬT FILE saoketv.m3u THÀNH CÔNG!")

if __name__ == "__main__":
    main()
    
