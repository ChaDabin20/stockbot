"""트레이딩 봇 메인 실행 파일

사용법:
    python main.py              # 1회 분석 실행
    python main.py --schedule   # 스케줄러로 주기적 실행
    streamlit run dashboard.py  # 대시보드 실행
"""
import argparse
import schedule
import time
from datetime import datetime

from signals import analyze_all, analyze_ticker
from alerts import send_alert, send_summary_alert
import config


def run_analysis():
    """전체 분석을 실행합니다."""
    print(f"\n{'='*50}")
    print(f"🚀 분석 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    results = analyze_all()

    # 에러 없는 결과만 필터
    valid_results = [r for r in results if "error" not in r]

    if valid_results:
        send_summary_alert(valid_results)
    else:
        print("[경고] 분석 가능한 종목이 없습니다.")

    print(f"\n✅ 분석 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return valid_results


def run_single(ticker: str):
    """특정 종목 1개를 분석합니다."""
    print(f"\n🔍 {ticker} 분석 중...")
    result = analyze_ticker(ticker)
    if "error" not in result:
        send_alert(result)
    else:
        print(f"[오류] {ticker}: {result['error']}")


def run_scheduler():
    """스케줄러로 주기적으로 분석을 실행합니다."""
    interval = config.CHECK_INTERVAL_MINUTES
    print(f"📅 스케줄러 시작 (매 {interval}분마다 분석)")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    # 시작 시 1회 실행
    run_analysis()

    # 주기적 실행 설정
    schedule.every(interval).minutes.do(run_analysis)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 스케줄러를 종료합니다.")


def main():
    parser = argparse.ArgumentParser(description="📊 주식 트레이딩 봇")
    parser.add_argument("--schedule", action="store_true",
                        help="스케줄러 모드로 실행 (주기적 분석)")
    parser.add_argument("--ticker", type=str,
                        help="특정 종목만 분석 (예: --ticker AAPL)")
    parser.add_argument("--dashboard", action="store_true",
                        help="Streamlit 대시보드 실행")
    args = parser.parse_args()

    if args.dashboard:
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py"])
    elif args.ticker:
        run_single(args.ticker.upper())
    elif args.schedule:
        run_scheduler()
    else:
        run_analysis()


if __name__ == "__main__":
    main()
