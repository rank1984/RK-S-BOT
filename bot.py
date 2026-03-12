import os
import yfinance as yf
import ta
import requests
import pandas as pd
from datetime import datetime

# רשימת המניות לסריקה (אפשר להרחיב)
TICKERS = [
    "SOFI", "RKLB", "IONQ", "OPEN", "UPST",
    "RIOT", "MARA", "FUBO", "NIO", "LCID"
]

# תנאי פילטר בסיסיים
MIN_PRICE = 2
MAX_PRICE = 20
MIN_CHANGE_PCT = 3    # 3%
MAX_RSI = 70

# קרדנציאלס ל-Telegram יגיעו מה-ENV (GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_data(tickers):
    # מוריד נתוני יום אחד אחורה + היום
    data = yf.download(
        tickers=" ".join(tickers),
        period="5d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False
    )
    return data

def calc_signals(data):
    results = []

    for ticker in TICKERS:
        try:
            df = data[ticker].copy()
        except KeyError:
            # אם אין נתונים למניה הזו, נמשיך הלאה
            continue

        # לוודא שיש מספיק נתונים
        df = df.dropna()
        if len(df) < 15:
            continue

        # מחשב RSI על מחירי הסגירה
        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

        # לוקחים רק את השורה האחרונה (היום האחרון)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        price = float(last["Close"])
        prev_close = float(prev["Close"])
        change_pct = (price - prev_close) / prev_close * 100
        rsi = float(last["RSI"])
        volume = float(last["Volume"])

        # פילטר בסיסי
        if price < MIN_PRICE or price > MAX_PRICE:
            continue
        if change_pct < MIN_CHANGE_PCT:
            continue
        if rsi > MAX_RSI:
            continue

        results.append({
            "ticker": ticker,
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "rsi": round(rsi, 2),
            "volume": int(volume),
        })

    # מיון לפי שינוי אחוזים בירידה (מהגבוה לנמוך)
    results = sorted(results, key=lambda x: x["change_pct"], reverse=True)
    return results

def format_message(results):
    if not results:
        return "⚠️ היום לא נמצאו מניות שעומדות בתנאים."

    lines = []
    lines.append("🚀 מניות עם מומנטום
")

    for stock in results[:5]:
        line = (
            f"{stock['ticker']}
"
            f"מחיר: {stock['price']}$
"
            f"עלייה: {stock['change_pct']}%
"
            f"RSI: {stock['rsi']}
"
            f"נפח: {stock['volume']}
"
        )
        lines.append(line)

    return "
".join(lines)

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("No Telegram credentials, skipping send.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        resp = requests.post(url, data=payload)
        print("Telegram status:", resp.status_code, resp.text)
    except Exception as e:
        print("Error sending Telegram message:", e)

def main():
    print("Starting scan at", datetime.utcnow())
    data = fetch_data(TICKERS)
    results = calc_signals(data)
    msg = format_message(results)
    send_telegram_message(msg)
    print("Done.")

if __name__ == "__main__":
    main()
