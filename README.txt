==============================================
Daily Investment Indicators Automation Guide
==============================================

[필수 설정: 자동 이메일 발송]
실행된 엑셀 파일을 매일 이메일로 받으려면 발신자 이메일 계정을 설정해야 합니다.
1. 이 폴더에 있는 `.env.example` 파일의 이름을 `.env` 로 변경합니다.
2. 메모장으로 `.env` 파일을 열고 다음과 같이 본인의 발신자 이메일과 비밀번호(또는 앱 비밀번호)를 입력하세요.
   * 네이버나 구글 메일의 경우 보안 설정에서 "앱 비밀번호"를 생성하여 입력하는 것을 권장합니다.
     EMAIL_SENDER="myemail@naver.com"
     EMAIL_PASSWORD="my_app_password"
   * 만약 이메일 발송 기능을 원치 않으시거나 나중에 설정하시려면 이 과정을 생략하셔도 됩니다. 프로그램은 엑셀 파일만 생성하고 종료됩니다.

[자동 실행 스케줄러 설정]

To run the script automatically every day at 7:00 AM, please follow these steps:

1. Open Windows Start Menu, search for "Task Scheduler" (작업 스케줄러) and open it.
2. In the right pane, click "Create Basic Task..." (기본 작업 만들기...).
3. Name the task (e.g., "Daily Investment Indicators") and click Next.
4. For Trigger, select "Daily" (매일) and click Next.
5. Set the start time to 07:00:00 AM and click Next.
6. For Action, select "Start a program" (프로그램 시작) and click Next.
7. Click "Browse..." (찾아보기...) and select the file:
   d:\AI Investing\Daily_Check\run_daily_indicators.bat
8. (Important) In the "Start in (optional)" field (시작 위치(선택 사항)), enter:
   d:\AI Investing\Daily_Check\
9. Click "Finish" (마침).

Now, the program will automatically run every day at 7:00 AM, fetch the data, and create a new styled Excel file in the "d:\AI Investing\Daily_Check\" folder.

Note:
* The KOSPI 200 Night Futures data is now reliably fetched from esignal.co.kr.
* If your email credentials are not set in the `.env` file, the script will gracefully skip the email sending portion and still generate the Excel file.
