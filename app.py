# -*- coding: utf-8 -*-
"""
🌅 Before Sunrise - 글로벌 20대 핵심 투자 지표 대시보드
Streamlit Web Application (Port 8507)
- 매일 아침 미국 시장 마감 직후 글로벌 핵심 지표 수집 및 텔레그램 발송 봇 통합 뷰어
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

st.set_page_config(
    page_title="Before Sunrise",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark Theme CSS
CUSTOM_CSS = """
<style>
    .reportview-container, .main {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
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
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='margin-bottom: 2px;'>🌅 Before Sunrise</h2>", unsafe_allow_html=True)
    st.caption("글로벌 20대 핵심 투자 지표 대시보드")

    # Dynamic Unified KIS Badge Card
    today_str = datetime.now().strftime("%Y-%m-%d")
    token_status = get_kis_token_status()
    if token_status.get("connected"):
        iss_date = token_status.get("issued_at", "").split()[0] if token_status.get("issued_at") else today_str
        exp_time = token_status.get("expires_at", "").split()[1] if " " in token_status.get("expires_at", "") else ""
        sub_text = f"🔑 공용 토큰 정상 활성 (만료: {exp_time})" if exp_time else "🔑 공용 토큰 정상 활성"
        badge_html = f"""
        <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 18px;">
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
        <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #ef4444; margin-bottom: 18px;">
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

    available_dates = get_available_report_dates()
    selected_png = None
    selected_date = None

    if available_dates:
        date_options = [d[0] for d in available_dates]
        chosen_date = st.selectbox(
            "📅 리포트 일자 선택",
            options=date_options,
            index=0,
            help="과거 일자에 생성된 데일리 인디케이터 리포트 이미지를 선택합니다."
        )
        selected_date = chosen_date
        selected_png = dict(available_dates).get(chosen_date)
    else:
        st.info("아직 생성된 일일 리포트 이미지가 없습니다.")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Action Button: Manual Refresh & Telegram Send
    if st.button("🔄 지금 데이터 수집 & 텔레그램 발송", type="primary", use_container_width=True):
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

    st.markdown("---")
    st.markdown("### ⏰ 자동 스케줄 안내")
    st.markdown(
        """
        - **발송 시각**: 화~토 아침 06:05 KST
        - **서머타임(EDT)**: 아침 05:05 KST 자동 적응
        - **트리거**: 뉴욕 증시 마감(16:00) 5분 후 자동 발송
        - **휴장 감지**: 토/일 주말 및 미국 법정 공휴일 자동 스킵
        """
    )
    st.caption("배포 서버: Oracle Cloud Server 1 (포트 8507)")


# ---------------------------------------------------------
# Main Content View
# ---------------------------------------------------------
st.title("🌅 Before Sunrise")
st.markdown("매일 아침 개장 전, 미국 정규장 마감 결과 및 **KOSPI200 야간 선물 지수**, 환율, 금리, 반도체 지표를 한눈에 파악합니다.")

# Load history
df_ngt = load_kospi_night_history()

# Header Metric Cards (Latest night futures & indicators if available)
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
    if selected_png and os.path.exists(selected_png):
        st.markdown(f"#### 📋 {selected_date} 일일 투자 지표 종합 리포트")
        st.image(selected_png, use_container_width=True, caption=f"BeforeSunrise - {selected_date}")

        with open(selected_png, "rb") as file:
            btn = st.download_button(
                label="💾 고화질 원본 이미지 다운로드 (PNG)",
                data=file,
                file_name=f"BeforeSunrise_{selected_date}.png",
                mime="image/png"
            )
    else:
        st.warning("선택된 날짜의 리포트 이미지를 찾을 수 없습니다. 사이드바에서 [🔄 지금 데이터 수집] 버튼을 눌러 새로 생성해 주세요.")

with tab2:
    st.markdown("#### 🌙 KOSPI200 야간 선물 일별 종가 추이 (최근 60거래일)")
    if not df_ngt.empty:
        # Plotly chart if available, otherwise native line chart
        try:
            import plotly.express as px
            fig = px.line(
                df_ngt,
                x="date",
                y="price",
                title="KOSPI200 Night Futures Trend",
                labels={"date": "날짜", "price": "지수 종가 (Point)"},
                markers=True
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0b0f19",
                plot_bgcolor="#1e293b",
                font_color="#f8fafc",
                height=450,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            chart_df = df_ngt.set_index("date")[["price"]]
            st.line_chart(chart_df, height=400)

        # Show Table
        with st.expander("📋 야간 선물 일별 데이터 테이블 보기"):
            disp_df = df_ngt.sort_values("date", ascending=False).copy()
            disp_df["date"] = disp_df["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(disp_df, use_container_width=True, hide_index=True)
    else:
        st.info("야간 선물 누적 이력 데이터(kospif_ngt_history.json)가 아직 없습니다.")

with tab3:
    st.markdown(
        """
        ### 🌐 Before Sunrise 20대 핵심 지표 목록
        
        매일 아침 한국 증시 개장 전, 아래 20대 지표를 통해 글로벌 매크로와 야간 시장의 흐름을 선제적으로 진단합니다.
        
        1. **01. 미국 S&P 500 지수 (`^GSPC`)** - 미국 대형주 500개 종합 지표
        2. **02. 미국 나스닥 지수 (`^IXIC`)** - 글로벌 기술주 및 혁신 성장주 흐름
        3. **03. 미국 국채 10년물 금리 (`^TNX`)** - 글로벌 무위험 금리 및 밸류에이션 할인율 기준
        4. **04. 미국 달러 지수 (`DX-Y.NYB`)** - 주요 6개국 통화 대비 달러화 강세/약세
        5. **05. USD/KRW 원/달러 환율 (`KRW=X`)** - 외국인 수급의 핵심 선행 지표
        6. **06. EWY (iShares MSCI South Korea ETF)** - 미국 장중 거래되는 한국물 대표 ETF
        7. **07. KOSPI200 야간 선물 지수 (`KIS Open API`)** - 당일 한국 코스피200 시초가 갭상승/갭하락 직접 선행 지표
        8. **08. CBOE VIX 변동성 지수 (`^VIX`)** - 월가 공포 지수 (20 초과 시 위험 관리)
        9. **09. CNN Fear & Greed Index** - 시장 참여자 심리 (극단적 공포/탐욕 판별)
        10. **10. WTI 원유 선물 (`CL=F`)** - 글로벌 에너지 원가 및 인플레이션 압력
        11. **11. 금 선물 (`GC=F`)** - 안전 자산 선호 및 지정학적 리스크 척도
        12. **12. 비트코인 (`BTC-USD`)** - 글로벌 디지털 유동성 및 위험 자산 선호도
        13. **13. 필라델피아 반도체 지수 (`^SOX`)** - 삼성전자, SK하이닉스 당일 시세의 최우선 벤치마크
        14. **14. SKHY (SK하이닉스 ADR)** - 미국 장외 거래되는 SK하이닉스 ADR
        15. **15. 엔비디아 (`NVDA`)** - AI 반도체 대장주
        16. **16. 마이크론 (`MU`)** - 글로벌 메모리 반도체(DRAM/NAND) 벤치마크
        17. **17. 샌디스크 (`SNDK`)** - 플래시 메모리 섹터 지표
        18. **18. 앤트로픽 (`ANT`)** - 생성형 AI 섹터 관련주
        19. **19. 오라클 (`ORCL`)** - 엔터프라이즈 클라우드 & AI 인프라
        20. **20. 코어위브 (`CRWV`)** - 차세대 GPU 클라우드 인프라
        """
    )
