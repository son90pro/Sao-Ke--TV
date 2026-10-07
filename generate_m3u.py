from curl_cffi import requests
from datetime import datetime, timedelta
import re
import json

# API chính chứa dữ liệu danh sách trận đấu
PRIMARY_API = "https://skapi.66887979.xyz/v2/saoke/live-data/6ac5952bf54928d5ed64013e?link=1"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://vip3.saoketv40.xyz/"
}

def fetch_live_data():
    # Bước 1: Thử gọi API trực tiếp
    try:
        res = requests.get(PRIMARY_API, headers=HEADERS, impersonate="chrome120", timeout=12)
        if res.status_code == 200:
            json_data = res.json()
            if json_data.get("data", {}).get("lives"):
                print("Lấy thành công dữ liệu trận đấu từ API chính.")
                return json_data
    except Exception as e:
        print(f"Lỗi API chính: {e}")

    # Bước 2: Dự phòng nếu ID cố định bị hết hạn -> Lấy match ID mới từ trang chủ
    print("Đang quét ID trận đấu mới từ trang chủ Sao Kê TV...")
    try:
        html_res = requests.get("https://vip3.saoketv40.xyz/", headers=HEADERS, impersonate="chrome120", timeout=10)
        if html_res.status_code == 200:
            match_ids = re.findall(r'[a-f0-9]{24}', html_res.text)
            for match_id in set(match_ids):
                fallback_url = f"https://skapi.66887979.xyz/v2/saoke/live-data/{match_id}?link=1"
                res = requests.get(fallback_url, headers=HEADERS, impersonate="chrome120", timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("data", {}).get("lives"):
                        print(f"Lấy thành công dữ liệu từ API dự phòng với ID: {match_id}")
                        return data
    except Exception as e:
        print(f"Lỗi quét ID dự phòng: {e}")
        
    return None

def build_m3u(json_data):
    m3u_lines = ["#EXTM3U x-tvg-url=\"\"\n\n"]
    
    if not json_data or "data" not in json_data or "lives" not in json_data["data"]:
        print("Dữ liệu JSON không hợp lệ hoặc thiếu mảng 'lives'.")
        return "".join(m3u_lines)

    lives = json_data["data"]["lives"]
    print(f"Tổng số trận đấu tìm thấy: {len(lives)}")

    # Thời gian lọc: Hôm nay & Ngày mai
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    match_count = 0
    stream_count = 0

    for match in lives:
        # Lấy thời gian (Epoch timestamp tính bằng ms)
        time_ms = match.get("time", 0)
        match_dt = datetime.fromtimestamp(time_ms / 1000) if time_ms > 0 else now

        # Chỉ lấy trận đấu diễn ra hôm nay và ngày mai
        if match_dt.date() not in [today, tomorrow]:
            continue

        time_str = match_dt.strftime("%H:%M %d/%m")
        team_a = match.get("teamA", {}).get("name", "Đội A")
        team_b = match.get("teamB", {}).get("name", "Đội B")
        logo_a = match.get("teamA", {}).get("picture", "")
        blv_name = match.get("blv", "BLV")

        # Thu thập danh sách các luồng phát HLS (SD, HD, FHD,...)
        hls_list = match.get("hlsUrls", [])
        if not hls_list and "blvs" in match:
            for b in match.get("blvs", []):
                if b.get("hlsUrls"):
                    hls_list.extend(b["hlsUrls"])

        if not hls_list:
            continue

        match_count += 1

        # Tạo từng dòng kênh theo từng chất lượng luồng (SD / HD / FHD...)
        for stream in hls_list:
            quality = stream.get("name", "HD")
            stream_url = stream.get("url", "")
            
            if not stream_url:
                continue

            # Định dạng đúng hình mẫu: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [Quality]
            title = f"{time_str} ⚽ {team_a} vs {team_b} ({blv_name}) [{quality}]"

            m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_a}" group-title="Sao Kê TV",{title}\n')
            m3u_lines.append(f'{stream_url}\n\n')
            stream_count += 1

    print(f"Đã xử lý {match_count} trận đấu hợp lệ -> Xuất ra {stream_count} luồng phát M3U.")
    return "".join(m3u_lines)

def main():
    data = fetch_live_data()
    if data:
        m3u_content = build_m3u(data)
        with open("saoketv.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print("Đã cập nhật file saoketv.m3u thành công!")
    else:
        print("Không thể lấy dữ liệu từ API Sao Kê TV.")

if __name__ == "__main__":
    main()
    
