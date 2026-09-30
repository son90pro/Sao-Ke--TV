from datetime import datetime
import json
import requests


def fetch_saoke_data(api_url):
  """Gửi request lấy danh sách trận đấu từ API SaoKê."""
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          ' (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
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
    print(f'Lỗi kết nối API: {e}')
    return []


def generate_m3u(lives_list, live_only=False):
  """Tạo danh sách M3U chuẩn hóa giao diện và tương thích luồng phát HD/SD."""

  # Sắp xếp: Trận Live lên đầu -> Sắp xếp theo thứ tự thời gian tăng dần
  lives_list.sort(
      key=lambda x: (0 if x.get('status') == 'live' else 1, x.get('time', 0))
  )

  m3u_lines = ['#EXTM3U']

  # Cấu hình User-Agent và Referer chuẩn CDN SaoKê
  user_agent = (
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      ' (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
  )
  referer = 'https://saoke34.xyz/'

  for match in lives_list:
    status = match.get('status', '')
    if live_only and status != 'live':
      continue

    league_name = (
        match.get('league', {}).get('name', 'Bóng đá').strip()
    )
    team_a_info = match.get('teamA', {})
    team_b_info = match.get('teamB', {})
    team_a = team_a_info.get('name', 'Đội A').strip()
    team_b = team_b_info.get('name', 'Đội B').strip()

    # Lấy Logo Đội nhà -> Đội khách -> Logo Giải đấu
    match_logo = (
        team_a_info.get('picture')
        or team_a_info.get('logo')
        or team_b_info.get('picture')
        or team_b_info.get('logo')
        or match.get('league', {}).get('picture', '')
    )

    # --------------------------------------------------------------------------
    # FIX 1: BỔ SUNG NGÀY & GIỜ CHO CÁC TRẬN ĐANG LIVE
    # --------------------------------------------------------------------------
    match_time_ms = match.get('time', 0)
    time_str = ''
    if match_time_ms:
      time_dt = datetime.fromtimestamp(match_time_ms / 1000)
      time_str = time_dt.strftime('%H:%M %d/%m')

    if status == 'live':
      status_tag = (
          f'🔴 [LIVE {time_str}]' if time_str else '🔴 [LIVE]'
      )
    else:
      status_tag = f'⏰ [{time_str}]' if time_str else '⏰'

    # Thu thập danh sách luồng phát (HD / SD)
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

      blv_tag = f" [BLV: {stream['blv']}]" if stream['blv'] else ''
      quality_tag = f" [{stream['quality']}]" if stream['quality'] else ''
      display_name = (
          f'{status_tag} {team_a} vs {team_b}{blv_tag}{quality_tag}'
      )

      extinf = (
          f'#EXTINF:-1 tvg-logo="{match_logo}"'
          f' group-title="{league_name}", {display_name}'
      )

      # --------------------------------------------------------------------------
      # FIX 2: BỔ SUNG CÁC THẺ HEADER ĐỂ TRÌNH PHÁT BẰNG ĐƯỢC LUỒNG HD
      # --------------------------------------------------------------------------
      playable_url = f'{raw_url}|User-Agent={user_agent}&Referer={referer}'

      m3u_lines.append(extinf)
      m3u_lines.append(f'#EXTVLCOPT:http-user-agent={user_agent}')
      m3u_lines.append(f'#EXTVLCOPT:http-referrer={referer}')
      m3u_lines.append(playable_url)

  return '\n'.join(m3u_lines)


if __name__ == '__main__':
  API_URL = (
      'https://skapi.66887979.xyz/v2/saoke/live-data/6abb8e323eba0388fc1f365a?link=1'
  )

  print('Đang cập nhật danh sách...')
  lives_data = fetch_saoke_data(API_URL)

  if lives_data:
    m3u_content = generate_m3u(lives_data)
    output_file = 'saoke_playlist.m3u'
    with open(output_file, 'w', encoding='utf-8') as f:
      f.write(m3u_content)
    print(f'✅ Tạo thành công file "{output_file}"!')
  else:
    print('❌ Không lấy được dữ liệu API.')
    
