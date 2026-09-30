from datetime import datetime
import json
import requests


def fetch_saoke_data(api_url):
  """Gửi request tới API SaoKe để lấy danh sách trận đấu."""
  headers = {
      'accept': 'application/json',
      'user-agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          ' (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      ),
      'origin': 'https://vip3.saoketv40.xyz',
      'referer': 'https://saoke34.xyz/',
  }

  try:
    response = requests.get(api_url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get('data', {}).get('lives', [])
  except Exception as e:
    print(f'Lỗi khi kết nối API: {e}')
    return []


def generate_m3u(lives_list, live_only=False, preferred_quality='HD'):
  """Chuyển đổi dữ liệu trận đấu thành định dạng playlist M3U."""
  m3u_lines = ['#EXTM3U']

  for match in lives_list:
    status = match.get('status', '')

    # Nếu tùy chọn live_only=True, chỉ lấy các trận đang phát (status == 'live')
    if live_only and status != 'live':
      continue

    # Thông tin cơ bản
    league_info = match.get('league', {})
    league_name = league_info.get('name', 'Bóng đá')
    league_logo = league_info.get('picture', '')

    team_a = match.get('teamA', {}).get('name', '')
    team_b = match.get('teamB', {}).get('name', '')

    # Thời gian trận đấu
    match_time_ms = match.get('time', 0)
    time_str = ''
    if match_time_ms:
      time_dt = datetime.fromtimestamp(match_time_ms / 1000)
      time_str = time_dt.strftime('%H:%M %d/%m')

    # Tiền tố trạng thái trận đấu
    status_tag = '🔴 [LIVE]' if status == 'live' else f'⏰ [{time_str}]'

    # Thu thập danh sách link phát sóng
    streams = []

    # 1. Ưu tiên lấy link từ danh sách Bình luận viên (blvs)
    blvs = match.get('blvs', [])
    if blvs:
      for blv_item in blvs:
        blv_name = blv_item.get('name', '')
        for hls in blv_item.get('hlsUrls', []):
          streams.append({
              'blv': blv_name,
              'quality': hls.get('name', 'HD'),
              'url': hls.get('url', ''),
          })
    # 2. Nếu không có danh sách blvs, lấy từ hlsUrls trực tiếp
    else:
      blv_name = match.get('blv', '')
      for hls in match.get('hlsUrls', []):
        streams.append({
            'blv': blv_name,
            'quality': hls.get('name', 'HD'),
            'url': hls.get('url', ''),
        })

    # Lọc bớt trùng lặp URL
    seen_urls = set()

    for stream in streams:
      url = stream['url']
      if not url or url in seen_urls:
        continue
      seen_urls.add(url)

      blv_tag = f" [BLV: {stream['blv']}]" if stream['blv'] else ''
      quality_tag = f" [{stream['quality']}]" if stream['quality'] else ''

      # Tên hiển thị Kênh
      display_name = (
          f'{status_tag} {team_a} vs {team_b} -'
          f' {league_name}{blv_tag}{quality_tag}'
      )

      # Định dạng dòng #EXTINF trong file M3U
      extinf = (
          f'#EXTINF:-1 tvg-logo="{league_logo}" group-title="{league_name}",'
          f' {display_name}'
      )

      m3u_lines.append(extinf)
      m3u_lines.append(url)

  return '\n'.join(m3u_lines)


# --- CHƯƠNG TRÌNH CHÍNH ---
if __name__ == '__main__':
  # URL API Saoke (có thể thay đổi ID hoặc endpoint chính)
  API_URL = (
      'https://skapi.66887979.xyz/v2/saoke/live-data/6abb8e323eba0388fc1f365a?link=1'
  )

  print('Đang lấy danh sách trận đấu từ API...')
  lives = fetch_saoke_data(API_URL)

  if lives:
    # live_only=False: Lấy tất cả trận (Live & Sắp diễn ra)
    # live_only=True: Chỉ lấy các trận đang phát Live
    m3u_content = generate_m3u(lives, live_only=False)

    # Lưu kết quả ra file saoke_playlist.m3u
    output_file = 'saoke_playlist.m3u'
    with open(output_file, 'w', encoding='utf-8') as f:
      f.write(m3u_content)

    print(
        f'✅ Đã tạo thành công file "{output_file}" với {len(lives)} trận'
        ' đấu.'
    )
  else:
    print('❌ Không tìm thấy dữ liệu trận đấu hoặc gặp lỗi kết nối.')
      
