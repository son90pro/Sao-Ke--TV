from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import requests

# Cấu hình múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Thông tin cấu hình Domain & Headers mới
DOMAIN = 'https://vip3.saoketv40.xyz/'
ORIGIN = 'https://vip3.saoketv40.xyz'
REFERER = 'https://vip3.saoketv40.xyz/'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like'
    ' Gecko) Chrome/128.0.0.0 Safari/537.36'
)

# API Sao Kê TV mới
API_URL = (
    'https://skapi.66887979.xyz/v2/saoke/live-data/6abd5e2cad19d495b20de551?link=1'
)


def fetch_saoke_data():
  """Lấy danh sách các trận đấu từ API Sao Kê TV."""
  headers = {
      'User-Agent': USER_AGENT,
      'Origin': ORIGIN,
      'Referer': REFERER,
      'Accept': 'application/json',
  }
  try:
    response = requests.get(API_URL, headers=headers, timeout=12)
    response.raise_for_status()
    result = response.json()
    if not result.get('error', True):
      return result.get('data', {}).get('lives', [])
  except Exception as e:
    print(f'❌ Lỗi khi tải dữ liệu từ API: {e}')
  return []


def format_match_time(timestamp_ms):
  """Chuyển đổi timestamp (ms) sang dạng HH:MM DD/MM giờ Việt Nam."""
  if not timestamp_ms:
    return ''
  try:
    ts = float(timestamp_ms) / 1000.0
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(VN_TZ)
    return dt.strftime('%H:%M %d/%m')
  except Exception:
    return ''


def resolve_direct_url(raw_url):
  """Bóc tách link CDN trực tiếp để tránh trình phát TV bị lỗi 403 khi Redirect (302)."""
  if not raw_url:
    return raw_url

  headers = {
      'User-Agent': USER_AGENT,
      'Referer': REFERER,
      'Origin': ORIGIN,
  }

  try:
    res = requests.head(
        raw_url, headers=headers, allow_redirects=True, timeout=4
    )
    if res.status_code == 200 and res.url:
      return res.url
  except Exception:
    pass
  return raw_url


def process_stream_urls(streams):
  """Xử lý đa luồng bóc tách URL CDN nhanh chóng."""
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


def generate_m3u(lives_list):
  """Tạo nội dung M3U hiển thị đúng chuẩn hình mẫu (TG, Đội bóng, BLV, Chất lượng)."""
  m3u_lines = ['#EXTM3U']

  # Cấu hình JSON Header chuẩn cho OTT Navigator / TiviMate
  exthttp_tag = json.dumps(
      {'User-Agent': USER_AGENT, 'Referer': REFERER, 'Origin': ORIGIN}
  )

  # Sắp xếp: Trận đang Live lên đầu, sau đó sắp theo thời gian
  lives_list.sort(
      key=lambda x: (0 if x.get('status') == 'live' else 1, x.get('time', 0))
  )

  for match in lives_list:
    status = match.get('status', 'upcoming')
    time_str = format_match_time(match.get('time'))

    # Ký hiệu trạng thái giống giao diện mẫu trong hình
    status_icon = '🟢' if status == 'live' else '🟡'

    team_a = match.get('teamA', {}).get('name', 'Đội A').strip()
    team_b = match.get('teamB', {}).get('name', 'Đội B').strip()

    # Logo đội bóng (Ưu tiên Logo Đội A hoặc Đội B)
    match_logo = match.get('teamA', {}).get('picture') or match.get(
        'teamB', {}
    ).get('picture', '')

    # Thu thập luồng phát (HLS)
    raw_streams = []
    blvs = match.get('blvs', [])

    if blvs:
      for blv_item in blvs:
        blv_name = blv_item.get('name', '')
        for hls in blv_item.get('hlsUrls', []):
          if hls.get('url'):
            raw_streams.append({
                'blv': blv_name,
                'quality': hls.get('name', 'HD'),
                'url': hls.get('url'),
            })
    else:
      blv_name = match.get('blv', '')
      for hls in match.get('hlsUrls', []):
        if hls.get('url'):
          raw_streams.append({
              'blv': blv_name,
              'quality': hls.get('name', 'HD'),
              'url': hls.get('url'),
          })

    # Nếu chưa có luồng phát active (ví dụ trận sắp diễn ra), bỏ qua
    if not raw_streams:
      continue

    # Giải mã link trực tiếp
    streams = process_stream_urls(raw_streams)

    seen_urls = set()
    for stream in streams:
      direct_url = stream.get('direct_url') or stream['url']
      if not direct_url or direct_url in seen_urls:
        continue
      seen_urls.add(direct_url)

      blv_part = f" ({stream['blv']})" if stream['blv'] else ''
      quality_part = f" [{stream['quality']}]" if stream['quality'] else ''

      # Định dạng tên hiển thị chuẩn theo hình mẫu: 🟢 06:00 01/10 ⚽ Argentina vs Bolivia (Bút Chì) [HD]
      display_name = f'{status_icon} {time_str} ⚽ {team_a} vs {team_b}{blv_part}{quality_part}'

      # Nhóm kênh đặt tên "Sao Kê TV" đúng như cột danh mục bên trái ảnh mẫu
      extinf = (
          f'#EXTINF:-1 tvg-logo="{match_logo}" group-title="Sao Kê'
          f' TV",{display_name}'
      )

      # Định dạng chuỗi Pipe truyền Headers đầy đủ
      playable_url = (
          f'{direct_url}|User-Agent={USER_AGENT}&Referer={REFERER}&Origin={ORIGIN}'
      )

      m3u_lines.append(f'#EXTHTTP:{exthttp_tag}')
      m3u_lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')
      m3u_lines.append(f'#EXTVLCOPT:http-referrer={REFERER}')
      m3u_lines.append(extinf)
      m3u_lines.append(playable_url)

  return '\n'.join(m3u_lines)


if __name__ == '__main__':
  print('🔄 Đang lấy dữ liệu trận đấu từ vip3.saoketv40.xyz...')
  lives = fetch_saoke_data()

  print(f'📊 Tìm thấy {len(lives)} trận đấu. Đang tạo file M3U...')
  m3u_content = generate_m3u(lives)

  output_filename = 'saoketv.m3u'
  with open(output_filename, 'w', encoding='utf-8') as f:
    f.write(m3u_content)

  print(f'✅ Đã xuất thành công file danh sách phát: {output_filename}')
    
