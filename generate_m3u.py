from curl_cffi import requests
from datetime import datetime, timedelta
import re
import json

# API kiểm tra domain hoạt động của Sao Kê TV
CONFIG_API = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://vip3.saoketv40.xyz/",
    "Origin": "https://vip3.saoketv40.xyz"
}

def get_active_domain():
    try:
        res = requests.get(CONFIG_API, headers=HEADERS, impersonate="chrome120", timeout=10)
        print(f"[Bước 1/4] Lấy domain hệ thống - HTTP Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            domain = data.get("current", "https://vip3.saoketv40.xyz/").rstrip('/') + '/'
            print(f"-> Domain đang hoạt động: {domain}")
            return domain
    except Exception as e:
        print(f"-> Lỗi lấy config domain: {e}")
    return "https://vip3.saoketv40.xyz/"

def get_match_ids_from_web(domain):
    HEADERS["Referer"] = domain
    HEADERS["Origin"] = domain.rstrip('/')
    
    ids = []
    try:
        print(f"[Bước 2/4] Tải trang chủ ({domain}) để quét danh sách ID trận đấu...")
        res = requests.get(domain, headers=HEADERS, impersonate="chrome120", timeout=12)
        print(f"-> HTTP Status trang chủ: {res.status_code}")
        if res.status_code == 200:
            # Quét tất cả mã Mongo ID 24 ký tự hex trong mã nguồn web
            found_ids = re.findall(r'[a-f0-9]{24}', res.text)
            ids = list(set(found_ids))
            print(f"-> Tìm thấy {len(ids)} mã ID trận đấu trên trang chủ.")
    except Exception as e:
        print(f"-> Lỗi quét ID trang chủ: {e}")
    return ids

def fetch_live_data(domain, match_ids):
    # Kết hợp ID vừa quét được và các ID dự phòng phổ biến
    fallback_ids = ["6ac4d7b72454ab5c04d29b0c", "6ac5952bf54928d5ed64013e", "6ac4d7b72454ab5c04d29b10"]
    test_ids = match_ids + [i for i in fallback_ids if i not in match_ids]

    print(f"[Bước 3/4] Truy vấn API live-data với danh sách {len(test_ids)} ID...")

    for mid in test_ids:
        api_url = f"https://skapi.66887979.xyz/v2/saoke/live-data/{mid}?link=1"
        try:
            res = requests.get(api_url, headers=HEADERS, impersonate="chrome120", timeout=8)
            if res.status_code == 200:
                data = res.json()
                lives = data.get("data", {}).get("lives", [])
                if lives:
                    print(f"-> THÀNH CÔNG! Lấy thành công mảng {len(lives)} trận từ ID: {mid}")
                    return data
            else:
                print(f"-> Thử ID {mid} nhận mã phản hồi: {res.status_code}")
        except Exception as e:
            print(f"-> Lỗi gọi ID {mid}: {e}")

    return None

def build_m3u(json_data):
    m3u_lines = ["#EXTM3U x-tvg-url=\"\"\n\n"]
    
    if not json_data or "data" not in json_data or "lives" not in json_data["data"]:
        print("Dữ liệu JSON phản hồi không chứa dữ liệu trận đấu.")
        return "".join(m3u_lines)

    lives = json_data["data"]["lives"]
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    for match in lives:
        # Xử lý mốc thời gian trận đấu (Epoch milliseconds)
        time_ms = match.get("time", 0)
        match_dt = datetime.fromtimestamp(time_ms / 1000) if time_ms > 0 else now

        # Chỉ lọc lấy các trận diễn ra trong hôm nay và ngày mai
        if match_dt.date() not in [today, tomorrow]:
            continue

        time_str = match_dt.strftime("%H:%M %d/%m")
        team_a = match.get("teamA", {}).get("name", "Đội A")
        team_b = match.get("teamB", {}).get("name", "Đội B")
        logo_a = match.get("teamA", {}).get("picture", "")
        blv_name = match.get("blv", "BLV")

        # Lấy danh sách các luồng phát HLS
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

            # Hiển thị đúng định dạng hình mẫu: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [Quality]
            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name}) [{quality}]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV",{title}\n')
            m3u_lines.append(f'{stream_url}\n\n')
            stream_count += 1

    print(f"[Bước 4/4] Đã lọc {match_count} trận đấu hợp lệ -> Xuất {stream_count} luồng stream vào file M3U.")
    return "".join(m3u_lines)

def main():
    domain = get_active_domain()
    match_ids = get_match_ids_from_web(domain)
    data = fetch_live_data(domain, match_ids)
    
    if data:
        m3u_content = build_m3u(data)
        with open("saoketv.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print("-> ĐÃ CẬP NHẬT FILE saoketv.m3u THÀNH CÔNG!")
    else:
        print("-> RẤT TIẾC: Không thể lấy dữ liệu từ hệ thống Sao Kê TV.")

if __name__ == "__main__":
    main()
    
