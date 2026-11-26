# BeforeSunrise (일일 투자 지표 자동 발송 봇)

매일 아침 글로벌 주요 20대 투자 지표(미국 지수, 반도체, 주요 빅테크/AI, 원자재, 환율, 금리, 비트코인 및 **KOSPI200 야간 선물 지수**)를 자동 수집하고, 고품질 대시보드 테이블 이미지(PNG)를 생성하여 **텔레그램 채널/개인 챗**으로 전송하는 자동화 애플리케이션입니다.

---

## 🌟 주요 특징 및 개선 사항

1. **KOSPI200 야간 선물 지수 데이터 제공처 전환**
   - 기존 eSignal 스크래핑 방식에서 **한국투자증권(KIS Open API)** 실시간/차트 공식 API로 변경하여 안정적인 시세 수집을 보장합니다.
   - 접근 토큰(OAuth 2.0) 24시간 자동 캐싱(`kis_token.json`)으로 KIS의 "1분당 1회 토큰 발급 제한(EGW00133)"을 방지합니다.
   - 선물 마스터 파일 분석을 통해 만기월에 따라 최근월물 코드(예: `A01612`)를 자동으로 탐색합니다.

2. **엑셀 파일 생성 없이 직접 고품질 PNG 이미지 렌더링**
   - Windows 전용 의존성(`excel2img`, MS Excel COM) 및 엑셀 파일(`.xlsx`) 생성 과정을 완전히 제거했습니다.
   - 순수 Python `Pillow` 엔진과 나눔고딕 폰트 번들(`fonts/`)을 탑재하여, **Windows PC뿐 아니라 오라클 클라우드 리눅스(Oracle Linux/Ubuntu/CentOS) 헤드리스 서버에서도 100% 동일하고 선명한 이미지**를 초고속으로 생성합니다.

3. **이메일 발송 삭제 및 텔레그램 봇 전송 연동**
   - 구형 SMTP 메일 발송 기능을 삭제하고, 생성된 PNG 이미지를 **텔레그램 봇 API(`sendPhoto`)**를 통해 스마트폰으로 즉시 전송합니다.

4. **미국 시장 마감 시간 및 서머타임(DST) 자동 대응 스케줄링**
   - 뉴욕 증시 마감(현지 16:00) 후 5분 뒤(16:05)에 실행되도록 뉴욕 현지 시각(16:xx) 검증 가드를 적용하여, **서머타임 기간(한국 05:05)과 해제 기간(한국 06:05)을 사람이 직접 변경할 필요 없이 사계절 내내 전자동 실행**됩니다.

---

## 📁 디렉터리 구조

```text
07 BeforeSunrise/
├── daily_indicators.py       # 핵심 데이터 수집, 렌더링, 텔레그램 발송 실행 파일
├── deploy_to_oracle.py       # 오라클 제2서버 원클릭 배포 & 동기화 도구
├── run_daily_indicators.bat  # 윈도우 로컬 실행 배치 파일 (상대경로 적용)
├── run_oracle.sh             # 오라클 리눅스 서버 실행 쉘 스크립트
├── requirements.txt          # Python 필수 라이브러리 목록
├── .env                      # API 키 및 텔레그램 설정 (Git 비공개 대상)
├── .env.example              # 환경 변수 설정 템플릿
├── .gitignore                # Git 제외 파일 목록
├── fonts/                    # 크로스 플랫폼 한글 폰트 (나눔고딕)
│   ├── NanumGothic.ttf
│   └── NanumGothicBold.ttf
└── DailyData/                # 결과 이미지 및 데이터 저장 폴더
    ├── BeforeSunrise_YYYY-MM-DD.png
    └── kospif_ngt_history.json
```

---

## 🚀 오라클 서버(Linux) 배포 및 설정 가이드

### 1단계: 배포 도구 이용 (가장 간편한 방법)
로컬 PC에서 아래 명령어를 실행하면 오라클 제2서버(`/home/ubuntu/BeforeSunrise`)로 파일 패키징, 가상환경 구성, 크론탭 스케줄러 등록까지 전자동으로 완료됩니다:
```bash
python deploy_to_oracle.py
```

### 2단계: 수동 클론 방식 이용 시
```bash
# 1. 저장소 클론 (본인의 GitHub 리포지토리 주소 입력)
git clone https://github.com/sonosgg-debug/07_BeforeSunrise.git BeforeSunrise
cd BeforeSunrise

# 2. 실행 권한 부여
chmod +x run_oracle.sh

# 3. Python 가상환경(venv) 생성 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⏰ 미국 시장 마감 5분 후 자동 실행 (Crontab 설정)

서버의 Crontab에 다음과 같이 등록되어 있습니다 (배포 스크립트 실행 시 자동 등록됨):
```cron
# 미국 시장 마감 5분 후 자동 실행 (화~토 아침 05:05 / 06:05 자동 적응)
# - 서머타임 기간(EDT): 05:05 KST 실행 (NY 16:05), 06:05는 자동 스킵
# - 비서머타임 기간(EST): 05:05는 자동 스킵 (NY 15:05), 06:05 KST 실행 (NY 16:05)
# - 토요일/일요일/공휴일(추수감사절, 크리스마스 등)은 자동 감지 후 발송 스킵
5 5,6 * * 2-6 /home/ubuntu/BeforeSunrise/run_oracle.sh --cron
```

### 💡 유용한 명령어
- **원격 서버의 PNG 파일 로컬 다운로드**:
  ```bash
  python deploy_to_oracle.py --pull
  ```
- **휴장 여부 무시하고 즉시 강제 테스트 실행**:
  ```bash
  python daily_indicators.py --force
  ```
