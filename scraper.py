from datetime import datetime
import json
import requests


def fetch_saoke_data(api_url):
  """Gửi request lấy danh sách trận đấu từ API SaoKê."""
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          ' (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      ),
      'Origin': 'https://vip3.saoketv40.xyz',
      'Referer': 'https://saoke34.xyz/',
  }
  try:
    response = requests.get(api_url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get('data', {}).get('lives', [])
  except Exception as e:
    print(f'Lỗi khi kết nối API: {e}')
    return []


def generate_m3u(lives_list, live_only=False):
  """Chuyển đổi dữ liệu và xử lý toàn bộ lỗi hiển thị/phát video."""

  # --------------------------------------------------------------------------
  # KHẮC PHỤC YÊU CẦU 4: SẮP XẾP TRẬN ĐẤU THEO THỜI GIAN
  # Ưu tiên: Trận đang LIVE lên trước -> Các trận chưa đá xếp theo mốc thời gian tăng dần
  # --------------------------------------------------------------------------
  def get_sort_key(match):
    is_live = 0 if match.get('status') == 'live' else 1
    match_time = match.get('time', 0)
    return (is_live, match_time)

  lives_list.sort(key=get_sort_key)

  m3u_lines = ['#EXTM3U']

  # --------------------------------------------------------------------------
  # KHẮC PHỤC YÊU CẦU 3: KÈM HEADER USER-AGENT & REFERER ĐỂ KHÔNG BỊ CHẶN LUỒNG
  # Các app IPTV (TiviMate, OTT Navigator, VLC...) cần Referer này mới stream được HLS
  # --------------------------------------------------------------------------
  stream_headers = (
      '|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
      '&Referer=https://saoke34.xyz/'
  )

  for match in lives_list:
    status = match.get('status', '')
    if live_only and status != 'live':
      continue

    # Thông tin giải đấu & Đội bóng
    league_info = match.get('league', {})
    league_name = league_info.get('name', 'Bóng đá').strip()

    team_a_info = match.get('teamA', {})
    team_b_info = match.get('teamB', {})
    team_a = team_a_info.get('name', 'Đội A').strip()
    team_b = team_b_info.get('name', 'Đội B').strip()

    # --------------------------------------------------------------------------
    # KHẮC PHỤC YÊU CẦU 1: LẤY ĐÚNG LOGO ĐỘI BÓNG
    # Ưu tiên lấy Logo Đội nhà -> Đội khách -> Logo Giải đấu
    # --------------------------------------------------------------------------
    match_logo = (
        team_a_info.get('picture')
        or team_a_info.get('logo')
        or team_b_info.get('picture')
        or team_b_info.get('logo')
        or league_info.get('picture')
        or league_info.get('logo')
        or ''
    )

    # Thời gian trận đấu
    match_time_ms = match.get('time', 0)
    time_str = ''
    if match_time_ms:
      time_dt = datetime.fromtimestamp(match_time_ms / 1000)
      time_str = time_dt.strftime('%H:%M %d/%m')

    status_tag = '🔴 [LIVE]' if status == 'live' else f'⏰ [{time_str}]'

    # Lấy danh sách luồng phát
    streams = []
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
    else:
      blv_name = match.get('blv', '')
      for hls in match.get('hlsUrls', []):
        streams.append({
            'blv': blv_name,
            'quality': hls.get('name', 'HD'),
            'url': hls.get('url', ''),
        })

    seen_urls = set()
    for stream in streams:
      raw_url = stream['url']
      if not raw_url or raw_url in seen_urls:
        continue
      seen_urls.add(raw_url)

      # Nối chuỗi Headers chống Anti-Hotlink CDN
      playable_url = raw_url + stream_headers

      blv_tag = f" [BLV: {stream['blv']}]" if stream['blv'] else ''
      quality_tag = f" [{stream['quality']}]" if stream['quality'] else ''

      # --------------------------------------------------------------------------
      # KHẮC PHỤC YÊU CẦU 2: BỎ TÊN GIẢI ĐẤU LẪN LỘN TRONG TÊN TRẬN
      # Chỉ hiển thị: Trạng thái + Tên Đội A vs Đội B + BLV + Chất lượng
      # Tên giải đấu chỉ nằm ở cột Group danh mục (group-title)
      # --------------------------------------------------------------------------
      display_name = f'{status_tag} {team_a} vs {team_b}{blv_tag}{quality_tag}'

      extinf = (
          f'#EXTINF:-1 tvg-logo="{match_logo}" group-title="{league_name}",'
          f' {display_name}'
      )
      m3u_lines.append(extinf)
      m3u_lines.append(playable_url)

  return '\n'.join(m3u_lines)


if __name__ == '__main__':
  API_URL = (
      'https://skapi.66887979.xyz/v2/saoke/live-data/6abb8e323eba0388fc1f365a?link=1'
  )

  print('Đang tải dữ liệu từ API...')
  lives_data = fetch_saoke_data(API_URL)

  if lives_data:
    m3u_content = generate_m3u(lives_data)

    output_file = 'saoke_playlist.m3u'
    with open(output_file, 'w', encoding='utf-8') as f:
      f.write(m3u_content)

    print(f'✅ Tạo thành công file "{output_file}"!')
  else:
    print('❌ Không thể trích xuất dữ liệu.')
