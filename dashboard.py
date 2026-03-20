"""트레이딩 봇 웹앱 대시보드

멀티페이지 구성:
  1. 홈 - 전체 종목 요약 카드
  2. 상세 분석 - 개별 종목 차트/지표/뉴스
  3. 종목 비교 - 여러 종목 나란히 비교
  4. 설정 - 감시 목록, 지표 파라미터 조정
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime

from data_fetcher import fetch_stock_data, fetch_stock_info, get_news_sentiment
from indicators import add_all_indicators, get_latest_indicators
from signals import analyze_technical, calculate_score, Signal
import config

# ===== 페이지 설정 =====
st.set_page_config(
    page_title="Dabin's StockBot V1 - 주식 트레이딩 봇",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": "### 📊 Dabin's StockBot V1\n기술적 지표 + 뉴스 감성 기반 주식 분석 봇\n\n**Made by Dabin Cha**",
    },
)

# ===== 커스텀 CSS =====
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background: linear-gradient(180deg, #0e1117 0%, #1a1d23 100%);
    }

    /* 상단 헤더 */
    .main-header {
        background: linear-gradient(90deg, #1e3a5f, #2d5a87);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
    }
    .main-header p {
        color: #a0c4e8;
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }

    /* 종목 카드 */
    .stock-card {
        background: linear-gradient(135deg, #1e2530 0%, #2a3441 100%);
        border: 1px solid #3a4a5a;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stock-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    .stock-card .ticker {
        font-size: 1.4rem;
        font-weight: bold;
        color: #e0e0e0;
    }
    .stock-card .name {
        font-size: 0.85rem;
        color: #8899aa;
    }
    .stock-card .price {
        font-size: 1.6rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }

    /* 시그널 뱃지 */
    .signal-buy {
        background: linear-gradient(135deg, #1b5e20, #2e7d32);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        font-size: 0.85rem;
    }
    .signal-sell {
        background: linear-gradient(135deg, #b71c1c, #c62828);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        font-size: 0.85rem;
    }
    .signal-hold {
        background: linear-gradient(135deg, #e65100, #f57c00);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        font-size: 0.85rem;
    }

    /* 점수 바 */
    .score-bar {
        background: #2a2a2a;
        border-radius: 10px;
        height: 8px;
        margin: 0.5rem 0;
        overflow: hidden;
    }
    .score-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }

    /* 뉴스 카드 */
    .news-item {
        background: #1e2530;
        border-left: 3px solid #2d5a87;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
    }
    .news-item.positive { border-left-color: #4caf50; }
    .news-item.negative { border-left-color: #f44336; }
    .news-item.neutral  { border-left-color: #ff9800; }

    /* 네비게이션 */
    .nav-container {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }

    /* 지표 미니카드 */
    .indicator-mini {
        background: #1e2530;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        text-align: center;
        border: 1px solid #3a4a5a;
    }
    .indicator-mini .label {
        font-size: 0.75rem;
        color: #8899aa;
    }
    .indicator-mini .value {
        font-size: 1.1rem;
        font-weight: bold;
        color: #e0e0e0;
    }

    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background: #151921;
    }

    /* Streamlit 기본 브랜딩 숨기기 */
    footer {visibility: hidden;}
    div[data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    /* 헤더: 앱 배경색과 맞추고 사이드바 토글 버튼은 보이게 유지 */
    header[data-testid="stHeader"] {
        background: #0e1117 !important;
        border-bottom: 1px solid #2a3441 !important;
    }
    /* Streamlit 워터마크/브랜딩만 숨기기 */
    header[data-testid="stHeader"] a[href*="streamlit"] {display: none !important;}
    div[data-testid="stMainMenuPopover"] {display: none !important;}
</style>
""", unsafe_allow_html=True)


# ===== 데이터 로딩 (캐싱) =====
@st.cache_data(ttl=300)
def load_analysis(ticker: str, period: str):
    df = fetch_stock_data(ticker, period=period)
    if df.empty:
        return None

    info = fetch_stock_info(ticker)
    df = add_all_indicators(df)
    indicators = get_latest_indicators(df)
    raw_df = fetch_stock_data(ticker, period=period)
    tech_signals = analyze_technical(raw_df)
    news = get_news_sentiment(ticker)
    score_result = calculate_score(tech_signals, news)

    return {
        "df": df,
        "info": info,
        "indicators": indicators,
        "tech_signals": tech_signals,
        "news": news,
        "score": score_result,
    }


