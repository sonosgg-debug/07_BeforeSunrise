import os
import sys
import re
import json
import time
import zipfile
import io
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import requests
import pytz
import pandas as pd
import yfinance as yf
from PIL import Image, ImageDraw, ImageFont

# Load environment variables from .env located in the same directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

OUTPUT_DIR = os.path.join(BASE_DIR, "DailyData")
os.makedirs(OUTPUT_DIR, exist_ok=True)
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)


# ==============================================================================
# 1. KIS (한국투자증권) API Helper Functions
# ==============================================================================

def get_kis_token_status() -> dict:
    """공용 KIS 토큰(kis_token.json) 유효성 및 만료 시간 확인 (독자 발급 0건 원칙)"""
    import time
    now_ts = time.time()

    candidates = [
        os.getenv("KIS_TOKEN_FILE"),
        "/home/ubuntu/apps/kis_token.json",
        os.path.join(os.path.dirname(BASE_DIR), "00 API Key", "kis_token.json"),
        r"D:\AI Investing\00 API Key\kis_token.json",
        os.path.join(BASE_DIR, "kis_token.json")
    ]

    for c in candidates:
        if c and os.path.exists(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    tok = json.load(f)
                exp = tok.get("expires_at", 0)
                if tok.get("access_token") and exp > now_ts + 60:
                    exp_dt = datetime.fromtimestamp(exp)
                    iss_dt = datetime.fromtimestamp(tok.get("issued_at", exp - 86400))
                    return {
                        "connected": True,
                        "file": c,
                        "token": tok.get("access_token"),
                        "expires_at": exp_dt.strftime("%Y-%m-%d %H:%M"),
                        "issued_at": iss_dt.strftime("%Y-%m-%d %H:%M"),
                        "expires_at_kst": tok.get("expires_at_kst", exp_dt.strftime("%Y-%m-%d %H:%M")),
                        "issued_at_kst": tok.get("issued_at_kst", iss_dt.strftime("%Y-%m-%d %H:%M"))
                    }
            except Exception as e:
                print(f"[KIS] Token cache read error from {c}: {e}")

    return {"connected": False, "file": None, "token": None, "expires_at": None, "issued_at": None}


def get_kis_access_token() -> str:
    """공용 KIS OAuth 토큰 문자열 반환 (중복 발급 원천 차단)"""
    status = get_kis_token_status()
    if status.get("connected"):
        return status.get("token")
    print("[KIS] Warning: No valid shared KIS token found. (Expected from 00 Bookmarks central token manager)")
    return None


def _load_kis_credentials():
    """KIS AppKey 및 AppSecret 자동 로드 (보조 폴백)"""
    if not os.getenv("KIS_APP_KEY") or not os.getenv("KIS_APP_SECRET"):
        parent_dir = Path(BASE_DIR).parent
        candidates = [
            parent_dir / "00 API Key" / "한국투자증권 API_kis.txt",
            Path(r"D:\AI Investing\00 API Key\한국투자증권 API_kis.txt"),
            parent_dir / "00 API Key" / ".env",
            Path("/home/ubuntu/apps/.env")
        ]
        for c in candidates:
            if c.exists():
                try:
                    with open(c, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if "=" in line and not line.startswith("#"):
                                k, v = line.split("=", 1)
                                k, v = k.strip().upper(), v.strip()
                                if k in ("KIS_APP_KEY", "APP_KEY", "APPKEY"):
                                    os.environ["KIS_APP_KEY"] = v
                                elif k in ("KIS_APP_SECRET", "APP_SECRET", "APPSECRET"):
                                    os.environ["KIS_APP_SECRET"] = v
                    if os.getenv("KIS_APP_KEY") and os.getenv("KIS_APP_SECRET"):
                        break
                except Exception:
                    pass


def get_recent_kospi200_futures_code():
    """Download KIS futures master file and detect the front-month KOSPI200 futures code."""
    url = 'https://new.real.download.dws.co.kr/common/master/fo_idx_code_mts.mst.zip'
    try:
        req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        req.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(req.content)) as z:
            with z.open(z.namelist()[0]) as f:
                for line in f:
                    decoded = line.decode('cp949', errors='ignore').strip()
                    parts = decoded.split('|')
                    # format: 1|A01612|KR4A016C0004|F 202612| |00000.00|1|2001|KOSPI200
                    if len(parts) >= 8 and parts[0] == '1' and parts[6] == '1' and parts[7] == '2001':
                        return parts[1]
    except Exception as e:
        print(f"[KIS] Failed to get master file: {e}")

    # Fallback: estimate front-month code from current year and month
    now = datetime.now()
    year_digit = str(now.year)[-1]
    # KOSPI 200 futures expire in Mar(03), Jun(06), Sep(09), Dec(12)
    month_candidates = [3, 6, 9, 12]
    target_m = None
    target_y = year_digit
    for m in month_candidates:
        if now.month < m or (now.month == m and now.day <= 14):
            target_m = m
            break
    if target_m is None:
        target_m = 3
        target_y = str(now.year + 1)[-1]
    return f"A01{target_y}{target_m:02d}"


def get_kospi200_night_futures_kis():
    """Fetch KOSPI200 night / front-month futures quote and history from KIS API."""
    token = get_kis_access_token()
    if not token:
        return None

    _load_kis_credentials()
    app_key = os.getenv('KIS_APP_KEY')
    app_secret = os.getenv('KIS_APP_SECRET')
    code = get_recent_kospi200_futures_code()
    print(f"[KIS] Fetching KOSPI200 Futures ({code})...")

    headers = {
        'content-type': 'application/json',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'FHMIF10000000'
    }
    params = {
        'FID_COND_MRKT_DIV_CODE': 'F',
        'FID_INPUT_ISCD': code
    }

    try:
        r = requests.get('https://openapi.koreainvestment.com:9443/uapi/domestic-futureoption/v1/quotations/inquire-price',
                         headers=headers, params=params, timeout=10)
        data = r.json()
        out1 = data.get('output1', {})
        if not out1:
            print(f"[KIS] No output1 in price response: {data}")
            return None

        close_p = float(out1['futs_prpr'])
        open_p = float(out1.get('futs_oprc', close_p))
        high_p = float(out1.get('futs_hgpr', max(open_p, close_p)))
        low_p = float(out1.get('futs_lwpr', min(open_p, close_p)))

        sign = out1.get('prdy_vrss_sign', '3')
        vrss = float(out1.get('futs_prdy_vrss', 0.0))
        if sign in ('4', '5'):
            vrss = -abs(vrss)
        ctrt = float(out1.get('futs_prdy_ctrt', 0.0))
        if sign in ('4', '5'):
            ctrt = -abs(ctrt)

        candle = (open_p, high_p, low_p, close_p)

        # 60-day historical chart prices via FHKIF03020100
        history_60 = []
        history_file = os.path.join(OUTPUT_DIR, "kospif_ngt_history.json")
        try:
            now = datetime.now()
            start_d = (now - timedelta(days=120)).strftime('%Y%m%d')
            end_d = now.strftime('%Y%m%d')
            headers_chart = {
                'content-type': 'application/json',
                'authorization': f'Bearer {token}',
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'FHKIF03020100'
            }
            params_chart = {
                'FID_COND_MRKT_DIV_CODE': 'F',
                'FID_INPUT_ISCD': code,
                'FID_INPUT_DATE_1': start_d,
                'FID_INPUT_DATE_2': end_d,
                'FID_PERIOD_DIV_CODE': 'D'
            }
            r_c = requests.get('https://openapi.koreainvestment.com:9443/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice',
                               headers=headers_chart, params=params_chart, timeout=10)
            out2 = r_c.json().get('output2', [])
            if out2:
                # out2 is newest first, reverse to get chronological order
                clean_history = []
                for row in reversed(out2):
                    if 'futs_prpr' in row and 'stck_bsop_date' in row:
                        d_raw = row['stck_bsop_date']
                        d_fmt = f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:]}"
                        clean_history.append({'date': d_fmt, 'price': float(row['futs_prpr'])})
                
                # Keep up to 60 trading days
                clean_history = clean_history[-60:]
                history_60 = [item['price'] for item in clean_history]

                # Sync clean history to local file (overwrites any stale/gapped data)
                try:
                    with open(history_file, "w", encoding="utf-8") as f:
                        json.dump(clean_history, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"[KIS] Failed to sync clean history file: {e}")
        except Exception as e:
            print(f"[KIS] Failed to fetch chart history from API: {e}")

        # Fallback to local history file ONLY if API failed and local data is clean
        if not history_60 and os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    cached_hist = json.load(f)
                if cached_hist and len(cached_hist) >= 2:
                    history_60 = [float(item['price']) for item in cached_hist][-60:]
            except Exception as e:
                print(f"[KIS] Failed to read fallback history: {e}")

        return {
            "price": close_p,
            "change_amt": vrss,
            "change": ctrt,
            "candle": candle,
            "history": history_60
        }
    except Exception as e:
        print(f"[KIS] Failed to fetch KOSPI 200 Futures via KIS API: {e}")
        return None


