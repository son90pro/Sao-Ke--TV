import re
import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://vip3.saoketv40.xyz/"
OUTPUT_FILE = "saoketv.m3u"

# Cấu hình Headers chuẩn theo lệnh curl của anh
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android 16; Mobile; rv:156.0) Gecko/156.0 Firefox/156.0",
    "Referer": "https://vip3.saoketv40.xyz/",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3",
}

def fetch_and_parse():
    try:
        # Gửi request với full header
        session = requests.Session()
        response = session.get(TARGET_URL, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"Lỗi HTTP {response.status_code} khi truy cập website!")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        m3u_lines = ["#EXTM3U\n"]
        
        # Bóc tách thẻ match/trận đấu
        match_items = soup.select('.list-match .item, .match-item, div[class*="match"], .card-match')
        
        if not match_items:
            # Fallback nếu không tìm thấy selector cụ thể
            match_items = soup.find_all('a', href=True)

        count = 0
        for item in match_items:
            title_el = item.select_one('.title, .match-name, .teams, .name, .team-name')
            time_el = item.select_one('.time, .match-time, .date')
            blv_el = item.select_one('.blv, .commentator, .author')
            
            # Lấy URL
            link_url = item['href'] if item.name == 'a' else None
            if not link_url:
                link_el = item.find('a', href=True)
                link_url = link_el['href'] if link_el else ""

            if title_el or (item.name == 'a' and 'vs' in item.text.lower()):
                title = title_el.text.strip() if title_el else item.text.strip()
                # Làm sạch chuỗi title
                title = re.sub(r'\s+', ' ', title)
                
                match_time = f" - {time_el.text.strip()}" if time_el else ""
                blv = f" (BLV {blv_el.text.strip()})" if blv_el else ""
                
                # Format lại URL stream / trang trận đấu
                if link_url.startswith('/'):
                    stream_url = f"https://vip3.saoketv40.xyz{link_url}"
                elif link_url.startswith('http'):
                    stream_url = link_url
                else:
                    stream_url = f"https://vip3.saoketv40.xyz/live/{link_url}/index.m3u8"

                # Phân loại nhóm thể thao
                group_title = "Bóng Đá"
                if "bóng chuyền" in title.lower() or "volleyball" in title.lower():
                    group_title = "Bóng Chuyền"
                elif "bóng rổ" in title.lower() or "basketball" in title.lower():
                    group_title = "Bóng Rổ"

                m3u_lines.append(f'#EXTINF:-1 group-title="{group_title}", {title}{match_time}{blv}')
                m3u_lines.append(f'{stream_url}\n')
                count += 1

        # Ghi file m3u
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
            
        print(f"Thành công! Đã ghi {count} trận đấu vào file {OUTPUT_FILE}")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    fetch_and_parse()
    
