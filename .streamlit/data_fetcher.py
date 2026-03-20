"""주식 데이터 및 뉴스 수집 모듈"""
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from datetime import datetime, timedelta
import config


def fetch_stock_data(ticker: str, period: str = None, interval: str = None) -> pd.DataFrame:
    """Yahoo Finance에서 주식 데이터를 가져옵니다."""
    import time
    period = period or config.DATA_PERIOD
    interval = interval or config.DATA_INTERVAL

    stock = yf.Ticker(ticker)
    for attempt in range(3):
        try:
            df = stock.history(period=period, interval=interval)
            if df.empty:
                print(f"[경고] {ticker}: 데이터를 가져올 수 없습니다.")
                return pd.DataFrame()
            return df
        except Exception as e:
            if "Rate" in str(type(e).__name__) or "rate" in str(e).lower():
                wait = (attempt + 1) * 5
                print(f"[대기] {ticker}: API 요청 제한, {wait}초 대기 중...")
                time.sleep(wait)
            else:
                print(f"[경고] {ticker}: 데이터 조회 실패 - {e}")
                return pd.DataFrame()

    print(f"[경고] {ticker}: 재시도 초과")
    return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    """종목의 기본 정보를 가져옵니다."""
    import time
    time.sleep(0.5)
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        return {
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "current_price": info.get("currentPrice", 0),
        }
    except Exception as e:
        print(f"[경고] {ticker} 정보 조회 실패: {e}")
        return {"name": ticker}


def fetch_news_newsapi(ticker: str, days: int = 3) -> list[dict]:
    """NewsAPI에서 뉴스를 가져옵니다."""
    if not config.NEWS_API_KEY:
        return []

    url = "https://newsapi.org/v2/everything"
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "q": ticker,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": 10,
        "apiKey": config.NEWS_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        return [
            {
                "title": a["title"],
                "description": a.get("description", ""),
                "url": a["url"],
                "published": a.get("publishedAt", ""),
                "source": a.get("source", {}).get("name", ""),
            }
            for a in articles
            if a.get("title")
        ]
    except Exception as e:
        print(f"[경고] 뉴스 API 오류: {e}")
        return []


def fetch_news_yfinance(ticker: str) -> list[dict]:
    """Yahoo Finance에서 뉴스를 가져옵니다 (API 키 불필요)."""
    stock = yf.Ticker(ticker)
    try:
        news = stock.news or []
        results = []
        for n in news[:10]:
            # 새로운 yfinance 응답 구조: content 안에 중첩
            content = n.get("content", n)
            title = content.get("title", "")
            if not title:
                continue

            summary = content.get("summary", content.get("description", ""))
            provider = content.get("provider", {})
            source = provider.get("displayName", "") if isinstance(provider, dict) else ""
            pub_date = content.get("pubDate", content.get("displayTime", ""))
            # URL 추출
            click_url = content.get("clickThroughUrl", {})
            url = click_url.get("url", "") if isinstance(click_url, dict) else ""
            if not url:
                canonical = content.get("canonicalUrl", {})
                url = canonical.get("url", "") if isinstance(canonical, dict) else ""

            results.append({
                "title": title,
                "description": summary,
                "url": url,
                "published": pub_date[:16] if pub_date else "",
                "source": source,
            })
        return results
    except Exception as e:
        print(f"[경고] Yahoo 뉴스 조회 실패: {e}")
        return []


def fetch_news(ticker: str) -> list[dict]:
    """뉴스를 가져옵니다. NewsAPI가 설정되어 있으면 사용, 없으면 Yahoo Finance."""
    if config.NEWS_API_KEY:
        news = fetch_news_newsapi(ticker)
        if news:
            return news
    return fetch_news_yfinance(ticker)


def analyze_sentiment(text: str) -> float:
    """텍스트의 감성 점수를 반환합니다 (-1.0 ~ 1.0)."""
    if not text:
        return 0.0
    blob = TextBlob(text)
    return blob.sentiment.polarity


def get_news_sentiment(ticker: str) -> dict:
    """종목의 뉴스 감성을 분석합니다."""
    news = fetch_news(ticker)
    if not news:
        return {"score": 0.0, "label": "중립", "count": 0, "articles": []}

    sentiments = []
    analyzed_articles = []

    for article in news:
        text = f"{article['title']} {article.get('description', '')}"
        score = analyze_sentiment(text)
        sentiments.append(score)
        article["sentiment"] = score
        analyzed_articles.append(article)

    avg_score = sum(sentiments) / len(sentiments) if sentiments else 0.0

    if avg_score > 0.1:
        label = "긍정적 🟢"
    elif avg_score < -0.1:
        label = "부정적 🔴"
    else:
        label = "중립 🟡"

    return {
        "score": round(avg_score, 3),
        "label": label,
        "count": len(news),
        "articles": analyzed_articles,
    }