# ==============================================================================
# 1.5. US Stock Market Holiday & Trading Day Verification
# ==============================================================================

def get_easter_date(year):
    """Calculate Easter Sunday for a given year using Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_nth_weekday(year, month, weekday, n):
    """Find the n-th occurrence of a weekday in a given month (weekday: 0=Mon, ..., 6=Sun)."""
    d = date(year, month, 1)
    diff = (weekday - d.weekday()) % 7
    d += timedelta(days=diff)
    d += timedelta(weeks=n - 1)
    return d


def get_last_weekday(year, month, weekday):
    """Find the last occurrence of a weekday in a given month."""
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    diff = (d.weekday() - weekday) % 7
    return d - timedelta(days=diff)


def get_nyse_holidays(year):
    """
    Return dictionary of official NYSE/NASDAQ stock market holidays for a given year.
    Matches official US market holiday rules including observed holiday shifts.
    """
    h = {}
    # 1. New Year's Day (Jan 1)
    ny = date(year, 1, 1)
    if ny.weekday() == 6:
        h[date(year, 1, 2)] = "New Year's Day (대체휴일)"
    elif ny.weekday() != 5:
        h[ny] = "New Year's Day"

    # 2. Martin Luther King, Jr. Day (3rd Monday of Jan)
    h[get_nth_weekday(year, 1, 0, 3)] = "Martin Luther King, Jr. Day"

    # 3. Washington's Birthday / Presidents' Day (3rd Monday of Feb)
    h[get_nth_weekday(year, 2, 0, 3)] = "Presidents' Day"

    # 4. Good Friday (Friday before Easter)
    h[get_easter_date(year) - timedelta(days=2)] = "Good Friday (성금요일)"

    # 5. Memorial Day (Last Monday of May)
    h[get_last_weekday(year, 5, 0)] = "Memorial Day"

    # 6. Juneteenth National Independence Day (June 19)
    june = date(year, 6, 19)
    if june.weekday() == 6:
        h[date(year, 6, 20)] = "Juneteenth (대체휴일)"
    elif june.weekday() == 5:
        h[date(year, 6, 18)] = "Juneteenth (대체휴일)"
    else:
        h[june] = "Juneteenth"

    # 7. Independence Day (July 4)
    jul4 = date(year, 7, 4)
    if jul4.weekday() == 6:
        h[date(year, 7, 5)] = "Independence Day (대체휴일)"
    elif jul4.weekday() == 5:
        h[date(year, 7, 3)] = "Independence Day (대체휴일)"
    else:
        h[jul4] = "Independence Day"

    # 8. Labor Day (1st Monday of Sep)
    h[get_nth_weekday(year, 9, 0, 1)] = "Labor Day"

    # 9. Thanksgiving Day (4th Thursday of Nov)
    h[get_nth_weekday(year, 11, 3, 4)] = "Thanksgiving Day (추수감사절)"

    # 10. Christmas Day (Dec 25)
    xmas = date(year, 12, 25)
    if xmas.weekday() == 6:
        h[date(year, 12, 26)] = "Christmas Day (대체휴일)"
    elif xmas.weekday() == 5:
        h[date(year, 12, 24)] = "Christmas Day (대체휴일)"
    else:
        h[xmas] = "Christmas Day"

    return h


def check_us_market_open():
    """
    Check if the US stock market (NYSE/NASDAQ) was open today (in New York time).
    When executed at 05:05/06:05 KST, the corresponding New York time is 16:05 of the previous day,
    which is right after the US regular market close (16:00 NY).
    Returns: (is_open: bool, reason: str, ny_date_str: str)
    """
    tz_ny = pytz.timezone('America/New_York')
    ny_now = datetime.now(tz_ny)
    ny_date = ny_now.date()
    ny_date_str = ny_date.strftime('%Y-%m-%d')
    weekday = ny_date.weekday()

    # 1. Weekend Check (Saturday=5, Sunday=6 in NY)
    if weekday == 5:
        return False, f"주말 (토요일, NY: {ny_date_str})", ny_date_str
    if weekday == 6:
        return False, f"주말 (일요일, NY: {ny_date_str})", ny_date_str

    # 2. Official NYSE Holiday Check
    holidays = get_nyse_holidays(ny_date.year)
    if ny_date in holidays:
        holiday_name = holidays[ny_date]
        return False, f"미국 증시 공휴일 ({holiday_name}, NY: {ny_date_str})", ny_date_str

    # 3. yfinance Live Market Data Verification (handles unscheduled closures/national mourning)
    try:
        t = yf.Ticker('^GSPC')
        hist = t.history(period='5d')
        if hist is not None and not hist.empty:
            last_traded_date = hist.index[-1].date()
            if ny_now.hour >= 16 and last_traded_date < ny_date:
                return False, f"미국 증시 미개장/휴장 확인 (최근 거래일: {last_traded_date}, NY 당일: {ny_date_str})", ny_date_str
    except Exception as e:
        print(f"[Warn] yfinance market closure check skipped: {e}")

    return True, f"정상 거래일 (NY: {ny_date_str})", ny_date_str


# ==============================================================================
# 2. General Market Data Fetchers
# ==============================================================================

def get_ticker_history(ticker_name_or_obj, default_period='6mo'):
    if isinstance(ticker_name_or_obj, str):
        ticker_obj = yf.Ticker(ticker_name_or_obj)
    else:
        ticker_obj = ticker_name_or_obj

    for period in [default_period, '1y', '3mo', '1mo']:
        try:
            hist = ticker_obj.history(period=period)
            if hist is not None and not hist.empty:
                hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
                if len(hist) >= 2:
                    return hist
        except Exception as e:
            print(f"Failed to fetch history for {ticker_obj.ticker} with period {period}: {e}")

    try:
        hist = yf.download(ticker_obj.ticker, period=default_period, progress=False)
        if hist is not None and not hist.empty:
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)
            hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
            if len(hist) >= 2:
                return hist
    except Exception as e:
        print(f"Failed to download history for {ticker_obj.ticker}: {e}")

    raise RuntimeError(f"Failed to retrieve history for {ticker_obj.ticker}")


def get_fear_and_greed_index():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://edition.cnn.com/markets/fear-and-greed'
    }
    url = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        score = data['fear_and_greed']['score']
        prev_close = data['fear_and_greed']['previous_close']
        change_amt = score - prev_close
        change = (change_amt / prev_close) * 100

        hist = data.get('fear_and_greed_historical', {}).get('data', [])
        hist_scores = [item['y'] for item in hist]
        history = hist_scores[-60:] if len(hist_scores) > 0 else []

        return score, change_amt, change, history
    except Exception as e:
        print(f"Failed to fetch Fear and Greed: {e}")
        return None, None, None, []


# ==============================================================================
# 3. Direct PNG Table Image Renderer (No Excel Required)
# ==============================================================================

def get_change_percent_bg(name, change):
    """등락률(%) 수치에 따른 배경색 반환 (호재/악재 구분 및 3단계 농도 차등 적용)"""
    if not isinstance(change, (int, float)) or change == 0:
        return '#FFFFFF'

    # 역방향 지표 (03, 04, 05, 08, 10): 상승 시 악재(부정), 하락 시 호재(긍정)
    is_neg_fav = name.startswith(('03.', '04.', '05.', '08.', '10.'))
    is_positive = (change < 0) if is_neg_fav else (change > 0)
    abs_chg = abs(change)

    # [방안 A] 3단계 차등: 1.0% 이하 / 1.0% 초과 ~ 3.0% 미만 / 3.0% 이상
    if abs_chg <= 1.0:
        return '#D5F5E3' if is_positive else '#FADBD8'  # 1단계 (은은한 연파스텔)
    elif abs_chg < 3.0:
        return '#A9DFBF' if is_positive else '#F5B7B1'  # 2단계 (부드러운 중간색)
    else:
        return '#52BE80' if is_positive else '#FF5733'  # 3단계 (선명한 강렬색)


def get_font(size, bold=False):
    """Retrieve font with cross-platform fallback."""
    candidate_fonts = []
    if bold:
        candidate_fonts.append(os.path.join(FONTS_DIR, "NanumGothicBold.ttf"))
        candidate_fonts.append("C:/Windows/Fonts/malgunbd.ttf")
        candidate_fonts.append("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
    else:
        candidate_fonts.append(os.path.join(FONTS_DIR, "NanumGothic.ttf"))
        candidate_fonts.append("C:/Windows/Fonts/malgun.ttf")
        candidate_fonts.append("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")

    for fp in candidate_fonts:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue

    return ImageFont.load_default()


def render_indicators_image(data_rows, candle_data, histories, update_time_str, date_str, output_path):
    """Render investment indicator table directly into a PNG image identical to Excel styling."""
    col_widths = [280, 85, 50, 95, 100, 203]
    total_w = sum(col_widths)
    title_h = 42
    header_h = 25
    row_h = 29
    footer_h = 22
    total_h = title_h + header_h + len(data_rows) * row_h + footer_h

    font_title = get_font(16, bold=True)
    font_header = get_font(13, bold=True)
    font_cell = get_font(12, bold=False)
    font_footer = get_font(10, bold=False)

    im = Image.new('RGB', (total_w, total_h), '#FFFFFF')
    draw = ImageDraw.Draw(im)

    col_x = [0]
    for w in col_widths:
        col_x.append(col_x[-1] + w)

    # 0. Title Row (No background color / White)
    draw.rectangle([(0, 0), (total_w - 1, title_h - 1)], fill='#FFFFFF')
    title_text = f"[{date_str}] 미국 시장 주요 지표"
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (total_w - tw) // 2
    ty = (title_h - th) // 2 - 1
    draw.text((tx, ty), title_text, fill='#000000', font=font_title)

    # 1. Header Row
    header_y1 = title_h
    header_y2 = title_h + header_h
    draw.rectangle([(0, header_y1), (total_w - 1, header_y2 - 1)], fill='#FFC000')
    headers = ['주요 지표', '현재가', '일봉', '등락', '등락률(%)', '60일 Sparkline']
    for idx, (h_text, x1, x2) in enumerate(zip(headers, col_x[:-1], col_x[1:])):
        bbox = draw.textbbox((0, 0), h_text, font=font_header)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = x1 + (x2 - x1 - tw) // 2
        ty = header_y1 + (header_h - th) // 2 - 1
        draw.text((tx, ty), h_text, fill='#000000', font=font_header)

    # 2. Data Rows
    for r_idx, row in enumerate(data_rows):
        y1 = header_y2 + r_idx * row_h
        y2 = y1 + row_h
        name = row['주요 지표']
        num = int(name.split('.')[0]) if '.' in name else (r_idx + 1)
        is_odd = (num % 2 != 0)

        # Base white background
        draw.rectangle([(0, y1), (total_w - 1, y2 - 1)], fill='#FFFFFF')

        # Change percent background (3-tier gradation)
        change = row.get('등락률(%)')
        bg = get_change_percent_bg(name, change)
        draw.rectangle([(col_x[4], y1), (col_x[5] - 1, y2 - 1)], fill=bg)

        # Sparkline cell background
        spark_bg = '#808080' if is_odd else '#FFFFFF'
        draw.rectangle([(col_x[5], y1), (col_x[6] - 1, y2 - 1)], fill=spark_bg)

        # Col 0: 주요 지표 (Left-aligned)
        bbox = draw.textbbox((0, 0), name, font=font_cell)
        th = bbox[3] - bbox[1]
        draw.text((col_x[0] + 8, y1 + (row_h - th) // 2 - 1), name, fill='#000000', font=font_cell)

        # Col 1: 현재가 (Right-aligned)
        price_val = row.get('현재가')
        price_str = f'{price_val:,.2f}' if isinstance(price_val, (int, float)) else str(price_val)
        bbox = draw.textbbox((0, 0), price_str, font=font_cell)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((col_x[2] - 8 - tw, y1 + (row_h - th) // 2 - 1), price_str, fill='#000000', font=font_cell)

        # Col 2: 일봉 (Candlestick center)
        if name in candle_data:
            co, ch, cl, cc = candle_data[name]
            cx1, cx2 = col_x[2], col_x[3]
            cw_avail = cx2 - cx1
            candle_w = 12
            candle_h = 20
            candle_x = cx1 + (cw_avail - candle_w) // 2
            candle_y = y1 + (row_h - candle_h) // 2

            c_color = '#FF0000' if cc >= co else '#0000FF'
            if ch == cl:
                draw.line([(candle_x, candle_y + candle_h // 2), (candle_x + candle_w, candle_y + candle_h // 2)], fill=c_color, width=2)
            else:
                pad_y = 1
                eff_h = candle_h - 2 * pad_y
                scale = eff_h / (ch - cl) if ch != cl else 1.0
                y_high = candle_y + pad_y
                y_low = candle_y + candle_h - pad_y
                yo = candle_y + pad_y + (ch - co) * scale
                yc = candle_y + pad_y + (ch - cc) * scale
                ytop = min(yo, yc)
                ybot = max(yo, yc)
                if ybot - ytop < 2:
                    ybot = ytop + 2
                center_x = candle_x + candle_w // 2
                draw.line([(center_x, y_high), (center_x, y_low)], fill=c_color, width=1)
                draw.rectangle([(candle_x + 2, ytop), (candle_x + candle_w - 2, ybot)], fill=c_color)

        # Col 3: 등락 (Right-aligned)
        chg_amt = row.get('등락')
        if isinstance(chg_amt, (int, float)):
            amt_str = f'▲{chg_amt:.2f}' if chg_amt > 0 else (f'▼{abs(chg_amt):.2f}' if chg_amt < 0 else f'{chg_amt:.2f}')
        else:
            amt_str = str(chg_amt)
        bbox = draw.textbbox((0, 0), amt_str, font=font_cell)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((col_x[4] - 8 - tw, y1 + (row_h - th) // 2 - 1), amt_str, fill='#000000', font=font_cell)

        # Col 4: 등락률(%) (Right-aligned)
        chg_str = f'{change:.2f}' if isinstance(change, (int, float)) else str(change)
        bbox = draw.textbbox((0, 0), chg_str, font=font_cell)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((col_x[5] - 8 - tw, y1 + (row_h - th) // 2 - 1), chg_str, fill='#000000', font=font_cell)

        # Col 5: 60일 Sparkline
        raw_hist = histories.get(name, [])
        hist = [float(v) for v in raw_hist if v is not None and not (isinstance(v, float) and (v != v))]
        if len(hist) >= 2:
            sx1 = col_x[5] + 8
            sx2 = col_x[6] - 8
            sy1 = y1 + 4
            sy2 = y2 - 4
            sw = sx2 - sx1
            sh = sy2 - sy1
            min_v = min(hist)
            max_v = max(hist)
            diff = max_v - min_v if max_v != min_v else 1.0

            line_color = '#FFFF00' if is_odd else '#2F5597'
            pts = []
            total_slots = 59  # standard 60-day window (0 to 59 slots)
            hist_len = len(hist)
            # If a ticker has fewer than 60 days (e.g., newly listed IPO like ANT with 5 days),
            # align it to the right so time scale is consistent across all rows!
            offset = total_slots - (hist_len - 1) if hist_len < 60 else 0
            denom = total_slots if hist_len < 60 else (hist_len - 1)

            for i, val in enumerate(hist):
                slot = offset + i
                px = sx1 + (slot / denom) * sw
                py = sy2 - ((val - min_v) / diff) * sh
                pts.append((px, py))
            draw.line(pts, fill=line_color, width=2)

    # 3. Footer Row
    fy1 = total_h - footer_h
    draw.rectangle([(0, fy1), (total_w - 1, total_h - 1)], fill='#FFC000')
    footer_text = f'updated : {update_time_str}'
    bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((total_w - 8 - tw, fy1 + (footer_h - th) // 2 - 1), footer_text, fill='#555555', font=font_footer)

    # 4. Grid lines
    grid_color = '#D9D9D9'
    # Vertical grid lines (starting from header down to footer, excluding title row)
    for x in col_x:
        draw.line([(x, title_h), (x, total_h - 1)], fill=grid_color, width=1)

    # Horizontal grid lines
    draw.line([(0, title_h), (total_w - 1, title_h)], fill=grid_color, width=1)
    draw.line([(0, header_y2), (total_w - 1, header_y2)], fill=grid_color, width=1)
    for r in range(1, len(data_rows) + 1):
        y = header_y2 + r * row_h
        draw.line([(0, y), (total_w - 1, y)], fill=grid_color, width=1)
    draw.line([(0, total_h - 1), (total_w - 1, total_h - 1)], fill=grid_color, width=1)

    # Outer border
    draw.rectangle([(0, 0), (total_w - 1, total_h - 1)], outline='#000000', width=1)

    im.save(output_path, 'PNG')
    print(f"Table image successfully generated: {output_path}")


# ==============================================================================
# 4. Telegram Notification
# ==============================================================================

def send_telegram_photo(image_path, caption=None):
    """Send generated indicator image via Telegram bot (single clean high-resolution photo)."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID not found in .env. Skipping Telegram message.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        with open(image_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            r = requests.post(url, data=data, files=files, timeout=30)
            r.raise_for_status()
            res = r.json()
            if res.get('ok'):
                print(f"Telegram photo successfully sent to chat {chat_id}")
                return True
            else:
                print(f"Telegram API returned error: {res}")
                return False
    except Exception as e:
        print(f"Failed to send Telegram photo: {e}")
        return False


