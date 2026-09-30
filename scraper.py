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


def format_match_time(raw_time):
  """Chuyển đổi timestamp linh hoạt (cả 10 số và 13 số) sang chuỗi HH:MM DD/MM."""
  if not raw_time:
    return ''
  try:
    val = float(raw_time)
    # Nếu là timestamp mili-giây (13 chữ số) -> chuyển về giây
    if val > 1e11:
      val /= 1000.0
    dt = datetime.fromtimestamp(val)
    return dt.strftime('%H:%M %d/%m')
  except Exception:
    return str(raw_time)


def generate_m3u(lives_list, live_only=False):
  """Tạo danh sách M3U chuẩn hóa ngày giờ và tương thích luồng phát HD/SD."""

  # Sắp xếp: Trận Live lên đầu -> Các trận tiếp theo xếp theo thời gian tăng dần
  lives_list.sort(
      key=lambda x: (0 if x.get('status') == 'live' else 1, x.get('time', 0))
  )

  m3u_lines = ['#EXTM3U']

  # User-Agent & Referer chuẩn để mở khóa luồng HD trên CDN SaoKê
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

    # Logo đội bóng
    match_logo = (
        team_a_info.get('picture')
        or team_a_info.get('logo')
        or team_b_info.get('picture')
        or team_b_info.get('logo')
        or match.get('league', {}).get('picture', '')
    )

    # 1. FIX GIỜ VÀ NGÀY CHO CẢ TRẬN LIVE LẪN SẮP ĐÁ
    time_str = format_match_time(match.get('time'))
    if status == 'live':
      status_tag = (
          f'🔴 [LIVE {time_str}]' if time_str else '🔴 [LIVE]'
      )
    else:
      status_tag = f'⏰ [{time_str}]' if time_str else '⏰'

    # Thu thập danh sách luồng phát
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
          f' group-title="{league_name}",{display_name}'
      )

      # 2. FIX LUỒNG HD: GHI ĐÚNG CÚ PHÁP HEADER CHO TIVIMATE / OTT NAVIGATOR / VLC
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

  print('Đang lấy dữ liệu và khởi tạo file M3U...')
  lives_data = fetch_saoke_data(API_URL)

  if lives_data:
    m3u_content = generate_m3u(lives_data)
    output_file = 'saoke_playlist.m3u'
    with open(output_file, 'w', encoding='utf-8') as f:
      f.write(m3u_content)
    print(f'✅ Đã tạo thành công "{output_file}"!')
  else:
    print('❌ Lỗi không nhận được dữ liệu từ API.')
    
