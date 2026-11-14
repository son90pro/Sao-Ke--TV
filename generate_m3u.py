import os
import re
import json
from datetime import datetime, timedelta, timezone
from curl_cffi import requests

# Khai báo múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))
BASE_DOMAIN = "https://live.tamilians.in"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": BASE_DOMAIN,
    "Referer": f"{BASE_DOMAIN}/"
}

def get_matches_from_next_data():
    """Trích xuất danh sách trận đấu trực tiếp từ JSON nhúng __NEXT_DATA__ của trang chủ"""
    match_items = []
    try:
        print(f"Đang tải trang chủ {BASE_DOMAIN} để bóc tách dữ liệu...")
        res = requests.get(BASE_DOMAIN, headers=HEADERS, impersonate="chrome120", timeout=12)
        if res.status_code == 200:
            # Tìm thẻ chứa __NEXT_DATA__
            next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
            if next_data_match:
                json_raw = json.loads(next_data_match.group(1))
                # Điều hướng sâu vào cấu trúc props của Next.js để tìm danh sách trận
                page_props = json_raw.get("props", {}).get("pageProps", {})
                
                # Quét tất cả các key có thể chứa danh sách trận đấu
                for key in ["matches", "matchList", "list", "data", "lives", "initialState"]:
                    val = page_props.get(key)
                    if isinstance(val, list) and len(val) > 0:
                        match_items.extend(val)
                    elif isinstance(val, dict):
                        for sub_k, sub_v in val.items():
                            if isinstance(sub_v, list) and len(sub_v) > 0:
                                match_items.extend(sub_v)
                                
                print(f"-> Tìm thấy {len(match_items)} trận từ __NEXT_DATA__.")
                
            # Nếu không tìm thấy qua Next data, quét toàn bộ các ID dạng chuỗi 15-18 ký tự
            if not match_items:
                found_ids = set(re.findall(r'"id"\s*:\s*"([a-z0-9]{12,18})"', res.text))
                print(f"-> Quét được {len(found_ids)} ID tiềm năng từ HTML.")
                for mid in found_ids:
                    detail = fetch_match_detail(mid)
                    if detail and detail.get("success"):
                        match_items.append(detail.get("data", {}))
                        
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu trang chủ: {e}")
        
    return match_items

def fetch_match_detail(match_id):
    """Gọi API chi tiết từng trận đấu"""
    detail_api = (
        f"{BASE_DOMAIN}/api/matches/{match_id}/?"
        "lang=vi&companyIds=2"
        "&returnList=info&returnList=livestreams&returnList=stats"
        "&returnList=asia&returnList=asiaHt&returnList=bs&returnList=bsHt"
        "&isIncludedRelation=true"
    )
    headers_api = HEADERS.copy()
    headers_api["Accept"] = "application/json, text/plain, */*"
    try:
        res = requests.get(detail_api, headers=headers_api, impersonate="chrome120", timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def build_m3u():
    m3u_lines = ["#EXTM3U x-tvg-url=\"\"\n\n"]
    
    now_vn = datetime.now(VN_TZ)
    today = now_vn.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    raw_items = get_matches_from_next_data()
    match_items_to_process = []

    for item in raw_items:
        # Nếu item đã có cấu trúc info & livestreams
        if isinstance(item, dict) and "info" in item and "livestreams" in item:
            match_items_to_process.append(item)
        else:
            m_id = item.get("id") or item.get("matchId")
            if m_id:
                detail = fetch_match_detail(m_id)
                if detail and detail.get("success"):
                    match_items_to_process.append(detail.get("data", {}))

    print(f"Tổng số trận đấu chuẩn bị xử lý: {len(match_items_to_process)}")

    for data in match_items_to_process:
        info = data.get("info", {})
        relation = data.get("relation", {})
        livestreams = data.get("livestreams", {})

        match_time_str = info.get("matchTime")
        if not match_time_str:
            continue

        try:
            match_dt_utc = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
            match_dt_vn = match_dt_utc.astimezone(VN_TZ)
        except Exception:
            continue

        # Lọc các trận diễn ra trong ngày hôm nay và ngày mai theo giờ Việt Nam (UTC+7)
        if match_dt_vn.date() not in [today, tomorrow]:
            continue

        time_str = match_dt_vn.strftime("%H:%M %d/%m")

        # Ánh xạ thông tin đội bóng và logo
        teams = relation.get("teams", [])
        team_map = {t["id"]: t for t in teams}
        
        home_team = team_map.get(info.get("homeTeamId"), {})
        away_team = team_map.get(info.get("awayTeamId"), {})
        
        team_a_name = home_team.get("name", "Đội nhà")
        team_b_name = away_team.get("name", "Đội khách")
        logo = home_team.get("logo", "")

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
    
