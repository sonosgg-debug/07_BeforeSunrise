# MorningWatch (일일 투자 지표 자동 발송 봇)

매일 아침 글로벌 주요 17대 투자 지표(미국 지수, 반도체, 원자재, 환율, 금리, 비트코인 및 **KOSPI200 야간 선물 지수**)를 자동 수집하고, 고품질 대시보드 테이블 이미지(PNG)를 생성하여 **텔레그램 채널/개인 챗**으로 전송하는 자동화 애플리케이션입니다.

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
   - 뉴욕 증시 마감(현지 16:00) 후 5분 뒤(16:05)에 실행되도록 리눅스 `crontab`에 `CRON_TZ=America/New_York` 시간대 설정을 적용하여, **서머타임 기간(한국 05:05)과 해제 기간(한국 06:05)을 사람이 직접 변경할 필요 없이 사계절 내내 전자동 실행**됩니다.

---

## 📁 디렉터리 구조

```text
07 MorningWatch/
├── daily_indicators.py       # 핵심 데이터 수집, 렌더링, 텔레그램 발송 실행 파일
├── run_oracle.sh             # 오라클 리눅스 서버 실행 쉘 스크립트
├── requirements.txt          # Python 필수 라이브러리 목록
├── .env                      # API 키 및 텔레그램 설정 (Git 비공개 대상)
├── .env.example              # 환경 변수 설정 템플릿
├── .gitignore                # Git 제외 파일 목록
├── fonts/                    # 크로스 플랫폼 한글 폰트 (나눔고딕)
│   ├── NanumGothic.ttf
│   └── NanumGothicBold.ttf
└── DailyData/                # 결과 이미지 및 데이터 저장 폴더
    ├── MorningWatch_YYYY-MM-DD.png
    └── kospif_ngt_history.json
```

---

## 🚀 오라클 서버(Linux) 배포 및 설정 가이드

### 1단계: GitHub에 코드 올리기 (PC에서 진행)
`.env` 파일과 민감 정보는 `.gitignore`에 의해 제외되므로 안심하고 푸시하세요:
```bash
git add .
git commit -m "Update KIS API, direct PNG rendering, and Telegram bot integration"
git push origin main
```

### 2단계: 오라클 서버에서 코드 클론 및 환경 설정
오라클 서버 터미널(SSH)에 접속하여 진행합니다:

```bash
# 1. 저장소 클론 (본인의 GitHub 리포지토리 주소 입력)
git clone https://github.com/your-id/MorningWatch.git
cd MorningWatch

# 2. 실행 권한 부여
chmod +x run_oracle.sh

# 3. Python 가상환경(venv) 생성 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3단계: 환경 변수(`.env`) 설정
오라클 서버에 `.env` 파일을 생성하고 본인의 API 키를 입력합니다:

```bash
nano .env
```
내용 작성 예시:
```env
# 1. 한국투자증권(KIS) 실전 계정 키
KIS_APP_KEY=PSBf...
KIS_APP_SECRET=9d82...

# 2. 텔레그램 봇 토큰 및 수신 Chat ID
TELEGRAM_BOT_TOKEN=9253423656:AAFCWLZn...
TELEGRAM_CHAT_ID=5638262425
```
*(저장: `Ctrl + O` -> `Enter`, 종료: `Ctrl + X`)*

### 4단계: 테스트 실행
오라클 서버에서 정상 작동하는지 수동으로 실행해 봅니다:
```bash
./run_oracle.sh
```
텔레그램 방으로 오늘 자 투자 지표 이미지가 도착하면 정상 설정된 것입니다.

---

## ⏰ 미국 시장 마감 5분 후 자동 실행 (Crontab 설정)

미국 정규 주식 시장은 현지 시각(US/Eastern)으로 **월~금 09:30 ~ 16:00**에 열립니다.
마감 5분 후 시점은 **현지 시각 16:05 (월~금)**입니다.
- **서머타임 기간 (3월 둘째 일요일 ~ 11월 첫째 일요일):** 한국 시각 **05:05**
- **비서머타임 기간 (겨울철 표준시):** 한국 시각 **06:05**

오라클 서버의 `crontab`에 시간대(`CRON_TZ`)를 지정하면, **서머타임 변경 시기를 신경 쓰지 않아도 사계절 내내 마감 5분 뒤에 정확히 실행**됩니다.

### 크론탭(crontab) 등록 방법:
터미널에서 크론탭 편집기를 엽니다:
```bash
crontab -e
```

파일 맨 아래에 다음 내용을 추가합니다 (경로는 본인 서버 경로에 맞게 지정):
```cron
# 미국 동부 시간(New York) 기준 월~금요일 16:05 (마감 5분 후)
# -> 한국 시간 기준 화~토요일 아침 (서머타임 시 05:05, 해제 시 06:05 자동 적용)
CRON_TZ=America/New_York
5 16 * * 1-5 /home/ubuntu/MorningWatch/run_oracle.sh >> /home/ubuntu/MorningWatch/execution.log 2>&1
```

> 💡 **참고**:
> 혹시 서버의 cron이 `CRON_TZ` 문법을 지원하지 않는 환경(아주 구형 cron)인 경우, 한국 시간(KST) 기준으로 다음과 같이 등록하실 수 있습니다:
> - 비서머타임 시기: `5 6 * * 2-6 /home/ubuntu/MorningWatch/run_oracle.sh ...` (화~토 06:05)
> - 서머타임 시기: `5 5 * * 2-6 /home/ubuntu/MorningWatch/run_oracle.sh ...` (화~토 05:05)
