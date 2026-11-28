# -*- coding: utf-8 -*-
"""
🌅 Before Sunrise - 글로벌 20대 핵심 투자 지표 대시보드
Streamlit Web Application (Port 8507)
- 00 App_AI_Template 공통 디자인 및 UI/UX 표준 가이드 (01, 02, 03) 100% 준수
- KIS(한국투자증권) 공용 토큰 연동을 통한 KOSPI200 야간선물 실시간/일별 데이터 조회
"""

import os
import sys
import glob
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

from daily_indicators import get_kis_token_status

# Base paths
CURRENT_DIR = Path(__file__).resolve().parent
DAILY_DATA_DIR = CURRENT_DIR / "DailyData"
DAILY_DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_JSON = DAILY_DATA_DIR / "kospif_ngt_history.json"
FAVICON_PATH = CURRENT_DIR / "favicon.png"

# 1. Page Config (가이드 01 - 2: 파비콘 3단계 우선순위 준수)
st.set_page_config(
    page_title="Before Sunrise",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Standard CSS Theme System (가이드 01, 02 준수)
CUSTOM_CSS = """
<style>
    /* 상단 고정 헤더 배경 투명화 */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* 화면 상단 패딩 표준화 (2.0rem) */
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 2.0rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 100% !important;
    }

    /* 사이드바 다크 네이비 테마 & 테두리 */
    section[data-testid="stSidebar"], [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155 !important;
    }

    /* 사이드바 텍스트 Pure White 강제 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #f8fafc !important;
        -webkit-text-fill-color: #f8fafc !important;
    }

    /* 사이드바 접기/열기 버튼 시인성 보강 */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #1e293b !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
    }
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapsedControl"] button * {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
    }

    /* 공통 파일 다운로드 버튼 규격 */
    div[data-testid="stDownloadButton"] > button,
    .stDownloadButton > button {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        height: 38px !important;
        padding: 0 16px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stDownloadButton"] > button:hover,
    .stDownloadButton > button:hover {
        background-color: #475569 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
    }

    /* 프라이머리 버튼 (파란색 표준: 가이드 01 - 4(1)) */
    div.stButton > button[kind="primary"],
    div[data-testid="stSidebar"] button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background-color: #2563eb !important;
        border: 1px solid #1d4ed8 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div[data-testid="stSidebar"] button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background-color: #1d4ed8 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }

    /* 세컨더리 버튼 (가이드 02 - 5 Type A) */
    div.stButton > button[kind="secondary"],
    div[data-testid="stSidebar"] button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        background-color: #334155 !important;
        border: 1px solid #475569 !important;
        color: #f8fafc !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }
    div.stButton > button[kind="secondary"]:hover,
    div[data-testid="stSidebar"] button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #475569 !important;
        border-color: #94a3b8 !important;
        color: #ffffff !important;
    }

    /* 지표 메트릭 카드 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-change-up {
        color: #f43f5e;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .metric-change-down {
        color: #38bdf8;
        font-size: 0.9rem;
        font-weight: 600;
    }

    /* 탭 헤더 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 8px 8px 0px 0px;
        background-color: #1e293b;
        color: #94a3b8;
        font-weight: 600;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Plotly Chart Theme Constants (가이드 03 준수)
STANDARD_CHART_THEME = {
    'paper_bgcolor': '#1E293B',    # Slate-800 (외곽 카드 배경)
    'plot_bgcolor': '#0F172A',     # Slate-900 (내부 딥 블랙 플롯)
    'text_main': '#F8FAFC',        # 타이틀/헤더 텍스트 (순백색)
    'text_body': '#E2E8F0',        # 본문 및 축 라벨
    'text_muted': '#CBD5E1',       # 눈금 수치 (Slate-300)
    'grid_color': '#334155',       # 그리드 격자선
    'border_color': '#475569',     # 축 기준선
    'legend_bg': 'rgba(30, 41, 59, 0.85)',
    'legend_border': '#334155',
    'hover_bg': 'rgba(15, 23, 42, 0.9)',
    'hover_border': '#334155'
}


def get_available_report_dates():
    """Scan available BeforeSunrise PNG files in DailyData."""
    png_files = sorted(glob.glob(str(DAILY_DATA_DIR / "BeforeSunrise_*.png")), reverse=True)
    dates = []
    for p in png_files:
        fname = Path(p).stem  # BeforeSunrise_YYYY-MM-DD
        if fname.startswith("BeforeSunrise_"):
            d_part = fname.replace("BeforeSunrise_", "")
            dates.append((d_part, p))
    return dates


def load_kospi_night_history():
    """Load KOSPI200 night futures history from JSON."""
    if not HISTORY_JSON.exists():
        return pd.DataFrame()
    try:
        with open(HISTORY_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            df = pd.DataFrame(data)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
            return df
    except Exception as e:
        st.warning(f"야간선물 이력 로드 실패: {e}")
    return pd.DataFrame()


def run_data_collection():
    """Execute daily_indicators.py in force mode."""
    script_path = CURRENT_DIR / "daily_indicators.py"
    py_bin = sys.executable
    if os.path.exists("/home/ubuntu/venv_apps/bin/python3"):
        py_bin = "/home/ubuntu/venv_apps/bin/python3"

    cmd = [py_bin, str(script_path), "--force"]
    res = subprocess.run(cmd, cwd=str(CURRENT_DIR), capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr


# ---------------------------------------------------------
# 3. Sidebar (가이드 02: 단일 블록 & 표준 헤더 카드 적용)
# ---------------------------------------------------------
with st.sidebar:
    # (1) 최상단 표준 헤더 카드
    st.markdown(
        """
        <div style='padding: 2px 0 12px 0;'>
            <div style='font-size: 1.25rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.01em; display: flex; align-items: center; gap: 8px;'>
                <span>🌅</span> Before Sunrise
            </div>
            <div style='font-size: 0.82rem; color: #94a3b8; margin-top: 4px; line-height: 1.4;'>
                미국 정규장 마감 후 글로벌 20대 핵심 지표 브리핑
            </div>
        </div>
        <hr style='border: 0; height: 1px; background-color: #334155; margin: 10px 0 16px 0;'>
        """,
        unsafe_allow_html=True
    )

    # (2) Dynamic Unified KIS Badge Card
    today_str = datetime.now().strftime("%Y-%m-%d")
    token_status = get_kis_token_status()
    if token_status.get("connected"):
        iss_date = token_status.get("issued_at", "").split()[0] if token_status.get("issued_at") else today_str
        exp_time = token_status.get("expires_at", "").split()[1] if " " in token_status.get("expires_at", "") else ""
        sub_text = f"🔑 공용 토큰 정상 활성 (만료: {exp_time})" if exp_time else "🔑 공용 토큰 정상 활성"
        badge_html = f"""
        <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #10b981; font-weight: 600; font-size: 0.88rem;">🟢 KIS 공용 토큰 연동</span>
                <span style="color: #94a3b8; font-size: 0.78rem;">{iss_date}</span>
            </div>
            <div style="color: #38bdf8; font-size: 0.82rem; display: flex; align-items: center; gap: 4px;">
                {sub_text}
            </div>
        </div>
        """
    else:
        badge_html = f"""
        <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #ef4444; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #ef4444; font-weight: 600; font-size: 0.88rem;">🔴 KIS 공용 토큰 미연결</span>
                <span style="color: #94a3b8; font-size: 0.78rem;">{today_str}</span>
            </div>
            <div style="color: #fca5a5; font-size: 0.82rem; display: flex; align-items: center; gap: 4px;">
                ⚠️ 공용 토큰 파일(kis_token.json) 확인 필요
            </div>
        </div>
        """
    st.markdown(badge_html, unsafe_allow_html=True)

    # (3) 리포트 일자 선택 섹션 (소제목 규격 준수)
    st.markdown(
        "<div style='font-size: 0.95rem; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;'>📅 리포트 일자 선택</div>",
        unsafe_allow_html=True
    )
    available_dates = get_available_report_dates()
    selected_png = None
    selected_date = None

    if available_dates:
        date_options = [d[0] for d in available_dates]
        chosen_date = st.selectbox(
            "리포트 일자",
            options=date_options,
            index=0,
            label_visibility="collapsed",
            help="과거 일자에 생성된 데일리 인디케이터 리포트 이미지를 선택합니다."
        )
        selected_date = chosen_date
        selected_png = dict(available_dates).get(chosen_date)
    else:
        st.info("아직 생성된 일일 리포트 이미지가 없습니다.")

    # (4) 구분선 & 하단 액션 버튼 (가이드 02 - 5 Type A: 2열 표준 배치)
    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 16px 0;'>", unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Update", use_container_width=True, help="데이터를 실시간으로 재수집하고 텔레그램으로 즉시 발송합니다."):
            with st.spinner("미국 시장 및 KIS 야간선물 시세 수집 중 (약 10~15초 소요)..."):
                success, stdout, stderr = run_data_collection()
                if success:
                    st.toast("성공적으로 데이터 수집 및 텔레그램 발송이 완료되었습니다!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("데이터 수집 중 오류가 발생했습니다.")
                    if stderr:
                        st.code(stderr[-500:])

    with col_btn2:
        if st.button("🔍 조회", type="primary", use_container_width=True, help="선택한 일자의 대시보드를 조회합니다."):
            st.rerun()

    # (5) 자동 발송 스케줄 안내 카드
    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 16px 0;'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background-color: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 12px;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; margin-bottom: 6px;">
                ⏰ 텔레그램 자동 발송 스케줄
            </div>
            <div style="font-size: 0.78rem; color: #94a3b8; line-height: 1.5;">
                • <b>발송 시각</b> : 화~토 아침 06:05 KST (서머타임 05:05)<br>
                • <b>트리거</b> : 뉴욕 정규장 마감(16:00 EST) 5분 후<br>
                • <b>휴장 감지</b> : 주말 및 미국 공휴일 자동 스킵<br>
                <span style="color: #10b981;">• 서버 1 백그라운드 크론탭(crontab) 등록 가동 중</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------------------------------------------------------
# 4. Main Content View (가이드 01 - 3: 메인 타이틀 H1 표준)
# ---------------------------------------------------------
st.markdown(
    """
    <div style='text-align: center; padding-top: 0.5rem;'>
        <h1 style='color: #8AB4F8; font-size: 2.0rem; font-weight: 800; margin-bottom: 6px;'>🌅 Before Sunrise</h1>
        <p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 16px;'>매일 아침 개장 전, 미국 정규장 마감 결과 및 KOSPI200 야간 선물, 환율, 금리, 반도체 지표 브리핑</p>
        <hr style='border: 0; height: 1px; background-color: #334155; margin: 16px 0 24px 0;'>
    </div>
    """,
    unsafe_allow_html=True
)

# Load history
df_ngt = load_kospi_night_history()

# Header Metric Cards
if not df_ngt.empty:
    latest_row = df_ngt.iloc[-1]
    prev_row = df_ngt.iloc[-2] if len(df_ngt) >= 2 else latest_row
    ngt_p = latest_row["price"]
    prev_p = prev_row["price"]
    diff = ngt_p - prev_p
    diff_pct = (diff / prev_p * 100) if prev_p else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">KOSPI200 야간 선물 종가</div>
                <div class="metric-val">{ngt_p:.2f}</div>
                <div class="{'metric-change-up' if diff >= 0 else 'metric-change-down'}">
                    {'▲' if diff >= 0 else '▼'} {abs(diff):.2f} ({diff_pct:+.2f}%)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">야간 선물 5일 최고가</div>
                <div class="metric-val">{df_ngt['price'].tail(5).max():.2f}</div>
                <div style="color: #94a3b8; font-size: 0.85rem;">최근 5거래일 범위</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">야간 선물 5일 최저가</div>
                <div class="metric-val">{df_ngt['price'].tail(5).min():.2f}</div>
                <div style="color: #94a3b8; font-size: 0.85rem;">최근 5거래일 범위</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">최근 갱신 기준일</div>
                <div class="metric-val" style="font-size: 1.2rem; padding-top: 4px;">{selected_date or today_str}</div>
                <div style="color: #10b981; font-size: 0.85rem;">🟢 정상 집계 완료</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Tabs
tab1, tab2, tab3 = st.tabs([
    "🖼️ 데일리 인디케이터 리포트 카드",
    "🌙 KOSPI200 야간 선물 60일 추이",
    "ℹ️ 20대 핵심 지표 구성 가이드"
])

with tab1:
    # Level 2 Main Sector Title (가이드 01 - 6 준수)
    st.markdown(
        f"<div style='font-size: 1.20rem; font-weight: 700; color: #8AB4F8; margin: 18px 0 10px 0; display: flex; align-items: center; gap: 8px;'>"
        f"<span>📋</span> {selected_date or today_str} 일일 투자 지표 종합 리포트"
        f"</div>",
        unsafe_allow_html=True
    )

    if selected_png and os.path.exists(selected_png):
        st.image(selected_png, use_container_width=True, caption=f"BeforeSunrise - {selected_date}")

        with open(selected_png, "rb") as file:
            st.download_button(
                label="📥 원본 리포트 이미지 다운로드 (PNG)",
                data=file,
                file_name=f"BeforeSunrise_{selected_date}.png",
                mime="image/png",
                use_container_width=True
            )
    else:
        st.warning("선택된 날짜의 리포트 이미지를 찾을 수 없습니다. 사이드바에서 [🔄 Update] 버튼을 눌러 새로 생성해 주세요.")

with tab2:
    # Level 2 Main Sector Title (가이드 01 - 6 준수)
    st.markdown(
        "<div style='font-size: 1.20rem; font-weight: 700; color: #8AB4F8; margin: 18px 0 10px 0; display: flex; align-items: center; gap: 8px;'>"
        "<span>🌙</span> KOSPI200 야간 선물 일별 종가 추이 (최근 60거래일)"
        "</div>",
        unsafe_allow_html=True
    )

    if not df_ngt.empty:
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_ngt["date"],
                y=df_ngt["price"],
                mode="lines+markers",
                name="야간선물 종가",
                line=dict(color="#38BDF8", width=2.5),
                marker=dict(size=5, color="#818CF8"),
                hovertemplate="날짜: %{x|%Y-%m-%d}<br>종가: %{y:.2f} pt<extra></extra>"
            ))

            # 가이드 03: 고대비 Tailwind Slate 액자형 카드 표준 테마 적용
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor=STANDARD_CHART_THEME['paper_bgcolor'],
                plot_bgcolor=STANDARD_CHART_THEME['plot_bgcolor'],
                title=dict(
                    text="<b>KOSPI200 Night Futures Trend</b>",
                    font=dict(color=STANDARD_CHART_THEME['text_main'], size=15),
                    x=0.5,
                    xanchor="center"
                ),
                hovermode="x unified",
                hoverlabel=dict(
                    bgcolor=STANDARD_CHART_THEME['hover_bg'],
                    bordercolor=STANDARD_CHART_THEME['hover_border'],
                    font=dict(color="#FFFFFF", size=12)
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    bgcolor=STANDARD_CHART_THEME['legend_bg'],
                    bordercolor=STANDARD_CHART_THEME['legend_border'],
                    borderwidth=1,
                    font=dict(color=STANDARD_CHART_THEME['text_main'], size=11)
                ),
                margin=dict(l=40, r=40, t=75, b=40),
                height=460
            )

            fig.update_xaxes(
                gridcolor=STANDARD_CHART_THEME['grid_color'],
                linecolor=STANDARD_CHART_THEME['border_color'],
                tickfont=dict(color=STANDARD_CHART_THEME['text_muted'], size=11)
            )
            fig.update_yaxes(
                gridcolor=STANDARD_CHART_THEME['grid_color'],
                linecolor=STANDARD_CHART_THEME['border_color'],
                tickfont=dict(color=STANDARD_CHART_THEME['text_muted'], size=11)
            )

            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Plotly 렌더링 대체: {e}")
            chart_df = df_ngt.set_index("date")[["price"]]
            st.line_chart(chart_df, height=400)

        # Level 3 Sub Sector Title
        st.markdown(
            "<div style='font-size: 1.00rem; font-weight: 600; color: #E2E8F0; margin: 14px 0 6px 0; display: flex; align-items: center; gap: 6px;'>"
            "<span>📅</span> 야간 선물 일별 데이터 테이블"
            "</div>",
            unsafe_allow_html=True
        )
        with st.expander("📋 일별 데이터 테이블 상세 보기 (펼치기)", expanded=False):
            disp_df = df_ngt.sort_values("date", ascending=False).copy()
            disp_df["date"] = disp_df["date"].dt.strftime("%Y-%m-%d")
            disp_df.columns = ["거래일자", "야간선물 종가 (pt)"]
            st.dataframe(disp_df, use_container_width=True, hide_index=True)
    else:
        st.info("야간 선물 누적 이력 데이터(kospif_ngt_history.json)가 아직 없습니다.")

with tab3:
    # Level 2 Main Sector Title
    st.markdown(
        "<div style='font-size: 1.20rem; font-weight: 700; color: #8AB4F8; margin: 18px 0 10px 0; display: flex; align-items: center; gap: 8px;'>"
        "<span>🌐</span> Before Sunrise 20대 핵심 지표 목록 및 모니터링 목적"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        """
        매일 아침 한국 증시 개장 전, 아래 20대 지표를 통해 글로벌 매크로와 야간 시장의 흐름을 선제적으로 진단합니다.
        
        1. **01. 미국 S&P 500 지수 (`^GSPC`)** - 미국 대형주 500개 종합 벤치마크
        2. **02. 미국 나스닥 지수 (`^IXIC`)** - 글로벌 기술주 및 혁신 성장주 흐름
        3. **03. 미국 국채 10년물 금리 (`^TNX`)** - 글로벌 무위험 금리 및 밸류에이션 할인율 기준
        4. **04. 미국 달러 지수 (`DX-Y.NYB`)** - 주요 6개국 통화 대비 달러화 강세/약세
        5. **05. USD/KRW 원/달러 환율 (`KRW=X`)** - 외국인 수급의 핵심 선행 지표
        6. **06. CBOE VIX 변동성 지수 (`^VIX`)** - 월가 공포 지수 (20 초과 시 위험 관리)
        7. **07. CNN Fear & Greed Index** - 시장 참여자 심리 (극단적 공포/탐욕 판별)
        8. **08. WTI 원유 선물 (`CL=F`)** - 글로벌 에너지 원가 및 인플레이션 압력
        9. **09. 금 선물 (`GC=F`)** - 안전 자산 선호 및 지정학적 리스크 척도
        10. **10. 비트코인 (`BTC-USD`)** - 글로벌 디지털 유동성 및 위험 자산 선호도
        11. **11. 필라델피아 반도체 지수 (`^SOX`)** - 삼성전자, SK하이닉스 당일 시세의 최우선 벤치마크
        12. **12. 엔비디아 (`NVDA`)** - AI 반도체 대장주
        13. **13. 마이크론 (`MU`)** - 글로벌 메모리 반도체(DRAM/NAND) 벤치마크
        14. **14. 샌디스크 (`SNDK`)** - 플래시 메모리 섹터 지표
        15. **15. 앤트로픽 (`ANT`)** - 생성형 AI 섹터 관련주
        16. **16. 오라클 (`ORCL`)** - 엔터프라이즈 클라우드 & AI 인프라
        17. **17. 코어위브 (`CRWV`)** - 차세대 GPU 클라우드 인프라
        18. **18. SKHY (SK하이닉스 ADR)** - 미국 장외 거래되는 SK하이닉스 ADR 프리미엄
        19. **19. EWY (iShares MSCI South Korea ETF)** - 미국 장중 거래되는 한국물 대표 ETF
        20. **20. KOSPI200 야간 선물 지수 (`KIS Open API`)** - 당일 한국 코스피200 시초가 갭상승/갭하락 직접 선행 지표
        """
    )

# 5. Legal Disclaimer Footer (가이드 01 - 5(2) 준수)
st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 30px 0 10px 0;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 0.8rem; margin-top: 8px; margin-bottom: 24px; line-height: 1.6;'>"
    "⚠️ 본 서비스에서 제공하는 모든 정보는 투자 참고용이며, 투자의 최종 결정과 책임은 투자자 본인에게 있습니다."
    "</div>",
    unsafe_allow_html=True
)
