import os
import yfinance as yf
import ta
import requests
import pandas as pd
from datetime import datetime
import json

TICKERS = ["SOFI", "RKLB", "IONQ", "OPEN", "UPST", "RIOT", "MARA", "FUBO", "NIO", "LCID"]

MIN_PRICE = 1
MAX_PRICE = 50
MIN_CHANGE_PCT = 1
MAX_RSI = 80

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_data(tickers):
    data = yf.download(
        tickers=" ".join(tickers),
        period="5d",
        interval="1d",
        group_by="ticker"
    )
    return data

def calc_signals(data):
    results = []
    for ticker in TICKERS:
        try:
            df = data[ticker].copy()
        except KeyError:
            continue
        
        df = df.dropna()
        if len(df) < 15:
            continue
            
        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = float(last["Close"])
        prev_close = float(prev["Close"])
        change_pct = (price - prev_close) / prev_close * 100
        rsi = float(last["RSI"])
        volume = float(last["Volume"])
        
        if (MIN_PRICE <= price <= MAX_PRICE and 
            change_pct >= MIN_CHANGE_PCT and 
            rsi <= MAX_RSI):
            
            results.append({
                "ticker": ticker,
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "rsi": round(rsi, 2),
                "volume": int(volume),
            })
    
    return sorted(results, key=lambda x: x["change_pct"], reverse=True)

def format_message(results):
    if not results:
        return {
            "text": "⚠️ לא נמצאו מניות שעומדות בתנאים.",
            "reply_markup": {
                "inline_keyboard": [[{"text": "🔄 סרוק עכשיו", "callback_data": "scan_now"}]]
            }
        }
    
    lines = ["🚀 מניות עם מומנטום:"]
    for stock in results[:5]:
        lines.append(f"{stock['ticker']}")
        lines.append(f"💰 מחיר: {stock['price']}$")
        lines.append(f"📈 עלייה: {stock['change_pct']}%")
        lines.append(f"📊 RSI: {stock['rsi']}")
        lines.append("")
    
    return {
        "text": "\n".join(lines),
        "reply_markup": {
            "inline_keyboard": [[{"text": "🔄 סרוק שוב", "callback_data": "scan_again"}]]
        }
    }

def send_telegram_message(msg):
    if isinstance(msg, dict):
        payload = msg
    else:
        payload = {"text": msg, "chat_id": TELEGRAM_CHAT_ID}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ No Telegram credentials")
        print("📱 Would send:", payload["text"][:100])
        return
    
    try:
        resp = requests.post(url, json=payload)
        print("📤 Telegram status:", resp.status_code)
        if resp.status_code != 200:
            print("❌ Error:", resp.text)
    except Exception as e:
        print("❌ Telegram error:", e)

def main():
    print("🔥 Starting scan at", datetime.utcnow())
    print("📊 Scanning:", TICKERS)
    
    data = fetch_data(TICKERS)
    print("✅ Data OK")
    
    results = calc_signals(data)
    print(f"🎯 Found {len(results)} stocks")
    
    msg = format_message(results)
    send_telegram_message(msg)
    print("✅ Done!")

if __name__ == "__main__":
    main()

