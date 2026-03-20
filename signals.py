"""매매 시그널 생성 모듈

기술적 지표와 뉴스 감성을 종합하여 매수/매도 시그널을 생성합니다.
"""
import pandas as pd
from indicators import add_all_indicators, get_latest_indicators
from data_fetcher import get_news_sentiment
import config


class Signal:
    BUY = "매수 🟢"
    SELL = "매도 🔴"
    HOLD = "관망 🟡"
    STRONG_BUY = "강력 매수 🟢🟢"
    STRONG_SELL = "강력 매도 🔴🔴"


def analyze_technical(df: pd.DataFrame) -> list[dict]:
    """기술적 지표 기반 시그널을 분석합니다."""
    df = add_all_indicators(df)
    if df.empty:
        return []

    indicators = get_latest_indicators(df)
    signals = []
    cfg = config.INDICATORS

    price = indicators["price"]

    # 1. 이동평균선 크로스
    if indicators["sma_20"] > indicators["sma_50"]:
        signals.append({"name": "SMA 골든크로스", "signal": Signal.BUY, "weight": 2,
                        "detail": f"SMA20({indicators['sma_20']}) > SMA50({indicators['sma_50']})"})
    elif indicators["sma_20"] < indicators["sma_50"]:
        signals.append({"name": "SMA 데드크로스", "signal": Signal.SELL, "weight": 2,
                        "detail": f"SMA20({indicators['sma_20']}) < SMA50({indicators['sma_50']})"})

    # 2. 가격 vs 이동평균선
    if price > indicators["sma_20"]:
        signals.append({"name": "가격 > SMA20", "signal": Signal.BUY, "weight": 1,
                        "detail": f"현재가({price}) > SMA20({indicators['sma_20']})"})
    else:
        signals.append({"name": "가격 < SMA20", "signal": Signal.SELL, "weight": 1,
                        "detail": f"현재가({price}) < SMA20({indicators['sma_20']})"})

    # 3. RSI
    rsi = indicators["rsi"]
    if rsi < cfg["rsi_oversold"]:
        signals.append({"name": "RSI 과매도", "signal": Signal.BUY, "weight": 3,
                        "detail": f"RSI({rsi}) < {cfg['rsi_oversold']}"})
    elif rsi > cfg["rsi_overbought"]:
        signals.append({"name": "RSI 과매수", "signal": Signal.SELL, "weight": 3,
                        "detail": f"RSI({rsi}) > {cfg['rsi_overbought']}"})
    else:
        signals.append({"name": "RSI 중립", "signal": Signal.HOLD, "weight": 1,
                        "detail": f"RSI({rsi})"})

    # 4. MACD
    if indicators["macd"] > indicators["macd_signal"]:
        signals.append({"name": "MACD 매수 시그널", "signal": Signal.BUY, "weight": 2,
                        "detail": f"MACD({indicators['macd']}) > Signal({indicators['macd_signal']})"})
    else:
        signals.append({"name": "MACD 매도 시그널", "signal": Signal.SELL, "weight": 2,
                        "detail": f"MACD({indicators['macd']}) < Signal({indicators['macd_signal']})"})

    # 5. 볼린저 밴드
    if price <= indicators["bb_lower"]:
        signals.append({"name": "볼린저 밴드 하단 터치", "signal": Signal.BUY, "weight": 2,
                        "detail": f"현재가({price}) ≤ BB하단({indicators['bb_lower']})"})
    elif price >= indicators["bb_upper"]:
        signals.append({"name": "볼린저 밴드 상단 터치", "signal": Signal.SELL, "weight": 2,
                        "detail": f"현재가({price}) ≥ BB상단({indicators['bb_upper']})"})

    # 6. 거래량
    if indicators["volume_ratio"] > 2.0:
        signals.append({"name": "거래량 급증", "signal": Signal.BUY, "weight": 1,
                        "detail": f"거래량 비율: {indicators['volume_ratio']}x"})

    # 7. 스토캐스틱
    if indicators["stoch_k"] < 20 and indicators["stoch_d"] < 20:
        signals.append({"name": "스토캐스틱 과매도", "signal": Signal.BUY, "weight": 1,
                        "detail": f"K({indicators['stoch_k']}), D({indicators['stoch_d']})"})
    elif indicators["stoch_k"] > 80 and indicators["stoch_d"] > 80:
        signals.append({"name": "스토캐스틱 과매수", "signal": Signal.SELL, "weight": 1,
                        "detail": f"K({indicators['stoch_k']}), D({indicators['stoch_d']})"})

    return signals


