@echo off
cd /d "d:\AI Investing\07 MorningWatch"
:: Python script runs and logs output
python daily_indicators.py >> execution.log 2>&1
exit