# ==============================================================================
# 5. Main Execution Flow
# ==============================================================================

def main():
    # 0. 미국 시장(NYSE/NASDAQ) 개장 여부 검증 (토/일 주말, 추수감사절 등 공휴일 자동 스킵)
    force_run = ('--force' in sys.argv)
    if not force_run:
        is_open, reason, ny_date_str = check_us_market_open()
        if not is_open:
            print(f"[Market Holiday Guard] {reason} -> 미국 시장 휴장으로 실행 및 텔레그램 발송을 건너뜁니다.")
            return
    else:
        print("[Notice] --force 옵션이 감지되어 휴장 여부와 관계없이 강제 실행합니다.")

    tickers = {
        '01. 미국 S&P 500 지수': '^GSPC',
        '02. 미국 나스닥 지수': '^IXIC',
        '03. 미국 국채 10년물 금리(TNX)': '^TNX',
        '04. 미국 달러 지수(USD Index)': 'DX-Y.NYB',
        '05. USD/KRW 환율': 'KRW=X',
        '06. EWY (MSCI South Korea ETF)': 'EWY',
        '07. KOSPI200 야간 선물 지수': 'KOSPI200_NIGHT',
        '08. CBOE VIX': '^VIX',
        '09. CNN Fear & Greed Index': 'FEAR_GREED',
        '10. Crude Oil WTI (NYMEX, CL=F)': 'CL=F',
        '11. 금 (COMEX, GC=F)': 'GC=F',
        '12. 비트코인(BTC-USD)': 'BTC-USD',
        '13. 필라델피아 반도체 지수(SOX)': '^SOX',
        '14. SKHY (SK하이닉스 ADR)': 'SKHY',
        '15. 엔비디아 (NVDA)': 'NVDA',
        '16. 마이크론 (MU)': 'MU',
        '17. 샌디스크 (SNDK)': 'SNDK',
        '18. 앤트로픽 (ANT)': 'ANT',
        '19. 오라클 (ORCL)': 'ORCL',
        '20. 코어위브 (CRWV)': 'CRWV'
    }

    data = []
    histories = {}
    candle_data = {}

    print("Fetching market data...")
    for name, ticker in tickers.items():
        if ticker == 'KOSPI200_NIGHT':
            kis_res = get_kospi200_night_futures_kis()
            if kis_res is not None:
                price = kis_res["price"]
                change_amt = kis_res["change_amt"]
                change = kis_res["change"]
                candle_data[name] = kis_res["candle"]
                histories[name] = kis_res["history"]
                data.append({'주요 지표': name, '현재가': price, '일봉': '', '등락': change_amt, '등락률(%)': change})
            else:
                data.append({'주요 지표': name, '현재가': 'N/A', '일봉': '', '등락': 'N/A', '등락률(%)': 'N/A'})

        elif ticker == 'FEAR_GREED':
            print(f"Fetching {name} via requests...")
            price, change_amt, change, history = get_fear_and_greed_index()
            if price is not None and change is not None:
                data.append({'주요 지표': name, '현재가': round(price, 2), '일봉': '', '등락': round(change_amt, 2), '등락률(%)': round(change, 2)})
                if history:
                    histories[name] = history
            else:
                data.append({'주요 지표': name, '현재가': 'N/A', '일봉': '', '등락': 'N/A', '등락률(%)': 'N/A'})

        else:
            print(f"Fetching {name} via yfinance ({ticker})...")
            try:
                t = yf.Ticker(ticker)
                hist = get_ticker_history(t, '6mo')
                if len(hist) >= 2:
                    histories[name] = hist['Close'].tolist()[-60:]
                    current_price = hist['Close'].iloc[-1]
                    prev_price = hist['Close'].iloc[-2]
                    change_amt = current_price - prev_price
                    change = (change_amt / prev_price) * 100 if prev_price else 0

                    open_p = hist['Open'].iloc[-1]
                    high_p = hist['High'].iloc[-1]
                    low_p = hist['Low'].iloc[-1]
                    candle_data[name] = (open_p, high_p, low_p, current_price)
                    data.append({'주요 지표': name, '현재가': round(current_price, 2), '일봉': '', '등락': round(change_amt, 2), '등락률(%)': round(change, 2)})
                else:
                    data.append({'주요 지표': name, '현재가': 'N/A', '일봉': '', '등락': 'N/A', '등락률(%)': 'N/A'})
            except Exception as e:
                print(f"Failed to fetch {name}: {e}")
                data.append({'주요 지표': name, '현재가': 'N/A', '일봉': '', '등락': 'N/A', '등락률(%)': 'N/A'})

    date_str = datetime.now().strftime("%Y-%m-%d")
    update_time_str = datetime.now().strftime("%Y-%m-%d-%H:%M")
    img_filename = os.path.join(OUTPUT_DIR, f"BeforeSunrise_{date_str}.png")

    # Render table image directly without creating Excel file
    render_indicators_image(data, candle_data, histories, update_time_str, date_str, img_filename)

    # Send Telegram notification (Single clean photo)
    caption = f"[{date_str}] 미국 시장 주요 지표"
    send_telegram_photo(img_filename, caption=caption)


if __name__ == '__main__':
    main()
