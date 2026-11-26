@echo off
cd /d "%~dp0"
:: Python script runs and logs output
python daily_indicators.py >> execution.log 2>&1
exit
