"""알림 시스템 모듈 (텔레그램 + 콘솔)"""
import asyncio
from datetime import datetime
import config

# 텔레그램 봇 (선택적)
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


def format_alert_message(result: dict) -> str:
    """분석 결과를 보기 좋은 메시지로 포맷합니다."""
    ind = result.get("indicators", {})

    msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📊 {result['ticker']} - {result.get('name', '')}
━━━━━━━━━━━━━━━━━━━━━━━━
💰 현재가: ${ind.get('price', 'N/A')} ({ind.get('change_pct', 0):+.2f}%)

📈 기술적 지표:
  • RSI: {ind.get('rsi', 'N/A')}
  • MACD: {ind.get('macd', 'N/A')}
  • SMA20: ${ind.get('sma_20', 'N/A')}
  • SMA50: ${ind.get('sma_50', 'N/A')}
  • 볼린저: ${ind.get('bb_lower', 'N/A')} ~ ${ind.get('bb_upper', 'N/A')}

📰 뉴스 감성: {result.get('news_sentiment', {}).get('label', 'N/A')}

🎯 종합 점수: {result.get('score', 0)}점
🚦 시그널: {result.get('signal', 'N/A')}

📋 분석 근거:
{chr(10).join(result.get('reasons', []))}
━━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return msg.strip()


def send_console_alert(result: dict):
    """콘솔에 알림을 출력합니다."""
    msg = format_alert_message(result)
    print(msg)


async def send_telegram_alert(result: dict):
    """텔레그램으로 알림을 보냅니다."""
    if not TELEGRAM_AVAILABLE:
        print("[경고] python-telegram-bot이 설치되지 않았습니다.")
        return
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    msg = format_alert_message(result)
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=msg)


def send_alert(result: dict, telegram: bool = True):
    """알림을 전송합니다."""
    # 항상 콘솔 출력
    send_console_alert(result)

    # 텔레그램 전송 (설정된 경우)
    if telegram and config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        try:
            asyncio.run(send_telegram_alert(result))
            print(f"[✓] {result['ticker']} 텔레그램 알림 전송 완료")
        except Exception as e:
            print(f"[경고] 텔레그램 전송 실패: {e}")


def send_summary_alert(results: list[dict]):
    """전체 분석 요약을 전송합니다."""
    buy_signals = [r for r in results if "매수" in r.get("signal", "")]
    sell_signals = [r for r in results if "매도" in r.get("signal", "")]
    hold_signals = [r for r in results if "관망" in r.get("signal", "")]

    summary = f"""
╔══════════════════════════════╗
║     📊 트레이딩 봇 분석 요약     ║
╠══════════════════════════════╣
║ ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}       ║
╚══════════════════════════════╝

🟢 매수 시그널 ({len(buy_signals)}개):
"""
    for r in buy_signals:
        summary += f"  • {r['ticker']} ({r.get('name', '')}) - 점수: {r['score']}\n"

    summary += f"\n🔴 매도 시그널 ({len(sell_signals)}개):\n"
    for r in sell_signals:
        summary += f"  • {r['ticker']} ({r.get('name', '')}) - 점수: {r['score']}\n"

    summary += f"\n🟡 관망 ({len(hold_signals)}개):\n"
    for r in hold_signals:
        summary += f"  • {r['ticker']} ({r.get('name', '')}) - 점수: {r['score']}\n"

    print(summary)

    # 매수/매도 시그널이 있는 종목만 상세 알림
    for r in buy_signals + sell_signals:
        send_alert(r, telegram=True)
