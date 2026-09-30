import re
import requests
from bs4 import BeautifulSoup

# URL trang web cần lấy dữ liệu
TARGET_URL = "https://vip3.saoketv40.xyz/"
OUTPUT_FILE = "saoketv.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def fetch_and_parse():
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        m3u_lines = ["#EXTM3U\n"]
        
        # Bóc tách danh sách các trận đấu từ DOM
        # Điều chỉnh selector theo cấu trúc HTML thực tế của trang
        match_items = soup.select('.list-match .item, .match-item, div[class*="match"]')
        
        for item in match_items:
            title_el = item.select_one('.title, .match-name, .teams, .name')
            time_el = item.select_one('.time, .match-time')
            blv_el = item.select_one('.blv, .commentator')
            link_el = item.find('a', href=True)
            
            if title_el:
                title = title_el.text.strip()
                match_time = f" - {time_el.text.strip()}" if time_el else ""
                blv = f" (BLV {blv_el.text.strip()})" if blv_el else ""
                
                # Xác định link luồng phát (.m3u8 hoặc URL chi tiết)
                stream_url = link_el['href'] if link_elem else TARGET_URL
                if stream_url.startswith('/'):
                    stream_url = f"https://vip3.saoketv40.xyz{stream_url}"
                elif not stream_url.startswith('http'):
                    stream_url = f"https://vip3.saoketv40.xyz/live/{stream_url}/index.m3u8"

                # Phân loại nhóm thể thao
                group_title = "Bóng Đá"
                if "volleyball" in title.lower() or "bóng chuyền" in title.lower():
                    group_title = "Bóng Chuyền"

                # Thêm dòng EXTINF
                m3u_lines.append(f'#EXTINF:-1 group-title="{group_title}", {title}{match_time}{blv}')
                m3u_lines.append(f'{stream_url}\n')

        # Ghi nội dung ra tệp .m3u
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
            
        print(f"Cập nhật thành công {len(match_items)} trận đấu vào {OUTPUT_FILE}")

    except Exception as e:
        print(f"Lỗi trong quá trình cập nhật: {e}")

if __name__ == "__main__":
    fetch_and_parse()
    