def calculate_score(technical_signals: list[dict], news_sentiment: dict) -> dict:
    """기술적 시그널과 뉴스 감성을 종합하여 점수를 매깁니다.

    Returns:
        dict with keys: score (-100~100), signal, reasons
    """
    score = 0
    reasons = []

    # 기술적 점수 계산 (가중치 적용)
    for sig in technical_signals:
        weight = sig["weight"]
        if sig["signal"] in (Signal.BUY, Signal.STRONG_BUY):
            score += weight * 10
            reasons.append(f"  ✅ {sig['name']}: {sig['detail']}")
        elif sig["signal"] in (Signal.SELL, Signal.STRONG_SELL):
            score -= weight * 10
            reasons.append(f"  ❌ {sig['name']}: {sig['detail']}")
        else:
            reasons.append(f"  ➖ {sig['name']}: {sig['detail']}")

    # 뉴스 감성 점수 (최대 ±20점)
    news_score = news_sentiment["score"] * 20
    score += news_score
    if news_sentiment["count"] > 0:
        reasons.append(f"  📰 뉴스 감성: {news_sentiment['label']} (점수: {news_sentiment['score']}, 기사 {news_sentiment['count']}건)")

    # 점수 정규화 (-100 ~ 100)
    score = max(-100, min(100, score))

    # 종합 시그널 결정
    if score >= 50:
        signal = Signal.STRONG_BUY
    elif score >= 20:
        signal = Signal.BUY
    elif score <= -50:
        signal = Signal.STRONG_SELL
    elif score <= -20:
        signal = Signal.SELL
    else:
        signal = Signal.HOLD

    # 추천 이유 요약 생성
    summary = _generate_summary(signal, round(score, 1), technical_signals, news_sentiment)

    return {
        "score": round(score, 1),
        "signal": signal,
        "reasons": reasons,
        "summary": summary,
    }


def _generate_summary(signal: str, score: float, tech_signals: list[dict], news_sentiment: dict) -> str:
    """사람이 읽기 쉬운 추천 이유 요약을 생성합니다."""
    buy_reasons = []
    sell_reasons = []

    for sig in tech_signals:
        if sig["signal"] in (Signal.BUY, Signal.STRONG_BUY):
            buy_reasons.append(sig["name"])
        elif sig["signal"] in (Signal.SELL, Signal.STRONG_SELL):
            sell_reasons.append(sig["name"])

    def join_reasons(reasons: list[str]) -> str:
        if len(reasons) == 1:
            return reasons[0]
        return ", ".join(reasons[:-1]) + " 및 " + reasons[-1]

    parts = []
    news_count = news_sentiment["count"]
    news_score = news_sentiment["score"]

    if "강력 매수" in signal:
        parts.append(f"종합 {score}점 → 강력 매수 추천.")
        if buy_reasons:
            parts.append(f"{join_reasons(buy_reasons)} 등 다수 지표가 상승 신호를 보이고 있습니다.")
        if news_count > 0 and news_score > 0.1:
            parts.append(f"최근 뉴스 {news_count}건도 긍정적 분위기입니다.")

    elif "매수" in signal:
        parts.append(f"종합 {score}점 → 매수 추천.")
        if buy_reasons:
            parts.append(f"{join_reasons(buy_reasons)}에서 매수 신호가 감지되었습니다.")
        if sell_reasons:
            parts.append(f"다만 {join_reasons(sell_reasons)}은 주의가 필요합니다.")
        if news_count > 0:
            if news_score > 0.1:
                parts.append("뉴스 분위기도 우호적입니다.")
            elif news_score < -0.1:
                parts.append("단, 뉴스 분위기는 다소 부정적입니다.")

    elif "강력 매도" in signal:
        parts.append(f"종합 {score}점 → 강력 매도 추천.")
        if sell_reasons:
            parts.append(f"{join_reasons(sell_reasons)} 등 다수 지표가 하락 신호를 보이고 있습니다.")
        if news_count > 0 and news_score < -0.1:
            parts.append("뉴스 분위기도 부정적입니다.")

    elif "매도" in signal:
        parts.append(f"종합 {score}점 → 매도 추천.")
        if sell_reasons:
            parts.append(f"{join_reasons(sell_reasons)}에서 매도 신호가 감지되었습니다.")
        if buy_reasons:
            parts.append(f"다만 {join_reasons(buy_reasons)}은 긍정적 요소입니다.")

    else:  # 관망
        parts.append(f"종합 {score}점 → 관망 추천.")
        parts.append("매수/매도 신호가 혼재되어 추세를 더 지켜보는 것이 좋겠습니다.")
        if buy_reasons:
            parts.append(f"긍정: {join_reasons(buy_reasons)}.")
        if sell_reasons:
            parts.append(f"부정: {join_reasons(sell_reasons)}.")

    return " ".join(parts)


def analyze_ticker(ticker: str) -> dict:
    """종목 하나를 종합 분석합니다."""
    from data_fetcher import fetch_stock_data, fetch_stock_info

    # 데이터 수집
    df = fetch_stock_data(ticker)
    if df.empty:
        return {"ticker": ticker, "error": "데이터 없음"}

    info = fetch_stock_info(ticker)
    df_with_indicators = add_all_indicators(df)
    indicators = get_latest_indicators(df_with_indicators)

    # 기술적 분석
    tech_signals = analyze_technical(df)

    # 뉴스 감성 분석
    news_sentiment = get_news_sentiment(ticker)

    # 종합 점수
    result = calculate_score(tech_signals, news_sentiment)

    return {
        "ticker": ticker,
        "name": info.get("name", ticker),
        "indicators": indicators,
        "technical_signals": tech_signals,
        "news_sentiment": news_sentiment,
        "score": result["score"],
        "signal": result["signal"],
        "reasons": result["reasons"],
        "df": df_with_indicators,
    }


def analyze_all() -> list[dict]:
    """감시 목록의 모든 종목을 분석합니다."""
    results = []
    for ticker in config.WATCHLIST:
        print(f"[분석 중] {ticker}...")
        result = analyze_ticker(ticker)
        results.append(result)
    return results
