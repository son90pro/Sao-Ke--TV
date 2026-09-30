import requests
import json
import re
from datetime import datetime

# Header giả lập trình duyệt để tránh bị chặn
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://saoke34.xyz/',
    'Origin': 'https://saoke34.xyz'
}

def get_saoke_matches():
    m3u_lines = ["#EXTM3U\n"]
    
    # Endpoint API của Sao Kê TV (trích xuất danh sách trận đấu)
    api_url = "https://vip3.saoketv40.xyz/api/match/list"  # Hoặc endpoint API match của web
    
    try:
        res = requests.get(api_url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            data = res.json()
            matches = data.get('data', [])
            
            for item in matches:
                # Trích xuất thông tin
                time_str = item.get('match_time', '00:00')   # Ví dụ: 01:45
                date_str = item.get('match_date', '30/09')   # Ví dụ: 30/09
                home_team = item.get('home_name', 'Đội nhà')
                away_team = item.get('away_name', 'Đội khách')
                blv_name = item.get('commentator', 'BLV')
                logo = item.get('home_logo') or item.get('league_logo') or ""
                stream_link = item.get('hls_url') or item.get('play_url') or ""
                
                # Định dạng tên hiển thị chuẩn theo mẫu
                title = f"{time_str} {date_str} ⚽ {home_team} vs {away_team} ({blv_name}) [hls]"
                
                if stream_link:
                    extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV", {title}'
                    m3u_lines.append(extinf)
                    m3u_lines.append(stream_link)
    except Exception as e:
        print(f"Lỗi khi tải dữ liệu: {e}")
        
    # Ghi ra file saoke.m3u
    with open("saoke.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

if __name__ == "__main__":
    get_saoke_matches()
  
