import yfinance as yf
import pandas as pd
import ta
import requests
import os

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === STOCK LIST (can be expanded) ===
INDIAN_STOCKS = [
    'RELIANCE', 'HDFCBANK', 'INFY', 'ICICIBANK', 'TCS', 'LT',
    'SBIN', 'AXISBANK', 'KOTAKBANK', 'BHARTIARTL'
]

# === FUNCTIONS ===
def fetch_data(stock_symbol, period='3mo', interval='1d'):
    df = yf.download(stock_symbol + ".NS", period=period, interval=interval)
    df.dropna(inplace=True)
    return df

def apply_indicators(df):
    df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
    df['EMA50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['MACD_diff'] = ta.trend.macd_diff(df['Close'])
    df['RSI'] = ta.momentum.rsi(df['Close'])
    bb = ta.volatility.BollingerBands(df['Close'], window=20)
    df['BB_bwidth'] = bb.bollinger_wband()
    df['BB_upper'] = bb.bollinger_hband()
    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'])
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    return df

def signal_entry(df):
    if len(df) < 2:
        return False
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    conditions = [
        latest['Close'] > latest['EMA20'],
        latest['MACD_diff'] > 0 and prev['MACD_diff'] < 0,
        latest['RSI'] > 50,
        latest['ADX'] > 20,
        latest['BB_bwidth'] < df['BB_bwidth'].rolling(20).mean().iloc[-1],
        latest['Volume'] > 1.5 * latest['Volume_MA20']
    ]

    return all(conditions)

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")

def scan_stocks():
    breakout_candidates = []
    for stock in INDIAN_STOCKS:
        try:
            df = fetch_data(stock)
            df = apply_indicators(df)
            if signal_entry(df):
                breakout_candidates.append(stock)
        except Exception as e:
            print(f"Error processing {stock}: {e}")
    return breakout_candidates

def main():
    candidates = scan_stocks()
    if candidates:
        message = "\n".join([f"\u2705 Potential breakout: *{stock}*" for stock in candidates])
    else:
        message = "\u26A0 No breakout candidates found today."
    send_telegram_message(message)

if __name__ == '__main__':
    main()
