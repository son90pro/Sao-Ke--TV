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
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": BASE_DOMAIN,
    "Referer": f"{BASE_DOMAIN}/"
}

def get_matches_from_api():
    """Thử gọi các endpoint danh sách trận đấu khác nhau của hệ thống"""
    endpoints = [
        f"{BASE_DOMAIN}/api/matches",
        f"{BASE_DOMAIN}/api/match/list",
        f"{BASE_DOMAIN}/api/matches/list",
        f"{BASE_DOMAIN}/api/home",
        f"{BASE_DOMAIN}/api/lives"
    ]
    
    for api in endpoints:
        try:
            print(f"Đang thử gọi API danh sách: {api}")
            res = requests.get(api, headers=HEADERS, impersonate="chrome120", timeout=8)
            if res.status_code == 200:
                data = res.json()
                # Trích xuất mảng trận đấu tùy theo cấu trúc JSON trả về
                matches = []
                if isinstance(data, list):
                    matches = data
                elif isinstance(data, dict):
                    matches = data.get("data", data.get("matches", data.get("list", [])))
                    if isinstance(matches, dict):
                        matches = matches.get("lives", matches.get("list", []))
                
                if matches and isinstance(matches, list):
                    print(f"-> Lấy thành công {len(matches)} trận từ API: {api}")
                    return matches
        except Exception as e:
            print(f"-> Lỗi khi gọi {api}: {e}")
            
    return []

def get_match_ids_from_web():
    """Quét mã ID trận đấu từ trang chủ nếu API list thay đổi cấu trúc"""
    match_ids = set()
    try:
        print(f"Đang quét trang chủ {BASE_DOMAIN} để tìm ID trận đấu...")
        res = requests.get(BASE_DOMAIN, headers=HEADERS, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            # Quét các đường dẫn dạng /matches/{id} hoặc ID 12-16 ký tự
            found_links = re.findall(r'/matches/([a-z0-9]+)', res.text)
            for lid in found_links:
                match_ids.add(lid)
            
            found_ids = re.findall(r'"id"\s*:\s*"([a-z0-9]{12,18})"', res.text)
            for fid in found_ids:
                match_ids.add(fid)
    except Exception as e:
        print(f"Lỗi quét trang chủ: {e}")
        
    # ID mẫu dự phòng nếu quét trắng
    if not match_ids:
        match_ids.add("1l4rjnh9nowpm7v")
        
    return list(match_ids)

def fetch_match_detail(match_id):
    """Gọi API chi tiết từng trận đấu"""
    detail_api = (
        f"{BASE_DOMAIN}/api/matches/{match_id}/?"
        "lang=vi&companyIds=2"
        "&returnList=info&returnList=livestreams&returnList=stats"
        "&returnList=asia&returnList=asiaHt&returnList=bs&returnList=bsHt"
        "&isIncludedRelation=true"
    )
    try:
        res = requests.get(detail_api, headers=HEADERS, impersonate="chrome120", timeout=6)
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

    # Bước 1: Thử lấy danh sách trận trực tiếp từ API list
    raw_matches = get_matches_from_api()
    
    match_items_to_process = []
    
    if raw_matches:
        for item in raw_matches:
            m_id = item.get("id") or item.get("matchId")
            if m_id:
                # Nếu API list đã có sẵn thông tin chi tiết, dùng luôn; nếu không gọi chi tiết
                if "info" in item and "livestreams" in item:
                    match_items_to_process.append(item)
                else:
                    detail = fetch_match_detail(m_id)
                    if detail and detail.get("success"):
                        match_items_to_process.append(detail.get("data", {}))
    else:
        # Bước 2: Nếu API list không trả về, quét qua danh sách ID trên trang chủ
        print("API list trống, chuyển sang quét chi tiết qua danh sách ID trang chủ...")
        match_ids = get_match_ids_from_web()
        print(f"Tìm thấy {len(match_ids)} ID trận đấu từ trang chủ.")
        for mid in match_ids:
            detail = fetch_match_detail(mid)
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
    
