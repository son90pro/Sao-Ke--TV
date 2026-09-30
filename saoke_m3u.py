import requests
import json

# API chính xác lấy từ curl của anh
API_URL = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Android 16; Mobile; rv:156.0) Gecko/156.0 Firefox/156.0',
    'Referer': 'https://vip3.saoketv40.xyz/',
    'Origin': 'https://vip3.saoketv40.xyz'
}

def generate_m3u():
    m3u_lines = ["#EXTM3U\n"]
    
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Lấy danh sách các trận đấu từ JSON trả về
        matches = data.get('data', []) if isinstance(data, dict) else data
        if not isinstance(matches, list):
            matches = []

        for match in matches:
            # Bắt các trường dữ liệu thông dụng của API Sao Kê
            home_team = match.get('home_name') or match.get('home_team') or match.get('home') or ''
            away_team = match.get('away_name') or match.get('away_team') or match.get('away') or ''
            
            time_str = match.get('time') or match.get('match_time') or match.get('start_time') or ''
            date_str = match.get('date') or match.get('match_date') or ''
            
            blv = match.get('commentator') or match.get('blv') or match.get('author') or 'BLV'
            logo = match.get('home_logo') or match.get('logo') or match.get('league_logo') or ''
            
            # Đường dẫn luồng phát
            stream_url = match.get('play_url') or match.get('hls_url') or match.get('m3u8') or match.get('url') or ''
            
            # Xử lý tiêu đề hiển thị
            if home_team and away_team:
                match_title = f"{home_team} vs {away_team}"
            else:
                match_title = match.get('title') or match.get('name') or 'Trận đấu'

            time_prefix = f"{time_str} {date_str}".strip()
            if time_prefix:
                display_title = f"{time_prefix} ⚽ {match_title} ({blv}) [hls]"
            else:
                display_title = f"⚽ {match_title} ({blv}) [hls]"

            # Thêm vào file M3U nếu có link phát
            if stream_url:
                extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV", {display_title}'
                m3u_lines.append(extinf)
                m3u_lines.append(stream_url)
                
    except Exception as e:
        print(f"Lỗi khi tải API Sao Kê TV: {e}")

    # Ghi kết quả ra file saoke.m3u
    with open("saoke.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

if __name__ == "__main__":
    generate_m3u()
    
