import os
import yfinance as yf
import ta
import requests
import pandas as pd
from datetime import datetime

TICKERS = ["SOFI", "RKLB", "IONQ", "OPEN", "UPST", "RIOT", "MARA", "FUBO", "NIO", "LCID"]
MIN_PRICE = 1
MAX_PRICE = 50
MIN_CHANGE_PCT = 1
MAX_RSI = 80

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_data(tickers):
    data = yf.download(tickers=" ".join(tickers), period="5d", interval="1d", group_by="ticker")
    return data

def calc_signals(data):
    results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].copy()
        except KeyError:
            continue
        df = df.dropna()
        if len(df) < 15: continue
        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(last["Close"])
        prev_close = float(prev["Close"])
        change_pct = (price - prev_close) / prev_close * 100
        rsi = float(last["RSI"])
        if (MIN_PRICE <= price <= MAX_PRICE and change_pct >= MIN_CHANGE_PCT and rsi <= MAX_RSI):
            results.append({
                "ticker": ticker, "price": round(price, 2), 
                "change_pct": round(change_pct, 2), "rsi": round(rsi, 2),
                "volume": int(last["Volume"])
            })
    return sorted(results, key=lambda x: x["change_pct"], reverse=True)

def format_message(results):
    if not results:
        return "⚠️ לא נמצאו מניות שעומדות בתנאים.\n\n🔄 כפתור סריקה: Actions ב-GitHub"
    
    lines = ["🚀 מניות עם מומנטום:"]
    for stock in results[:5]:
        lines.extend([
            f"{stock['ticker']}",
            f"💰 מחיר: {stock['price']}$",
            f"📈 עלייה: {stock['change_pct']}%", 
            f"📊 RSI: {stock['rsi']}",
            ""
        ])
    return "\n".join(lines)

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ No Telegram credentials")
        print("📱 Message:", text[:100])
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        resp = requests.post(url, data=payload)
        print("📤 Telegram:", resp.status_code, resp.text[:100])
    except Exception as e:
        print("❌ Telegram error:", e)

def main():
    print("🔥 Starting at", datetime.utcnow())
    data = fetch_data(TICKERS)
    results = calc_signals(data)
    print(f"🎯 Found {len(results)} stocks")
    msg = format_message(results)
    send_telegram_message(msg)
    print("✅ Done!")

if __name__ == "__main__":
    main()
