from datetime import datetime, timezone, timedelta
import requests

API_URL = "https://skapi.66887979.xyz/v2/saoke/live-data/6abb8e323eba0388fc1f365a?link=1"
OUTPUT_FILE = "saoketv.m3u"

HEADERS = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def format_match_time(ts_ms):
    if not ts_ms:
        return ""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone(timedelta(hours=7)))
    return dt.strftime("%H:%M %d/%m")

def fetch_lives():
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("error") and "data" in data and "lives" in data["data"]:
            return data["data"]["lives"]
    except Exception as e:
        print(f"Lỗi kết nối API: {e}")
    return []

def generate_m3u(lives):
    m3u_lines = ["#EXTM3U"]

    if not lives:
        # Tự động tạo dòng ghi chú nếu không có trận đấu nào
        m3u_lines.append('#EXTINF:-1 tvg-logo="" group-title="Sao Kê TV",Hệ thống đang cập nhật trận đấu...')
        m3u_lines.append('https://0.0.0.0/live.m3u8')
    else:
        for match in lives:
            time_str = format_match_time(match.get("time"))
            team_a = match.get("teamA", {}).get("name", "")
            team_b = match.get("teamB", {}).get("name", "")
            logo = match.get("teamA", {}).get("picture") or match.get("league", {}).get("picture", "")
            match_title = f"{team_a} vs {team_b}" if team_a and team_b else match.get("title", "")

            blvs = match.get("blvs", [])
            if blvs:
                for blv in blvs:
                    blv_name = blv.get("name") or match.get("blv") or "SaoKe"
                    for stream in blv.get("hlsUrls", []):
                        url = stream.get("url")
                        quality = stream.get("name", "hls").lower()
                        if url:
                            display_name = f"{time_str} ⚽ {match_title} ({blv_name}) [{quality}]"
                            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV",{display_name}')
                            m3u_lines.append(url)
            else:
                fallback_blv = match.get("blv", "SaoKe")
                for stream in match.get("hlsUrls", []):
                    url = stream.get("url")
                    quality = stream.get("name", "hls").lower()
                    if url:
                        display_name = f"{time_str} ⚽ {match_title} ({fallback_blv}) [{quality}]"
                        m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Sao Kê TV",{display_name}')
                        m3u_lines.append(url)

    # Đảm bảo file saoketv.m3u luôn luôn được ghi thành công
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"Đã cập nhật file '{OUTPUT_FILE}' thành công.")

if __name__ == "__main__":
    matches = fetch_lives()
    generate_m3u(matches) # Luôn thực thi hàm tạo file
