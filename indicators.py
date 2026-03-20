"""기술적 지표 계산 모듈"""
import pandas as pd
import numpy as np
import ta
import config


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """데이터프레임에 모든 기술적 지표를 추가합니다."""
    if df.empty or len(df) < 30:
        return df

    df = df.copy()
    cfg = config.INDICATORS

    # === 이동평균선 (SMA) ===
    df["SMA_20"] = ta.trend.sma_indicator(df["Close"], window=cfg["sma_short"])
    df["SMA_50"] = ta.trend.sma_indicator(df["Close"], window=cfg["sma_long"])

    # === 지수 이동평균선 (EMA) ===
    df["EMA_12"] = ta.trend.ema_indicator(df["Close"], window=cfg["ema_period"])
    df["EMA_26"] = ta.trend.ema_indicator(df["Close"], window=26)

    # === RSI ===
    df["RSI"] = ta.momentum.rsi(df["Close"], window=cfg["rsi_period"])

    # === MACD ===
    macd = ta.trend.MACD(
        df["Close"],
        window_slow=cfg["macd_slow"],
        window_fast=cfg["macd_fast"],
        window_sign=cfg["macd_signal"],
    )
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()

    # === 볼린저 밴드 ===
    bb = ta.volatility.BollingerBands(
        df["Close"],
        window=cfg["bb_period"],
        window_dev=cfg["bb_std"],
    )
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Lower"] = bb.bollinger_lband()

    # === 거래량 지표 ===
    df["Volume_SMA"] = df["Volume"].rolling(window=20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA"]

    # === 스토캐스틱 ===
    stoch = ta.momentum.StochasticOscillator(
        df["High"], df["Low"], df["Close"],
        window=14, smooth_window=3,
    )
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # === ATR (평균 실제 범위) ===
    df["ATR"] = ta.volatility.average_true_range(
        df["High"], df["Low"], df["Close"], window=14
    )

    return df


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """최신 지표값들을 딕셔너리로 반환합니다."""
    if df.empty:
        return {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    return {
        "price": round(latest["Close"], 2),
        "change_pct": round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2),
        "sma_20": round(latest.get("SMA_20", 0), 2),
        "sma_50": round(latest.get("SMA_50", 0), 2),
        "ema_12": round(latest.get("EMA_12", 0), 2),
        "rsi": round(latest.get("RSI", 0), 2),
        "macd": round(latest.get("MACD", 0), 4),
        "macd_signal": round(latest.get("MACD_Signal", 0), 4),
        "macd_hist": round(latest.get("MACD_Hist", 0), 4),
        "bb_upper": round(latest.get("BB_Upper", 0), 2),
        "bb_middle": round(latest.get("BB_Middle", 0), 2),
        "bb_lower": round(latest.get("BB_Lower", 0), 2),
        "volume_ratio": round(latest.get("Volume_Ratio", 0), 2),
        "stoch_k": round(latest.get("Stoch_K", 0), 2),
        "stoch_d": round(latest.get("Stoch_D", 0), 2),
        "atr": round(latest.get("ATR", 0), 2),
    }
