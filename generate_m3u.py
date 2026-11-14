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
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_DOMAIN,
    "Referer": f"{BASE_DOMAIN}/",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty"
}

def fetch_matches_from_api():
    """Gọi API danh sách trận đấu sử dụng params chuẩn hóa tự động"""
    now_vn = datetime.now(VN_TZ)
    
    from_str = (now_vn - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00+07:00")
    to_str = (now_vn + timedelta(days=3)).strftime("%Y-%m-%dT23:59:59+07:00")

    api_url = f"{BASE_DOMAIN}/api/matches/"
    
    # Sử dụng danh sách tuple để hỗ trợ các tham số trùng lặp (nhiều statuses, returnList)
    params = [
        ("lang", "vi"),
        ("returnList", "info"),
        ("returnList", "livestreams"),
        ("isIncludedRelation", "true"),
        ("sortMatchTime", "asc"),
        ("fromDate", from_str),
        ("toDate", to_str),
        ("statuses", "LIVE"),
        ("statuses", "UPCOMING"),
        ("livestreamsStatuses", "LIVE"),
        ("livestreamsStatuses", "UPCOMING"),
        ("companyIds", "2"),
        ("page", "1"),
        ("limit", "100")
    ]
    
    try:
        print(f"Đang gọi API từ {from_str} đến {to_str}")
        res = requests.get(api_url, params=params, headers=HEADERS, impersonate="chrome120", timeout=12)
        print(f"HTTP Status Code: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            matches = data.get("data", {}).get("matches", [])
            print(f"-> Lấy thành công {len(matches)} trận đấu từ API.")
            return matches, data
        else:
            print(f"Phản hồi thô khi lỗi: {res.text[:300]}")
    except Exception as e:
        print(f"Lỗi gọi API matches: {e}")
        
    return [], {}

def build_m3u():
    m3u_lines = ["#EXTM3U\n\n"]
    
    now_vn = datetime.now(VN_TZ)
    today = now_vn.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    matches, raw_json = fetch_matches_from_api()
    
    relation = raw_json.get("data", {}).get("relation", {})
    teams_list = relation.get("teams", [])
    team_map = {t["id"]: t for t in teams_list}

    for item in matches:
        info = item.get("info", {})
        livestreams = item.get("livestreams", {})
        
        match_time_str = info.get("matchTime")
        if not match_time_str:
            continue

        try:
            match_dt_vn = datetime.fromisoformat(match_time_str)
        except Exception:
            try:
                match_dt_utc = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                match_dt_vn = match_dt_utc.astimezone(VN_TZ)
            except Exception:
                continue

        # Lọc các trận diễn ra trong ngày hôm nay và ngày mai theo giờ Việt Nam (UTC+7)
        if match_dt_vn.date() not in [today, tomorrow]:
            continue

        time_str = match_dt_vn.strftime("%H:%M %d/%m")

        home_id = info.get("homeTeamId")
        away_id = info.get("awayTeamId")
        
        home_team = team_map.get(home_id, {})
        away_team = team_map.get(away_id, {})
        
        team_a_name = home_team.get("name") or info.get("homeTeamName", "Đội nhà")
        team_b_name = away_team.get("name") or info.get("awayTeamName", "Đội khách")
        logo = home_team.get("logo") or info.get("homeTeamLogo", "")

        links = livestreams.get("links", [])
        if not links:
            continue

        match_count += 1

        for idx, link_info in enumerate(links):
            commentator = link_info.get("commentator", "BLV")
            stream_url = link_info.get("linkHls") or link_info.get("url")
            if not stream_url:
                continue

            # Đồng bộ định dạng chuẩn mẫu user đang chạy
            title = f"{time_str} ⚽ {team_a_name} vs {team_b_name} ({commentator}) [hls]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV" , {title}\n')
            m3u_lines.append(f'#EXTVLCOPT:http-referrer={BASE_DOMAIN}/\n')
            m3u_lines.append(f'{stream_url}\n\n')
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
    
