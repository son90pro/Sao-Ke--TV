import requests
import json
from datetime import datetime, timedelta

# API cấu hình domain & API lấy trận đấu thực tế của Sao Kê TV
CONFIG_API = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"
MATCHES_API = "https://skapi.66887979.xyz/v2/match/list"  # Cấu trúc API chính của hệ thống skapi

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://vip3.saoketv40.xyz",
    "Referer": "https://vip3.saoketv40.xyz/"
}

def get_matches_data():
    try:
        # Step 1: Lấy domain mới nhất từ skapi
        config_res = requests.get(CONFIG_API, headers=HEADERS, timeout=10)
        if config_res.status_code == 200:
            config_json = config_res.json()
            current_domain = config_json.get("current", "https://vip3.saoketv40.xyz/")
            HEADERS["Referer"] = current_domain
            HEADERS["Origin"] = current_domain.rstrip('/')
            print(f"Domain hiện tại: {current_domain}")

        # Step 2: Gọi API lấy danh sách trận đấu
        response = requests.get(MATCHES_API, headers=HEADERS, timeout=10)
        print(f"HTTP Status Code API trận đấu: {response.status_code}")

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Server trả về lỗi {response.status_code}. Nội dung: {response.text[:200]}")
            
    except requests.exceptions.JSONDecodeError:
        print("Lỗi JSONDecodeError: Server trả về HTML thay vì JSON (Do bị Cloudflare block IP GitHub hoặc sai URL API).")
        if 'response' in locals():
            print(f"Nội dung phản hồi từ Server: {response.text[:300]}")
    except Exception as e:
        print(f"Lỗi truy vấn API: {e}")
    return None

def format_m3u(data):
    m3u_content = "#EXTM3U x-tvg-url=\"\"\n\n"
    
    if not data or not isinstance(data, dict):
        print("Không có dữ liệu trận đấu hợp lệ.")
        return m3u_content

    # Lấy danh sách trận đấu tùy theo cấu trúc JSON trả về (data hoặc list)
    matches = data.get("data", []) if isinstance(data, dict) else []

    for match in matches:
        # Bóc tách các trường từ API
        team_a = match.get("home_name", match.get("home_team", "Đội nhà"))
        team_b = match.get("away_name", match.get("away_team", "Đội khách"))
        logo = match.get("home_logo", match.get("logo", ""))
        caster = match.get("commentator", match.get("blv", "BLV"))
        quality = match.get("quality", "hls")
        
        # Lấy link stream (ưu tiên hls / m3u8)
        stream_url = match.get("play_url", match.get("stream_url", ""))
        
        # Xử lý thời gian
        timestamp = match.get("match_time", match.get("time_stamp", 0))
        if isinstance(timestamp, int) and timestamp > 0:
            match_dt = datetime.fromtimestamp(timestamp)
            time_str = match_dt.strftime("%H:%M %d/%m")
        else:
            time_str = datetime.now().strftime("%H:%M %d/%m")

        if not stream_url:
            continue

        # Định dạng chuẩn theo hình mẫu: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [quality]
        title = f"{time_str} ⚽ {team_a} vs {team_b} ({caster}) [{quality}]"

        m3u_content += f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV",{title}\n'
        m3u_content += f'{stream_url}\n\n'

    return m3u_content

def main():
    data = get_matches_data()
    if data:
        m3u_data = format_m3u(data)
        with open("saoketv.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_data)
        print("Đã cập nhật danh sách saoketv.m3u thành công!")
    else:
        print("Không thể khởi tạo saoketv.m3u do lỗi lấy dữ liệu.")

if __name__ == "__main__":
    main()
    
