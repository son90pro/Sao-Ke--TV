from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import requests

# Định nghĩa múi giờ chuẩn Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like'
    ' Gecko) Chrome/124.0.0.0 Safari/537.36'
)
REFERER = 'https://saoke34.xyz/'
ORIGIN = 'https://saoke34.xyz'


def fetch_saoke_data(api_url):
  """Gửi request lấy danh sách trận đấu từ API SaoKê."""
  headers = {
      'User-Agent': USER_AGENT,
      'Origin': ORIGIN,
      'Referer': REFERER,
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
  """Chuyển đổi timestamp chuẩn về Giờ Việt Nam (UTC+7)."""
  if not raw_time:
    return ''
  try:
    val = float(raw_time)
    if val > 1e11:
      val /= 1000.0
    dt = datetime.fromtimestamp(val, tz=timezone.utc).astimezone(VN_TZ)
    return dt.strftime('%H:%M %d/%m')
  except Exception:
    return str(raw_time)


def resolve_direct_url(raw_url):
  """Giải mã bóc tách URL CDN trực tiếp để tránh trình phát bị mất Header khi 302 Redirect."""
  if not raw_url:
    return raw_url

  headers = {
      'User-Agent': USER_AGENT,
      'Referer': REFERER,
      'Origin': ORIGIN,
  }

  try:
    # Lấy liên kết CDN cuối cùng sau chuyển hướng
    res = requests.head(
        raw_url, headers=headers, allow_redirects=True, timeout=4
    )
    if res.status_code == 200 and res.url:
      return res.url
  except Exception:
    pass
  return raw_url


def process_stream_urls(streams):
  """Sử dụng đa luồng để xử lý nhanh toàn bộ link stream."""
  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(resolve_direct_url, s['url']): s for s in streams
    }
    for future in futures:
      stream = futures[future]
      try:
        stream['direct_url'] = future.result()
      except Exception:
        stream['direct_url'] = stream['url']
  return streams


def generate_m3u(lives_list, live_only=False):
  """Tạo danh sách M3U chuẩn hóa ngày giờ Việt Nam và tương thích hoàn hảo với OTT Navigator."""

  lives_list.sort(
      key=lambda x: (0 if x.get('status') == 'live' else 1, x.get('time', 0))
  )

  m3u_lines = ['#EXTM3U']

  # Cấu hình JSON Header chuẩn cho OTT Navigator / TiviMate
  exthttp_tag = json.dumps(
      {'User-Agent': USER_AGENT, 'Referer': REFERER, 'Origin': ORIGIN}
  )

  for match in lives_list:
    status = match.get('status', '')
    if live_only and status != 'live':
      continue

    league_name = match.get('league', {}).get('name', 'Bóng đá').strip()
    team_a_info = match.get('teamA', {})
    team_b_info = match.get('teamB', {})
    team_a = team_a_info.get('name', 'Đội A').strip()
    team_b = team_b_info.get('name', 'Đội B').strip()

    match_logo = (
        team_a_info.get('picture')
        or team_a_info.get('logo')
        or team_b_info.get('picture')
        or team_b_info.get('logo')
        or match.get('league', {}).get('picture', '')
    )

    time_str = format_match_time(match.get('time'))
    if status == 'live':
      status_tag = f'🔴 [LIVE {time_str}]' if time_str else '🔴 [LIVE]'
    else:
      status_tag = f'⏰ [{time_str}]' if time_str else '⏰'

    raw_streams = []
    blvs = match.get('blvs', [])
    if blvs:
      for blv_item in blvs:
        blv_name = blv_item.get('name', '')
        for hls in blv_item.get('hlsUrls', []):
          raw_streams.append({
              'blv': blv_name,
              'quality': hls.get('name', 'HD'),
              'url': hls.get('url', ''),
          })
    else:
      blv_name = match.get('blv', '')
      for hls in match.get('hlsUrls', []):
        raw_streams.append({
            'blv': blv_name,
            'quality': hls.get('name', 'HD'),
            'url': hls.get('url', ''),
        })

    # Xử lý bóc tách link trực tiếp
    streams = process_stream_urls(raw_streams)

    seen_urls = set()
    for stream in streams:
      direct_url = stream.get('direct_url') or stream['url']
      if not direct_url or direct_url in seen_urls:
        continue
      seen_urls.add(direct_url)

      blv_tag = f" [BLV: {stream['blv']}]" if stream['blv'] else ''
      quality_tag = f" [{stream['quality']}]" if stream['quality'] else ''
      display_name = (
          f'{status_tag} {team_a} vs {team_b}{blv_tag}{quality_tag}'
      )

      extinf = (
          f'#EXTINF:-1 tvg-logo="{match_logo}"'
          f' group-title="{league_name}",{display_name}'
      )

      # Định dạng chuỗi Pipe chứa đầy đủ các tham số Header
      playable_url = (
          f'{direct_url}|User-Agent={USER_AGENT}&Referer={REFERER}&Origin={ORIGIN}'
      )

      # Thẻ cấu hình Header chuẩn cho từng trình phát
      m3u_lines.append(f'#EXTHTTP:{exthttp_tag}')
      m3u_lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')
      m3u_lines.append(f'#EXTVLCOPT:http-referrer={REFERER}')
      m3u_lines.append(extinf)
      m3u_lines.append(playable_url)

  return '\n'.join(m3u_lines)


if __name__ == '__main__':
  API_URL = (
      'https://skapi.66887979.xyz/v2/saoke/live-data/6abb8e323eba0388fc1f365a?link=1'
  )

  print('Đang xử lý dữ liệu và tạo file M3U tối ưu...')
  lives_data = fetch_saoke_data(API_URL)

  m3u_content = generate_m3u(lives_data) if lives_data else '#EXTM3U\n'

  output_file = 'saoke_playlist.m3u'
  with open(output_file, 'w', encoding='utf-8') as f:
    f.write(m3u_content)

  if lives_data:
    print(f'✅ Tạo thành công file "{output_file}"!')
  else:
    print(f'⚠️ Không có dữ liệu API, đã xuất file "{output_file}" rỗng.')
    
