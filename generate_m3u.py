import requests
import json
from datetime import datetime, timedelta

# API danh sách trận đấu Sao Kê TV
BASE_API = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"
# Thông thường SaoKê TV lấy dữ liệu danh sách trận đấu qua endpoint JSON
MATCHES_API = "https://vip3.saoketv40.xyz/api/matches"  # Đổi theo endpoint JSON thực tế của web nếu có

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://vip3.saoketv40.xyz/"
}

def get_matches_data():
    try:
        response = requests.get(MATCHES_API, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Lỗi truy vấn API: {e}")
    return []

def format_m3u(matches):
    m3u_content = "#EXTM3U x-tvg-url=\"\"\n\n"
    
    # Lấy mốc thời gian hôm nay & ngày mai
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    for match in matches:
        # Giả định cấu trúc JSON từ API (Tùy chỉnh key tương ứng dữ liệu thực tế)
        timestamp = match.get("time_stamp", 0) # Epoch timestamp hoặc chuỗi ISO
        match_time = datetime.fromtimestamp(timestamp) if isinstance(timestamp, int) else now
        
        # Lọc trận đấu trong ngày hôm nay và ngày mai
        if match_time.date() not in [today, tomorrow]:
            continue

        team_a = match.get("home_team", "Đội nhà")
        team_b = match.get("away_team", "Đội khách")
        logo = match.get("home_logo", match.get("logo", ""))
        caster = match.get("commentator", "BLV")
        quality = match.get("quality", "hls")  # FHD, HD, SD, hls...
        stream_url = match.get("stream_url", "")

        if not stream_url:
            continue

        # Định dạng hiển thị đúng như hình mẫu: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [quality]
        time_str = match_time.strftime("%H:%M %d/%m")
        title = f"{time_str} ⚽ {team_a} vs {team_b} ({caster}) [{quality}]"

        m3u_content += f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV",{title}\n'
        m3u_content += f'{stream_url}\n\n'

    return m3u_content

def main():
    matches = get_matches_data()
    m3u_data = format_m3u(matches)
    
    with open("saoketv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_data)
    print("Đã cập nhật danh sách saoketv.m3u thành công!")

if __name__ == "__main__":
    main()

