from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

# API lấy domain hoạt động mới nhất của Sao Kê TV
CONFIG_API = "https://skapi.66887979.xyz/v2/web-list?url=saoketv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

def get_current_domain():
    try:
        res = requests.get(CONFIG_API, headers=HEADERS, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            data = res.json()
            domain = data.get("current", "https://vip3.saoketv40.xyz/")
            return domain.rstrip('/') + '/'
    except Exception as e:
        print(f"Lỗi lấy domain cấu hình: {e}")
    return "https://vip3.saoketv40.xyz/"

def fetch_html(url):
    try:
        # Dùng impersonate chrome120 để vượt qua Cloudflare 403 trên GitHub Actions
        response = requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
        print(f"HTTP Status Code trang chủ: {response.status_code}")
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Lỗi tải HTML trang chủ: {e}")
    return ""

def parse_matches(html):
    matches_list = []
    
    # Bóc tách mảng JSON trận đấu nhúng trong thẻ script __NEXT_DATA__
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1))
            page_props = data.get("props", {}).get("pageProps", {})
            raw_matches = page_props.get("matches", page_props.get("matchList", []))
            
            for item in raw_matches:
                matches_list.append({
                    "time": item.get("match_time_str", item.get("time", datetime.now().strftime("%H:%M %d/%m"))),
                    "home": item.get("home_name", item.get("home_team", "Đội nhà")),
                    "away": item.get("away_name", item.get("away_team", "Đội khách")),
                    "logo": item.get("home_logo", item.get("logo", "")),
                    "blv": item.get("commentator", item.get("blv", "BLV")),
                    "quality": item.get("quality", "hls"),
                    "url": item.get("play_url", item.get("stream_url", ""))
                })
            if matches_list:
                print(f"Trích xuất thành công {len(matches_list)} trận đấu từ JSON nhúng.")
                return matches_list
        except Exception as e:
            print(f"Lỗi parse NEXT_DATA: {e}")

    # Phương án dự phòng: Phân tích cú pháp DOM HTML bằng BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    match_items = soup.select(".match-item, .item-match, div[class*='match']")
    
    for item in match_items:
        try:
            home = item.select_one(".home-name, .team-home, .team-a")
            away = item.select_one(".away-name, .team-away, .team-b")
            time_el = item.select_one(".match-time, .time")
            blv_el = item.select_one(".blv-name, .commentator")
            logo_el = item.select_one("img")
            link_el = item.select_one("a[href*='xem']") or item

            if home and away:
                matches_list.append({
                    "time": time_el.get_text(strip=True) if time_el else datetime.now().strftime("%H:%M %d/%m"),
                    "home": home.get_text(strip=True),
                    "away": away.get_text(strip=True),
                    "logo": logo_el["src"] if logo_el and logo_el.has_attr("src") else "",
                    "blv": blv_el.get_text(strip=True) if blv_el else "BLV",
                    "quality": "hls",
                    "url": link_el.get("href", "")
                })
        except Exception:
            continue
            
    print(f"Trích xuất thành công {len(matches_list)} trận đấu từ DOM HTML.")
    return matches_list

def export_m3u(matches, domain):
    m3u = "#EXTM3U x-tvg-url=\"\"\n\n"
    for m in matches:
        if not m["home"] or not m["away"]:
            continue
            
        stream_url = m["url"]
        if stream_url and not stream_url.startswith("http"):
            stream_url = domain.rstrip('/') + '/' + stream_url.lstrip('/')

        # Hiển thị đúng định dạng: HH:MM DD/MM ⚽ TeamA vs TeamB (BLV) [hls]
        title = f"{m['time']} ⚽ {m['home']} vs {m['away']} ({m['blv']}) [{m['quality']}]"
        m3u += f'#EXTINF:-1 tvg-logo="{m["logo"]}" group-title="Sao Kê TV",{title}\n'
        m3u += f'{stream_url if stream_url else domain}\n\n'
    return m3u

def main():
    domain = get_current_domain()
    print(f"Đang kết nối: {domain}")
    html = fetch_html(domain)
    
    if html:
        matches = parse_matches(html)
        m3u_content = export_m3u(matches, domain)
        with open("saoketv.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print("Đã cập nhật file saoketv.m3u thành công!")
    else:
        print("Không tải được dữ liệu HTML trang chủ.")

if __name__ == "__main__":
    main()
    
