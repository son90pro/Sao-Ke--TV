import requests
import json
import sys

API_URL = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://vip3.saoketv40.xyz/',
    'Origin': 'https://vip3.saoketv40.xyz',
    'Accept': 'application/json, text/plain, */*'
}

def generate_m3u():
    m3u_lines = ["#EXTM3U\n"]
    
    try:
        res = requests.get(API_URL, headers=HEADERS, timeout=15)
        print(f"--> Mã phản hồi HTTP: {res.status_code}")
        
        if res.status_code != 200:
            print(f"LỖI: Máy chủ trả về mã {res.status_code} (Có thể bị chặn IP)")
            print(f"Nội dung phản hồi: {res.text[:300]}")
        else:
            data = res.json()
            # Log xem cấu trúc dữ liệu trả về
            print("--> Cấu trúc dữ liệu nhận được (300 ký tự đầu):")
            print(json.dumps(data, ensure_ascii=False)[:300])

            # Tìm mảng danh sách trận đấu
            matches = []
            if isinstance(data, list):
                matches = data
            elif isinstance(data, dict):
                matches = data.get('data') or data.get('list') or data.get('rows') or data.get('result') or []
                if isinstance(matches, dict):
                    matches = matches.get('list') or matches.get('data') or []

            print(f"--> Tìm thấy {len(matches)} trận đấu")

            for item in matches:
                if not isinstance(item, dict):
                    continue

                # 1. Tên trận đấu / Tên đội
                home = item.get('home_name') or item.get('home_team') or item.get('home') or item.get('team_a') or ''
                away = item.get('away_name') or item.get('away_team') or item.get('away') or item.get('team_b') or ''
                title_raw = item.get('title') or item.get('name') or item.get('match_name') or ''
                
                if home and away:
                    match_name = f"{home} vs {away}"
                elif title_raw:
                    match_name = title_raw
                else:
                    match_name = "Trực tiếp Bóng Đá"

                # 2. Thời gian & Ngày
                time_str = str(item.get('time') or item.get('match_time') or item.get('start_time') or '')
                date_str = str(item.get('date') or item.get('match_date') or '')
                time_info = f"{time_str} {date_str}".strip()

                # 3. BLV & Logo
                blv = item.get('commentator') or item.get('blv') or item.get('author') or 'BLV'
                logo = item.get('home_logo') or item.get('logo') or item.get('thumb') or ''

                # 4. Tìm link stream (.m3u8 hoặc http)
                stream_url = ""
                possible_keys = ['play_url', 'hls_url', 'm3u8', 'url', 'stream_url', 'link', 'live_url']
                for k in possible_keys:
                    val = item.get(k)
                    if val and isinstance(val, str) and len(val) > 5:
                        stream_url = val
                        break

                # Xử lý nếu link nằm trong mảng danh sách kênh (links / channels)
                if not stream_url:
                    channels = item.get('links') or item.get('channels') or item.get('play_urls') or []
                    if isinstance(channels, list) and len(channels) > 0:
                        ch0 = channels[0]
                        if isinstance(ch0, dict):
                            stream_url = ch0.get('url') or ch0.get('play_url') or ch0.get('link') or ''
                        elif isinstance(ch0, str):
                            stream_url = ch0

                # Nếu có link thì ghi vào file
                if stream_url:
                    display_title = f"{time_info} ⚽ {match_name} ({blv}) [hls]" if time_info else f"⚽ {match_name} ({blv}) [hls]"
                    extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV", {display_title}'
                    m3u_lines.append(extinf)
                    m3u_lines.append(stream_url)

    except Exception as e:
        print(f"LỖI EXCEPTION: {e}")

    # Ghi file
    with open("saoke.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print(f"--> Hoàn tất! Đã ghi {len(m3u_lines)} dòng vào saoke.m3u")

if __name__ == "__main__":
    generate_m3u()
    
