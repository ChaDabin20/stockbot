"""트레이딩 봇 설정"""
import os
from dotenv import load_dotenv

load_dotenv()

# ===== 감시할 종목 =====
# 미국 주식 티커 (Yahoo Finance 기준)
WATCHLIST = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Alphabet
    "AMZN",   # Amazon
    "TSLA",   # Tesla
    "NVDA",   # NVIDIA
    "META",   # Meta
]

# ===== 기술적 지표 설정 =====
INDICATORS = {
    "sma_short": 20,       # 단기 이동평균선
    "sma_long": 50,        # 장기 이동평균선
    "ema_period": 12,      # 지수 이동평균선
    "rsi_period": 14,      # RSI 기간
    "rsi_overbought": 70,  # RSI 과매수 기준
    "rsi_oversold": 30,    # RSI 과매도 기준
    "macd_fast": 12,       # MACD 빠른 선
    "macd_slow": 26,       # MACD 느린 선
    "macd_signal": 9,      # MACD 시그널
    "bb_period": 20,       # 볼린저 밴드 기간
    "bb_std": 2,           # 볼린저 밴드 표준편차
}

# ===== 데이터 설정 =====
DATA_PERIOD = "6mo"        # 가져올 데이터 기간
DATA_INTERVAL = "1d"       # 데이터 간격

# ===== 텔레그램 알림 설정 =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ===== 뉴스 설정 =====
# 무료 뉴스 API (https://newsapi.org 에서 키 발급)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ===== 스케줄링 =====
CHECK_INTERVAL_MINUTES = 30  # 분석 주기 (분)