# ===== 사이드바 =====
with st.sidebar:
    st.markdown("## 📊 Dabin's StockBot V1")
    st.divider()

    # 페이지 네비게이션
    page = st.radio(
        "메뉴",
        ["🏠 홈", "📈 상세 분석", "⚖️ 종목 비교", "📰 뉴스센터", "⚙️ 설정"],
        label_visibility="collapsed",
    )

    st.divider()

    # 감시 종목
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = config.WATCHLIST.copy()

    selected_tickers = st.multiselect(
        "감시 종목",
        options=st.session_state.watchlist,
        default=st.session_state.watchlist[:4],
    )

    # 종목 추가
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        new_ticker = st.text_input("추가", placeholder="티커 입력", label_visibility="collapsed")
    with col_add2:
        if st.button("➕", use_container_width=True):
            if new_ticker:
                ticker_upper = new_ticker.upper()
                if ticker_upper not in st.session_state.watchlist:
                    st.session_state.watchlist.append(ticker_upper)
                if ticker_upper not in selected_tickers:
                    selected_tickers.append(ticker_upper)
                st.rerun()

    st.divider()

    # 데이터 기간
    period = st.selectbox("📅 기간", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

    # 새로고침
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ===== 유틸리티 함수 =====
def get_signal_badge(signal: str) -> str:
    if "매수" in signal:
        return f'<span class="signal-buy">{signal}</span>'
    elif "매도" in signal:
        return f'<span class="signal-sell">{signal}</span>'
    else:
        return f'<span class="signal-hold">{signal}</span>'


def get_score_color(score: float) -> str:
    if score >= 30:
        return "#4caf50"
    elif score >= 0:
        return "#8bc34a"
    elif score >= -30:
        return "#ff9800"
    else:
        return "#f44336"


def get_change_color(change: float) -> str:
    return "#4caf50" if change >= 0 else "#f44336"


def render_stock_card(ticker: str, data: dict):
    """종목 카드를 렌더링합니다."""
    ind = data["indicators"]
    score = data["score"]
    info = data["info"]
    change_color = get_change_color(ind["change_pct"])
    score_color = get_score_color(score["score"])
    score_pct = (score["score"] + 100) / 2  # -100~100 -> 0~100%

    st.markdown(f"""
    <div class="stock-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="ticker">{ticker}</span>
                <span class="name"> · {info.get('name', '')}</span>
            </div>
            {get_signal_badge(score['signal'])}
        </div>
        <div class="price" style="color:{change_color}">
            ${ind['price']}
            <span style="font-size:0.9rem;">({ind['change_pct']:+.2f}%)</span>
        </div>
        <div class="score-bar">
            <div class="score-fill" style="width:{score_pct}%; background:{score_color};"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#8899aa;">
            <span>점수: {score['score']}점</span>
            <span>RSI: {ind['rsi']}</span>
            <span>거래량: {ind['volume_ratio']}x</span>
        </div>
        <div style="font-size:0.8rem; color:#b0bec5; margin-top:0.6rem; padding-top:0.5rem; border-top:1px solid #3a4a5a;">
            💡 {score.get('summary', '')}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_chart(df: pd.DataFrame, ticker: str, show_bb: bool = True, show_ma: bool = True):
    """인터랙티브 차트를 렌더링합니다."""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("", "", "RSI", "MACD"),
        row_heights=[0.45, 0.15, 0.2, 0.2],
    )

    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="가격",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ), row=1, col=1)

    # 이동평균선
    if show_ma:
        if "SMA_20" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["SMA_20"], name="SMA 20",
                line=dict(color="#ff9800", width=1.2),
            ), row=1, col=1)
        if "SMA_50" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["SMA_50"], name="SMA 50",
                line=dict(color="#2196f3", width=1.2),
            ), row=1, col=1)

    # 볼린저 밴드
    if show_bb and "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"], name="BB 상단",
            line=dict(color="rgba(150,150,150,0.5)", width=1, dash="dot"),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"], name="BB 하단",
            line=dict(color="rgba(150,150,150,0.5)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(100,150,200,0.06)",
        ), row=1, col=1)

    # 거래량
    vol_colors = ["#ef5350" if c < o else "#26a69a"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="거래량",
        marker_color=vol_colors, opacity=0.5,
    ), row=2, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#ab47bc", width=1.5),
        ), row=3, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(244,67,54,0.1)",
                      line_width=0, row=3, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="rgba(76,175,80,0.1)",
                      line_width=0, row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(244,67,54,0.5)",
                      row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(76,175,80,0.5)",
                      row=3, col=1)

    # MACD
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"], name="MACD",
            line=dict(color="#2196f3", width=1.5),
        ), row=4, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_Signal"], name="Signal",
            line=dict(color="#ff9800", width=1.5),
        ), row=4, col=1)
        macd_colors = ["#26a69a" if v >= 0 else "#ef5350"
                       for v in df["MACD_Hist"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACD_Hist"], name="Histogram",
            marker_color=macd_colors, opacity=0.4,
        ), row=4, col=1)

    fig.update_layout(
        height=850,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,0.8)",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    font=dict(size=10)),
        margin=dict(l=50, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor="rgba(50,50,50,0.5)")
    fig.update_yaxes(gridcolor="rgba(50,50,50,0.5)")

    return fig


# ================================================================
#                         페이지 렌더링
# ================================================================

# ===== 🏠 홈 =====
if page == "🏠 홈":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Dabin's StockBot V1 트레이딩 대시보드</h1>
        <p>기술적 지표 + 뉴스 감성 기반 주식 분석</p>
    </div>
    """, unsafe_allow_html=True)

    if not selected_tickers:
        st.info("👈 사이드바에서 감시할 종목을 선택하세요.")
    else:
        # 요약 통계
        all_data = {}
        buy_count = sell_count = hold_count = 0

        with st.spinner("데이터를 불러오는 중..."):
            for ticker in selected_tickers:
                data = load_analysis(ticker, period)
                if data:
                    all_data[ticker] = data
                    sig = data["score"]["signal"]
                    if "매수" in sig:
                        buy_count += 1
                    elif "매도" in sig:
                        sell_count += 1
                    else:
                        hold_count += 1

        # 상단 요약
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("감시 종목", f"{len(all_data)}개")
        m2.metric("매수 시그널", f"{buy_count}개", delta=f"{buy_count}개" if buy_count else None)
        m3.metric("매도 시그널", f"{sell_count}개", delta=f"-{sell_count}개" if sell_count else None, delta_color="inverse")
        m4.metric("관망", f"{hold_count}개")

        st.divider()

        # 종목 카드 그리드
        cols = st.columns(2)
        for i, (ticker, data) in enumerate(all_data.items()):
            with cols[i % 2]:
                render_stock_card(ticker, data)

        # 점수 랭킹 차트
        st.divider()
        st.subheader("🏆 종목 점수 랭킹")

        ranking_data = sorted(all_data.items(), key=lambda x: x[1]["score"]["score"], reverse=True)
        tickers_sorted = [t for t, _ in ranking_data]
        scores_sorted = [d["score"]["score"] for _, d in ranking_data]
        colors_sorted = [get_score_color(s) for s in scores_sorted]

        fig_rank = go.Figure(go.Bar(
            x=scores_sorted, y=tickers_sorted,
            orientation="h",
            marker_color=colors_sorted,
            text=[f"{s}점" for s in scores_sorted],
            textposition="outside",
        ))
        fig_rank.update_layout(
            height=max(200, len(tickers_sorted) * 50),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(range=[-100, 100], title="종합 점수"),
            yaxis=dict(autorange="reversed"),
            margin=dict(l=80, r=80, t=20, b=40),
        )
        fig_rank.add_vline(x=0, line_color="gray", line_dash="dash")
        st.plotly_chart(fig_rank, use_container_width=True)


# ===== 📈 상세 분석 =====
elif page == "📈 상세 분석":
    st.markdown("""
    <div class="main-header">
        <h1>📈 상세 종목 분석</h1>
        <p>차트, 기술적 지표, 뉴스 감성을 한눈에</p>
    </div>
    """, unsafe_allow_html=True)

    if not selected_tickers:
        st.info("👈 사이드바에서 종목을 선택하세요.")
    else:
        # 종목 선택 탭
        detail_ticker = st.selectbox(
            "분석할 종목", selected_tickers,
            format_func=lambda t: f"{t}",
        )

        data = load_analysis(detail_ticker, period)
        if data is None:
            st.error(f"{detail_ticker}: 데이터를 불러올 수 없습니다.")
        else:
            df = data["df"]
            ind = data["indicators"]
            score = data["score"]
            info = data["info"]

            # 상단 종목 정보
            h1, h2, h3, h4, h5 = st.columns(5)
            change_delta = f"{ind['change_pct']:+.2f}%"
            h1.metric(f"{detail_ticker}", f"${ind['price']}", change_delta)
            h2.metric("RSI", ind["rsi"])
            h3.metric("MACD", ind["macd"])
            h4.metric("거래량 비율", f"{ind['volume_ratio']}x")
            h5.metric("종합 점수", f"{score['score']}점")

            # 차트 옵션
            opt1, opt2 = st.columns(2)
            with opt1:
                show_bb = st.checkbox("볼린저 밴드", value=True)
            with opt2:
                show_ma = st.checkbox("이동평균선", value=True)

            # 메인 차트
            fig = render_chart(df, detail_ticker, show_bb=show_bb, show_ma=show_ma)
            st.plotly_chart(fig, use_container_width=True)

            # 하단 3열: 지표 | 시그널 | 뉴스
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("### 📊 기술적 지표")

                # 미니 카드 형태
                mc1, mc2 = st.columns(2)
                with mc1:
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">SMA 20</div>
                        <div class="value">${ind['sma_20']}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">SMA 50</div>
                        <div class="value">${ind['sma_50']}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">BB 상단</div>
                        <div class="value">${ind['bb_upper']}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">스토캐스틱 K</div>
                        <div class="value">{ind['stoch_k']}</div>
                    </div>""", unsafe_allow_html=True)
                with mc2:
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">RSI</div>
                        <div class="value" style="color:{'#f44336' if ind['rsi']>70 else '#4caf50' if ind['rsi']<30 else '#e0e0e0'}">{ind['rsi']}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">MACD</div>
                        <div class="value">{ind['macd']}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">BB 하단</div>
                        <div class="value">${ind['bb_lower']}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="indicator-mini">
                        <div class="label">ATR</div>
                        <div class="value">{ind['atr']}</div>
                    </div>""", unsafe_allow_html=True)

            with col2:
                st.markdown("### 🚦 시그널")

                for sig in data["tech_signals"]:
                    if "매수" in sig["signal"]:
                        st.success(f"**{sig['name']}**  \n{sig['detail']}")
                    elif "매도" in sig["signal"]:
                        st.error(f"**{sig['name']}**  \n{sig['detail']}")
                    else:
                        st.warning(f"**{sig['name']}**  \n{sig['detail']}")

                st.divider()

                # 게이지
                gauge_fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score["score"],
                    title={"text": "종합 점수", "font": {"color": "white"}},
                    number={"font": {"color": "white"}},
                    gauge={
                        "axis": {"range": [-100, 100], "tickcolor": "gray"},
                        "bar": {"color": "#2196f3"},
                        "bgcolor": "#1e2530",
                        "steps": [
                            {"range": [-100, -50], "color": "#b71c1c"},
                            {"range": [-50, -20], "color": "#e65100"},
                            {"range": [-20, 20], "color": "#f9a825"},
                            {"range": [20, 50], "color": "#558b2f"},
                            {"range": [50, 100], "color": "#1b5e20"},
                        ],
                    },
                ))
                gauge_fig.update_layout(
                    height=220,
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=30, r=30, t=50, b=10),
                )
                st.plotly_chart(gauge_fig, use_container_width=True)
                st.markdown(f"### {get_signal_badge(score['signal'])}", unsafe_allow_html=True)

                # 추천 이유 요약
                summary_text = score.get("summary", "")
                if summary_text:
                    st.markdown(f"""
                    <div style="background:#1a2332; border:1px solid #2d5a87; border-radius:8px; padding:1rem; margin-top:0.8rem;">
                        <div style="font-size:0.8rem; color:#64b5f6; font-weight:bold; margin-bottom:0.4rem;">💡 추천 이유</div>
                        <div style="font-size:0.85rem; color:#cfd8dc; line-height:1.5;">
                            {summary_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col3:
                st.markdown("### 📰 뉴스 감성")
                news = data["news"]

                # 감성 요약
                st.markdown(f"**{news['label']}** (점수: {news['score']}, {news['count']}건)")

                if news["articles"]:
                    for article in news["articles"][:6]:
                        sent = article.get("sentiment", 0)
                        if sent > 0.1:
                            css_class = "positive"
                        elif sent < -0.1:
                            css_class = "negative"
                        else:
                            css_class = "neutral"

                        title = article["title"][:70]
                        source = article.get("source", "")
                        pub = article.get("published", "")[:10]

                        st.markdown(f"""
                        <div class="news-item {css_class}">
                            <div style="font-size:0.85rem; color:#e0e0e0; margin-bottom:0.3rem;">
                                {title}
                            </div>
                            <div style="font-size:0.7rem; color:#8899aa;">
                                {source} · {pub} · 감성: {sent:+.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("뉴스 데이터가 없습니다.")


# ===== ⚖️ 종목 비교 =====
elif page == "⚖️ 종목 비교":
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ 종목 비교</h1>
        <p>여러 종목의 성과와 지표를 나란히 비교</p>
    </div>
    """, unsafe_allow_html=True)

    if len(selected_tickers) < 2:
        st.warning("비교하려면 2개 이상의 종목을 선택하세요.")
    else:
        with st.spinner("비교 데이터 로딩 중..."):
            compare_data = {}
            for ticker in selected_tickers:
                data = load_analysis(ticker, period)
                if data:
                    compare_data[ticker] = data

        if compare_data:
            # 수익률 비교 차트
            st.subheader("📈 수익률 비교 (기간 내 %)")
            fig_compare = go.Figure()
            for ticker, data in compare_data.items():
                df = data["df"]
                if not df.empty:
                    returns = (df["Close"] / df["Close"].iloc[0] - 1) * 100
                    fig_compare.add_trace(go.Scatter(
                        x=df.index, y=returns, name=ticker,
                        mode="lines", line=dict(width=2),
                    ))

            fig_compare.update_layout(
                height=450,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(14,17,23,0.8)",
                yaxis_title="수익률 (%)",
                hovermode="x unified",
                margin=dict(l=50, r=20, t=20, b=40),
            )
            fig_compare.add_hline(y=0, line_color="gray", line_dash="dash")
            st.plotly_chart(fig_compare, use_container_width=True)

            # 비교 테이블
            st.subheader("📊 지표 비교표")
            compare_rows = []
            for ticker, data in compare_data.items():
                ind = data["indicators"]
                score = data["score"]
                compare_rows.append({
                    "종목": ticker,
                    "이름": data["info"].get("name", ""),
                    "현재가": f"${ind['price']}",
                    "변동률": f"{ind['change_pct']:+.2f}%",
                    "RSI": ind["rsi"],
                    "MACD": ind["macd"],
                    "거래량비율": f"{ind['volume_ratio']}x",
                    "뉴스감성": data["news"]["score"],
                    "종합점수": score["score"],
                    "시그널": score["signal"],
                    "추천이유": score.get("summary", "")[:80] + "...",
                })

            compare_df = pd.DataFrame(compare_rows)
            st.dataframe(compare_df, hide_index=True, use_container_width=True)

            # 레이더 차트
            st.subheader("🕸️ 지표 레이더 차트")
            categories = ["RSI(정규화)", "MACD 강도", "거래량", "뉴스감성", "종합점수"]

            fig_radar = go.Figure()
            for ticker, data in compare_data.items():
                ind = data["indicators"]
                values = [
                    ind["rsi"] / 100,
                    min(abs(ind["macd"]) * 10, 1),
                    min(ind["volume_ratio"] / 3, 1),
                    (data["news"]["score"] + 1) / 2,
                    (data["score"]["score"] + 100) / 200,
                ]
                fig_radar.add_trace(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    name=ticker,
                    fill="toself",
                    opacity=0.3,
                ))

            fig_radar.update_layout(
                height=450,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                polar=dict(
                    bgcolor="rgba(14,17,23,0.8)",
                    radialaxis=dict(visible=True, range=[0, 1]),
                ),
                margin=dict(l=60, r=60, t=20, b=40),
            )
            st.plotly_chart(fig_radar, use_container_width=True)


# ===== 📰 뉴스센터 =====
elif page == "📰 뉴스센터":
    st.markdown("""
    <div class="main-header">
        <h1>📰 뉴스 감성 센터</h1>
        <p>종목별 뉴스와 시장 감성을 모아보기</p>
    </div>
    """, unsafe_allow_html=True)

    if not selected_tickers:
        st.info("👈 종목을 선택하세요.")
    else:
        for ticker in selected_tickers:
            data = load_analysis(ticker, period)
            if data is None:
                continue

            news = data["news"]
            st.subheader(f"{ticker} - {data['info'].get('name', '')}")

            # 감성 요약
            nc1, nc2, nc3 = st.columns(3)
            nc1.metric("감성 라벨", news["label"])
            nc2.metric("감성 점수", news["score"])
            nc3.metric("분석 기사", f"{news['count']}건")

            # 기사 목록
            if news["articles"]:
                for article in news["articles"][:5]:
                    sent = article.get("sentiment", 0)
                    if sent > 0.1:
                        css_class = "positive"
                        icon = "🟢"
                    elif sent < -0.1:
                        css_class = "negative"
                        icon = "🔴"
                    else:
                        css_class = "neutral"
                        icon = "🟡"

                    st.markdown(f"""
                    <div class="news-item {css_class}">
                        <div style="font-size:0.9rem; color:#e0e0e0;">
                            {icon} {article['title']}
                        </div>
                        <div style="font-size:0.75rem; color:#8899aa; margin-top:0.3rem;">
                            {article.get('source', '')} · {article.get('published', '')[:16]} · 감성: {sent:+.3f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("뉴스 없음")

            st.divider()


# ===== ⚙️ 설정 =====
elif page == "⚙️ 설정":
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ 설정</h1>
        <p>감시 종목과 분석 파라미터를 조정하세요</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📋 감시 종목 관리")

    st.write("현재 감시 목록:")
    for i, ticker in enumerate(st.session_state.watchlist):
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{ticker}**")
        if c2.button("❌", key=f"del_{i}"):
            st.session_state.watchlist.remove(ticker)
            st.rerun()

    st.divider()

    st.subheader("📐 기술적 지표 파라미터")
    st.caption("변경 사항은 현재 세션에만 적용됩니다.")

    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**이동평균선**")
        config.INDICATORS["sma_short"] = st.slider("SMA 단기", 5, 50, config.INDICATORS["sma_short"])
        config.INDICATORS["sma_long"] = st.slider("SMA 장기", 20, 200, config.INDICATORS["sma_long"])

        st.markdown("**RSI**")
        config.INDICATORS["rsi_period"] = st.slider("RSI 기간", 5, 30, config.INDICATORS["rsi_period"])
        config.INDICATORS["rsi_overbought"] = st.slider("과매수 기준", 60, 90, config.INDICATORS["rsi_overbought"])
        config.INDICATORS["rsi_oversold"] = st.slider("과매도 기준", 10, 40, config.INDICATORS["rsi_oversold"])

    with p2:
        st.markdown("**MACD**")
        config.INDICATORS["macd_fast"] = st.slider("MACD 빠른선", 5, 20, config.INDICATORS["macd_fast"])
        config.INDICATORS["macd_slow"] = st.slider("MACD 느린선", 15, 40, config.INDICATORS["macd_slow"])
        config.INDICATORS["macd_signal"] = st.slider("MACD 시그널", 5, 15, config.INDICATORS["macd_signal"])

        st.markdown("**볼린저 밴드**")
        config.INDICATORS["bb_period"] = st.slider("BB 기간", 10, 30, config.INDICATORS["bb_period"])
        config.INDICATORS["bb_std"] = st.slider("BB 표준편차", 1, 3, config.INDICATORS["bb_std"])

    st.divider()

    st.subheader("🔔 알림 설정")
    st.text_input("텔레그램 봇 토큰", value=config.TELEGRAM_BOT_TOKEN, type="password", key="tg_token")
    st.text_input("텔레그램 채팅 ID", value=config.TELEGRAM_CHAT_ID, key="tg_chat")
    st.text_input("NewsAPI 키", value=config.NEWS_API_KEY, type="password", key="news_key")

    if st.button("💾 알림 설정 저장 (현재 세션)", use_container_width=True):
        config.TELEGRAM_BOT_TOKEN = st.session_state.tg_token
        config.TELEGRAM_CHAT_ID = st.session_state.tg_chat
        config.NEWS_API_KEY = st.session_state.news_key
        st.success("설정이 저장되었습니다!")

    if st.button("🔄 캐시 초기화", use_container_width=True):
        st.cache_data.clear()
        st.success("캐시가 초기화되었습니다!")
